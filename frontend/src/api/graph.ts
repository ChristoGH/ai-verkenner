import { z } from "zod";
import { apiGet } from "./client";

/**
 * GET /graph (M6) — the Cosmograph projection: capped nodes/links from Neo4j (events + top
 * entities). `available` is false when Neo4j is unreachable (degraded, empty graph).
 */
export const GraphNodeSchema = z.object({
  id: z.string(),
  label: z.string(),
  kind: z.string(),
  type: z.string().nullable().optional(),
  priority_class: z.string().nullable().optional(),
  ts: z.string().nullable().optional(),
});

export const GraphLinkSchema = z.object({
  source: z.string(),
  target: z.string(),
  kind: z.string(),
  ts: z.string().nullable().optional(),
});

export const GraphSchema = z.object({
  nodes: z.array(GraphNodeSchema),
  links: z.array(GraphLinkSchema),
  truncated: z.boolean(),
  available: z.boolean(),
});

export type GraphNode = z.infer<typeof GraphNodeSchema>;
export type GraphLink = z.infer<typeof GraphLinkSchema>;
export type GraphData = z.infer<typeof GraphSchema>;

export interface GraphQuery {
  limit?: number;
  windowDays?: number;
  priority?: string;
}

export function fetchGraph(query: GraphQuery = {}): Promise<GraphData> {
  const params = new URLSearchParams();
  if (query.limit) params.set("limit", String(query.limit));
  if (query.windowDays) params.set("window_days", String(query.windowDays));
  if (query.priority) params.set("priority", query.priority);
  const qs = params.toString();
  return apiGet(`/graph${qs ? `?${qs}` : ""}`, GraphSchema);
}
