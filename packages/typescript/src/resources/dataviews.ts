import { createDataView, getDataView } from "../api/dataviews.js";
import type { ClientContext } from "../client.js";

export class DataViewsResource {
  constructor(private readonly ctx: ClientContext) {}

  async create(opts: {
    name: string;
    datasourceId: string;
    table: string;
    fields?: Array<{ name: string; type: string }>;
  }): Promise<string> {
    return createDataView({ ...this.ctx.base(), ...opts });
  }

  async get(id: string): Promise<unknown> {
    const raw = await getDataView({ ...this.ctx.base(), id });
    return JSON.parse(raw);
  }
}
