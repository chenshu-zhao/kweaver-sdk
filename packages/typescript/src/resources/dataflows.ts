import {
  createDataflow,
  runDataflow,
  pollDataflowResults,
  deleteDataflow,
  executeDataflow,
  type DataflowCreateBody,
  type DataflowResult,
} from "../api/dataflow.js";
import type { ClientContext } from "../client.js";

export class DataflowsResource {
  constructor(private readonly ctx: ClientContext) {}

  async create(body: DataflowCreateBody): Promise<string> {
    return createDataflow({ ...this.ctx.base(), body });
  }

  async run(dagId: string): Promise<void> {
    return runDataflow({ ...this.ctx.base(), dagId });
  }

  async poll(dagId: string, opts: { interval?: number; timeout?: number } = {}): Promise<DataflowResult> {
    return pollDataflowResults({ ...this.ctx.base(), dagId, ...opts });
  }

  async delete(dagId: string): Promise<void> {
    return deleteDataflow({ ...this.ctx.base(), dagId });
  }

  async execute(
    body: DataflowCreateBody,
    opts: { interval?: number; timeout?: number } = {},
  ): Promise<DataflowResult> {
    return executeDataflow({ ...this.ctx.base(), body, ...opts });
  }
}
