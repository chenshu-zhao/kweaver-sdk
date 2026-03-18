import test from "node:test";
import assert from "node:assert/strict";

import { KWeaverClient } from "../src/client.js";
import { ContextLoaderResource } from "../src/resources/context-loader.js";

const BASE = "https://mock.kweaver.test";
const TOKEN = "test-token-abc";

function makeClient(extra: Record<string, string> = {}): KWeaverClient {
  return new KWeaverClient({ baseUrl: BASE, accessToken: TOKEN, ...extra });
}

// ── constructor ───────────────────────────────────────────────────────────────

test("KWeaverClient throws when accessToken missing and env var absent", () => {
  // Point config dir to an empty temp directory so no saved token is found
  const emptyDir = new URL("../../.tmp-test-cfg", import.meta.url).pathname;
  const origTok = process.env.KWEAVER_TOKEN;
  const origDir = process.env.KWEAVERC_CONFIG_DIR;
  delete process.env.KWEAVER_TOKEN;
  process.env.KWEAVERC_CONFIG_DIR = emptyDir;

  try {
    assert.throws(
      () => new KWeaverClient({ baseUrl: BASE }),
      /accessToken is required/
    );
  } finally {
    delete process.env.KWEAVERC_CONFIG_DIR;
    if (origTok !== undefined) process.env.KWEAVER_TOKEN = origTok;
    if (origDir !== undefined) process.env.KWEAVERC_CONFIG_DIR = origDir;
  }
});

test("KWeaverClient strips trailing slash from baseUrl", () => {
  const client = new KWeaverClient({ baseUrl: `${BASE}///`, accessToken: TOKEN });
  assert.equal(client.base().baseUrl, BASE);
});

test("KWeaverClient defaults businessDomain to bd_public", () => {
  const client = makeClient();
  assert.equal(client.base().businessDomain, "bd_public");
});

test("KWeaverClient accepts custom businessDomain", () => {
  const client = makeClient({ businessDomain: "bd_enterprise" });
  assert.equal(client.base().businessDomain, "bd_enterprise");
});

test("KWeaverClient reads businessDomain from env", () => {
  process.env.KWEAVER_BUSINESS_DOMAIN = "bd_test";
  try {
    const client = makeClient();
    assert.equal(client.base().businessDomain, "bd_test");
  } finally {
    delete process.env.KWEAVER_BUSINESS_DOMAIN;
  }
});

test("KWeaverClient exposes resource properties", () => {
  const client = makeClient();
  assert.ok(client.knowledgeNetworks, "knowledgeNetworks resource exists");
  assert.ok(client.agents, "agents resource exists");
  assert.ok(client.bkn, "bkn resource exists");
  assert.ok(client.conversations, "conversations resource exists");
  assert.ok(typeof client.contextLoader === "function", "contextLoader() factory exists");
});

// ── knowledgeNetworks resource ────────────────────────────────────────────────

test("client.knowledgeNetworks.list calls listKnowledgeNetworks and parses data array", async () => {
  const orig = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ data: [{ id: "kn-1", name: "Net A" }] }), { status: 200 });

  try {
    const client = makeClient();
    const result = await client.knowledgeNetworks.list();
    assert.deepEqual(result, [{ id: "kn-1", name: "Net A" }]);
  } finally {
    globalThis.fetch = orig;
  }
});

test("client.knowledgeNetworks.listObjectTypes returns array", async () => {
  const orig = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(JSON.stringify([{ id: "ot-1", name: "Person" }]), { status: 200 });

  try {
    const client = makeClient();
    const result = await client.knowledgeNetworks.listObjectTypes("kn-abc");
    assert.deepEqual(result, [{ id: "ot-1", name: "Person" }]);
  } finally {
    globalThis.fetch = orig;
  }
});

test("client.knowledgeNetworks.listObjectTypes unwraps entries wrapper", async () => {
  const orig = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ entries: [{ id: "ot-2", name: "Case" }] }), { status: 200 });

  try {
    const client = makeClient();
    const result = await client.knowledgeNetworks.listObjectTypes("kn-abc");
    assert.deepEqual(result, [{ id: "ot-2", name: "Case" }]);
  } finally {
    globalThis.fetch = orig;
  }
});

// ── agents resource ───────────────────────────────────────────────────────────

test("client.agents.list unwraps data.records", async () => {
  const orig = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({ data: { records: [{ id: "a-1", name: "Supply Chain" }] } }),
      { status: 200 }
    );

  try {
    const client = makeClient();
    const result = await client.agents.list({ keyword: "supply" });
    assert.deepEqual(result, [{ id: "a-1", name: "Supply Chain" }]);
  } finally {
    globalThis.fetch = orig;
  }
});

test("client.agents.chat resolves agent info then sends chat request", async () => {
  const orig = globalThis.fetch;
  let callCount = 0;

  globalThis.fetch = async (input) => {
    callCount++;
    const url = typeof input === "string" ? input : input.toString();

    if (url.includes("/agent-market/agent")) {
      // fetchAgentInfo expects { id, key, version } directly
      return new Response(
        JSON.stringify({ id: "a-real", key: "k-real", version: "v2" }),
        { status: 200 }
      );
    }

    // sendChatRequest response (non-stream JSON)
    return new Response(
      JSON.stringify({
        message: { content: { final_answer: { answer: { text: "你好！" } } } },
        conversation_id: "conv-42",
      }),
      { status: 200 }
    );
  };

  try {
    const client = makeClient();
    const result = await client.agents.chat("agent-id", "你好");
    assert.equal(result.text, "你好！");
    assert.equal(result.conversationId, "conv-42");
    assert.equal(callCount, 2, "should call agent-info then chat");
  } finally {
    globalThis.fetch = orig;
  }
});

// ── bkn.knSearch ─────────────────────────────────────────────────────────────

test("client.bkn.knSearch sends correct request and parses response", async () => {
  const orig = globalThis.fetch;
  const captured: { url?: string; body?: string } = {};
  globalThis.fetch = async (input: string | URL | Request, init?: RequestInit) => {
    captured.url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    captured.body = init?.body as string;
    return new Response(
      JSON.stringify({
        object_types: [{ id: "ot_01", name: "Products" }],
        relation_types: [],
        action_types: [],
      }),
      { status: 200 }
    );
  };

  try {
    const client = makeClient();
    const result = await client.bkn.knSearch("kn_01", "产品");
    assert.ok(captured.url?.includes("/api/agent-retrieval/in/v1/kn/kn_search"));
    const sentBody = JSON.parse(captured.body!);
    assert.equal(sentBody.kn_id, "kn_01");
    assert.equal(sentBody.query, "产品");
    assert.equal(result.object_types?.length, 1);
    assert.equal((result.object_types![0] as { name: string }).name, "Products");
  } finally {
    globalThis.fetch = orig;
  }
});

test("client.bkn.knSearch passes only_schema when set", async () => {
  const orig = globalThis.fetch;
  const captured: { body?: string } = {};
  globalThis.fetch = async (_input: string | URL | Request, init?: RequestInit) => {
    captured.body = init?.body as string;
    return new Response(
      JSON.stringify({ object_types: [], relation_types: [], action_types: [] }),
      { status: 200 }
    );
  };

  try {
    const client = makeClient();
    await client.bkn.knSearch("kn_01", "test", { onlySchema: true });
    const sentBody = JSON.parse(captured.body!);
    assert.equal(sentBody.only_schema, true);
  } finally {
    globalThis.fetch = orig;
  }
});

// ── contextLoader factory ─────────────────────────────────────────────────────

test("client.contextLoader returns a ContextLoaderResource", () => {
  const client = makeClient();
  const cl = client.contextLoader("https://mock/mcp", "kn-xyz");
  assert.ok(cl instanceof ContextLoaderResource);
});
