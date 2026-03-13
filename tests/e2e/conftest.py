"""E2E test configuration for KWeaver SDK against a real ADP environment.

Follows the Alfred testing pattern:
  - pytest CLI options for environment selection
  - Environment registry for multiple ADP deployments
  - Session-scoped fixtures for expensive setup (client, datasource)
  - Destructive marker for state-mutating tests (build/delete KN)
  - Factory fixtures for common operations
  - Automatic token refresh via Playwright browser login
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

from kweaver import ADPClient

# ---------------------------------------------------------------------------
# Auto-load secrets from ~/.env.secrets (same pattern as Alfred)
# ---------------------------------------------------------------------------

_SECRETS_PATH = Path.home() / ".env.secrets"

def _load_env_secrets() -> None:
    """Source KEY=VALUE lines from ~/.env.secrets into os.environ.

    Handles ``export KEY="VALUE"`` and ``KEY=VALUE`` formats.
    Skips comments and blank lines. Does NOT override existing env vars.
    """
    if not _SECRETS_PATH.exists():
        return
    for line in _SECRETS_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        line = line.removeprefix("export ")
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        # Don't override — explicit env vars take precedence
        if key not in os.environ:
            os.environ[key] = value

_load_env_secrets()


# ---------------------------------------------------------------------------
# Playwright-based OAuth2 token refresh
# ---------------------------------------------------------------------------

def _refresh_adp_token(base_url: str, username: str, password: str) -> str:
    """Login to ADP via browser and return a fresh Bearer token.

    Uses Playwright (headless) to automate the Ory OAuth2 login flow:
      1. GET /api/dip-hub/v1/login  → 302 → /oauth2/auth → /oauth2/signin
      2. Fill account/password → click login button
      3. OAuth2 consent auto-approved → callback sets dip.oauth2_token cookie

    Returns the ory_at_* token string (without 'Bearer ' prefix).
    """
    import time as _time

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Start the OAuth2 login flow
        page.goto(
            f"{base_url}/api/dip-hub/v1/login",
            wait_until="networkidle",
            timeout=30000,
        )

        # Fill the login form and submit
        page.fill('input[name="account"]', username)
        page.fill('input[name="password"]', password)
        page.click("button.ant-btn-primary")

        # Poll for the dip.oauth2_token cookie (set after OAuth2 callback)
        token = None
        for _ in range(30):
            _time.sleep(1)
            for cookie in context.cookies():
                if cookie["name"] == "dip.oauth2_token":
                    token = cookie["value"]
                    break
            if token:
                break

        browser.close()

    if not token:
        raise RuntimeError(
            "Failed to extract ADP token after browser login. "
            "Check ADP_USERNAME/ADP_PASSWORD in ~/.env.secrets"
        )

    return token


# ---------------------------------------------------------------------------
# Default environment registry
# ---------------------------------------------------------------------------

E2E_ENV: dict[str, dict[str, str]] = {
    "dev": {
        "base_url": os.getenv("ADP_BASE_URL", ""),
        "token": os.getenv("ADP_TOKEN", ""),
        "account_id": os.getenv("ADP_ACCOUNT_ID", "test"),
        "business_domain": os.getenv("ADP_BUSINESS_DOMAIN", ""),
        # Database credentials for datasource tests
        "db_type": os.getenv("ADP_TEST_DB_TYPE", "mysql"),
        "db_host": os.getenv("ADP_TEST_DB_HOST", ""),
        "db_port": os.getenv("ADP_TEST_DB_PORT", "3306"),
        "db_name": os.getenv("ADP_TEST_DB_NAME", ""),
        "db_user": os.getenv("ADP_TEST_DB_USER", ""),
        "db_pass": os.getenv("ADP_TEST_DB_PASS", ""),
        "db_schema": os.getenv("ADP_TEST_DB_SCHEMA", ""),
    },
}


# ---------------------------------------------------------------------------
# pytest CLI options
# ---------------------------------------------------------------------------


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--e2e-env",
        default="dev",
        help="E2E environment name from registry (default: dev)",
    )
    parser.addoption(
        "--e2e-base-url",
        default=None,
        help="Override ADP base URL",
    )
    parser.addoption(
        "--e2e-token",
        default=None,
        help="Override ADP bearer token",
    )
    parser.addoption(
        "--run-destructive",
        action="store_true",
        default=False,
        help="Enable destructive tests that create/delete knowledge networks",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "destructive: marks tests that mutate ADP state (create/build/delete KN)",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if config.getoption("--run-destructive"):
        return
    skip = pytest.mark.skip(reason="needs --run-destructive option to run")
    for item in items:
        if "destructive" in item.keywords:
            item.add_marker(skip)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def e2e_env(request: pytest.FixtureRequest) -> dict[str, str]:
    """Resolve and validate the E2E environment config.

    Returns a dict with connection parameters.
    Skips the entire session if the environment is not available.
    """
    env_name = request.config.getoption("--e2e-env")
    env_cfg = E2E_ENV.get(env_name, E2E_ENV["dev"]).copy()

    # CLI overrides take precedence
    base_url_override = request.config.getoption("--e2e-base-url")
    if base_url_override:
        env_cfg["base_url"] = base_url_override

    token_override = request.config.getoption("--e2e-token")
    if token_override:
        env_cfg["token"] = token_override

    if not env_cfg.get("base_url"):
        pytest.skip("E2E environment not available: ADP_BASE_URL not set")

    # Auto-refresh token if credentials are available
    username = os.getenv("ADP_USERNAME", "")
    password = os.getenv("ADP_PASSWORD", "")
    if username and password:
        try:
            fresh_token = _refresh_adp_token(
                env_cfg["base_url"], username, password
            )
            env_cfg["token"] = f"Bearer {fresh_token}"
        except Exception as exc:
            # Fall back to static token if auto-login fails
            if not env_cfg.get("token"):
                pytest.skip(f"Token refresh failed and no static ADP_TOKEN: {exc}")
    elif not env_cfg.get("token"):
        pytest.skip("E2E environment not available: ADP_TOKEN not set and no ADP_USERNAME/ADP_PASSWORD")

    return env_cfg


@pytest.fixture(scope="session")
def adp_client(e2e_env: dict[str, str]) -> ADPClient:
    """Session-scoped ADPClient connected to the E2E environment."""
    client = ADPClient(
        base_url=e2e_env["base_url"],
        token=e2e_env["token"],
        account_id=e2e_env.get("account_id", "test"),
        business_domain=e2e_env.get("business_domain") or None,
    )
    yield client
    client.close()


@pytest.fixture(scope="session")
def db_config(e2e_env: dict[str, str]) -> dict[str, Any]:
    """Database connection config for datasource tests.

    Skips if db_host is not configured.
    """
    if not e2e_env.get("db_host"):
        pytest.skip("E2E database not configured: ADP_TEST_DB_HOST not set")

    cfg = {
        "type": e2e_env["db_type"],
        "host": e2e_env["db_host"],
        "port": int(e2e_env["db_port"]),
        "database": e2e_env["db_name"],
        "account": e2e_env["db_user"],
        "password": e2e_env["db_pass"],
    }
    if e2e_env.get("db_schema"):
        cfg["schema"] = e2e_env["db_schema"]
    return cfg


# ---------------------------------------------------------------------------
# Factory fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def create_datasource(adp_client: ADPClient, db_config: dict[str, Any]):
    """Factory: create a datasource and track it for cleanup.

    Returns a callable that creates datasources. All created datasources
    are deleted at session teardown.
    """
    created_ids: list[str] = []

    def _create(name: str = "e2e_test_ds", **overrides: Any) -> Any:
        params = {**db_config, **overrides}
        ds = adp_client.datasources.create(name=name, **params)
        created_ids.append(ds.id)
        return ds

    yield _create

    for ds_id in reversed(created_ids):
        try:
            adp_client.datasources.delete(ds_id)
        except Exception:
            pass


@pytest.fixture(scope="session")
def create_knowledge_network(adp_client: ADPClient):
    """Factory: create a knowledge network and track it for cleanup.

    All created KNs are deleted at session teardown (reverse order).
    """
    created_ids: list[str] = []

    def _create(name: str = "e2e_test_kn", **kwargs: Any) -> Any:
        kn = adp_client.knowledge_networks.create(name=name, **kwargs)
        created_ids.append(kn.id)
        return kn

    yield _create

    for kn_id in reversed(created_ids):
        try:
            adp_client.knowledge_networks.delete(kn_id)
        except Exception:
            pass
