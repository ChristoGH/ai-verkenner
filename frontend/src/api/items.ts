import { z } from "zod";
import { apiGet } from "./client";

/**
 * The EnrichedItem shape returned by GET /items (M6). Mirrors backend `ItemOut`. The five scores
 * keep hype labelled inverted; summary (fact) is kept separate from why_it_matters /
 * recommended_action (interpretation); the source link is always present.
 */
export const ScoresSchema = z.object({
  relevance: z.number(),
  novelty: z.number(),
  actionability: z.number(),
  strategic_potential: z.number(),
  hype: z.number(), // inverted: 0 = signal, 5 = noise
});

export const PriorityClassSchema = z.enum([
  "immediate_priority",
  "operational_update",
  "horizon_signal",
  "archive",
]);

export const ItemSchema = z.object({
  id: z.string(),
  title: z.string(),
  source_name: z.string(),
  source_url: z.string().url(),
  published_at: z.string().nullable(),
  priority_class: PriorityClassSchema,
  category: z.string(),
  tags: z.array(z.string()),
  scores: ScoresSchema,
  summary: z.string(),
  why_it_matters: z.string(),
  recommended_action: z.string(),
  is_weak_signal: z.boolean(),
  horizon: z.string().nullable(),
  graph_why: z.string(),
  convergence: z.number(),
});

export const ItemsSchema = z.array(ItemSchema);

export type Item = z.infer<typeof ItemSchema>;
export type PriorityClass = z.infer<typeof PriorityClassSchema>;

export interface ItemsQuery {
  priorityClass?: PriorityClass;
  entity?: string;
  limit?: number;
}

export function fetchItems(query: ItemsQuery = {}): Promise<Item[]> {
  const params = new URLSearchParams();
  if (query.priorityClass) params.set("priority_class", query.priorityClass);
  if (query.entity) params.set("entity", query.entity);
  if (query.limit) params.set("limit", String(query.limit));
  const qs = params.toString();
  return apiGet(`/items${qs ? `?${qs}` : ""}`, ItemsSchema);
}
