import {
  getCurrentPlatform,
  loadTokenConfig,
} from "./config/store.js";
import { AgentsResource } from "./resources/agents.js";
import { ConversationsResource } from "./resources/conversations.js";
import { ContextLoaderResource } from "./resources/context-loader.js";
import { KnowledgeNetworksResource } from "./resources/knowledge-networks.js";
import { BknResource } from "./resources/bkn.js";

// ── ClientContext ─────────────────────────────────────────────────────────────

/**
 * Shared credentials passed to every resource method.
 * Internal — use KWeaverClient.
 */
export interface ClientContext {
  /** Returns the base options that every API function requires. */
  base(): { baseUrl: string; accessToken: string; businessDomain: string };
}

// ── KWeaverClientOptions ──────────────────────────────────────────────────────

export interface KWeaverClientOptions {
  /**
   * KWeaver platform base URL (e.g. "https://your-kweaver.com").
   * When omitted, reads the active platform saved by `kweaver auth login`.
   */
  baseUrl?: string;

  /**
   * Bearer access token.
   * When omitted, reads the token saved for the active platform.
   */
  accessToken?: string;

  /**
   * x-business-domain header value.  Defaults to "bd_public".
   * Override with KWEAVER_BUSINESS_DOMAIN env var or pass explicitly.
   */
  businessDomain?: string;
}

// ── KWeaverClient ─────────────────────────────────────────────────────────────

/**
 * Main entry point for the KWeaver TypeScript SDK.
 *
 * @example Using explicit credentials:
 * ```typescript
 * import { KWeaverClient } from "kweaver-sdk";
 *
 * const client = new KWeaverClient({
 *   baseUrl: "https://your-kweaver.com",
 *   accessToken: "your-token",
 * });
 *
 * const kns = await client.knowledgeNetworks.list();
 * const reply = await client.agents.chat("agent-id", "你好");
 * console.log(reply.text);
 * ```
 *
 * @example Using credentials saved by `kweaver auth login` (zero config):
 * ```typescript
 * const client = new KWeaverClient();   // reads ~/.kweaver/
 * ```
 *
 * @example Using environment variables:
 * ```typescript
 * // Set KWEAVER_BASE_URL and KWEAVER_TOKEN
 * const client = new KWeaverClient();
 * ```
 */
export class KWeaverClient implements ClientContext {
  private readonly _baseUrl: string;
  private readonly _accessToken: string;
  private readonly _businessDomain: string;

  /** Knowledge network CRUD and schema (object/relation/action types). */
  readonly knowledgeNetworks: KnowledgeNetworksResource;

  /** Agent listing and chat (single-shot and streaming). */
  readonly agents: AgentsResource;

  /** BKN engine: instance queries, subgraph, action execute/poll, action logs. */
  readonly bkn: BknResource;

  /** Conversation and message history. */
  readonly conversations: ConversationsResource;

  constructor(opts: KWeaverClientOptions = {}) {
    const envUrl = process.env.KWEAVER_BASE_URL;
    const envToken = process.env.KWEAVER_TOKEN;
    const envDomain = process.env.KWEAVER_BUSINESS_DOMAIN;

    // Resolve baseUrl: explicit > env > saved config
    let baseUrl = opts.baseUrl ?? envUrl;
    let accessToken = opts.accessToken ?? envToken;

    if (!baseUrl || !accessToken) {
      const platform = getCurrentPlatform();
      if (platform) {
        const stored = loadTokenConfig(platform);
        if (!baseUrl) baseUrl = platform;
        if (!accessToken && stored) accessToken = stored.accessToken;
      }
    }

    if (!baseUrl) {
      throw new Error(
        "KWeaverClient: baseUrl is required. " +
        "Pass it explicitly, set KWEAVER_BASE_URL, or run `kweaver auth login`."
      );
    }
    if (!accessToken) {
      throw new Error(
        "KWeaverClient: accessToken is required. " +
        "Pass it explicitly, set KWEAVER_TOKEN, or run `kweaver auth login`."
      );
    }

    this._baseUrl = baseUrl.replace(/\/+$/, "");
    this._accessToken = accessToken;
    this._businessDomain = opts.businessDomain ?? envDomain ?? "bd_public";

    this.knowledgeNetworks = new KnowledgeNetworksResource(this);
    this.agents = new AgentsResource(this);
    this.bkn = new BknResource(this);
    this.conversations = new ConversationsResource(this);
  }

  /** @internal — used by resource classes to build API call options. */
  base(): { baseUrl: string; accessToken: string; businessDomain: string } {
    return {
      baseUrl: this._baseUrl,
      accessToken: this._accessToken,
      businessDomain: this._businessDomain,
    };
  }

  /**
   * Create a ContextLoaderResource bound to a specific knowledge network.
   *
   * @param mcpUrl  Full MCP endpoint URL (e.g. from `kweaver context-loader config show`).
   * @param knId    Knowledge network ID to search against.
   *
   * @example
   * ```typescript
   * const cl = client.contextLoader(mcpUrl, "d5iv6c9818p72mpje8pg");
   * const results = await cl.search({ query: "高血压 治疗" });
   * ```
   */
  contextLoader(mcpUrl: string, knId: string): ContextLoaderResource {
    return new ContextLoaderResource(this, mcpUrl, knId);
  }
}
