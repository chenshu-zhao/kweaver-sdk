import { listAgents } from "../api/agent-list.js";
import {
  fetchAgentInfo,
  sendChatRequest,
  sendChatRequestStream,
} from "../api/agent-chat.js";
import type { ChatResult, SendChatRequestStreamCallbacks } from "../api/agent-chat.js";
import type { ClientContext } from "../client.js";

export class AgentsResource {
  constructor(private readonly ctx: ClientContext) {}

  async list(opts: { name?: string; keyword?: string; offset?: number; limit?: number } = {}): Promise<unknown[]> {
    const { keyword, ...rest } = opts;
    const raw = await listAgents({ ...this.ctx.base(), name: keyword, ...rest });
    const parsed = JSON.parse(raw) as unknown;
    const items =
      parsed && typeof parsed === "object" && "data" in parsed
        ? (parsed as { data: { records?: unknown[] } }).data?.records ?? []
        : Array.isArray(parsed)
          ? parsed
          : [];
    return items;
  }

  /** Resolve agent key and version for a given agent id. */
  async info(agentId: string, version = "v0"): Promise<{ id: string; key: string; version: string }> {
    const info = await fetchAgentInfo({ ...this.ctx.base(), agentId, version });
    return info;
  }

  /**
   * Send a single message and return the full response.
   * Automatically resolves the agent key/version before sending.
   */
  async chat(
    agentId: string,
    message: string,
    opts: {
      conversationId?: string;
      version?: string;
      stream?: boolean;
      verbose?: boolean;
    } = {}
  ): Promise<ChatResult> {
    const { version = "v0", stream = false, conversationId, verbose } = opts;
    const info = await fetchAgentInfo({ ...this.ctx.base(), agentId, version });
    return sendChatRequest({
      ...this.ctx.base(),
      agentId: info.id,
      agentKey: info.key,
      agentVersion: info.version,
      query: message,
      conversationId,
      stream,
      verbose,
    });
  }

  /**
   * Send a message with streaming callbacks.
   * Automatically resolves the agent key/version before sending.
   */
  async stream(
    agentId: string,
    message: string,
    callbacks: SendChatRequestStreamCallbacks,
    opts: {
      conversationId?: string;
      version?: string;
      verbose?: boolean;
    } = {}
  ): Promise<ChatResult> {
    const { version = "v0", conversationId, verbose } = opts;
    const info = await fetchAgentInfo({ ...this.ctx.base(), agentId, version });
    return sendChatRequestStream(
      {
        ...this.ctx.base(),
        agentId: info.id,
        agentKey: info.key,
        agentVersion: info.version,
        query: message,
        conversationId,
        stream: true,
        verbose,
      },
      callbacks
    );
  }
}
