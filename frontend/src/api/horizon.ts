import { z } from "zod";
import { apiGet } from "./client";
import { ItemSchema } from "./items";

/**
 * GET /horizon (M6) — THE weak-signal view. The horizon_signal/archive quadrant ranked by graph
 * convergence (NOT the Core Radar order), each item carrying its `why` and contributing sources.
 */
export const HorizonItemSchema = ItemSchema.extend({
  graph_score: z.number(),
  contributing_sources: z.array(z.string()),
});

export const HorizonSchema = z.object({
  items: z.array(HorizonItemSchema),
  graph_available: z.boolean(),
});

export type HorizonItem = z.infer<typeof HorizonItemSchema>;
export type Horizon = z.infer<typeof HorizonSchema>;

export function fetchHorizon(limit = 50): Promise<Horizon> {
  return apiGet(`/horizon?limit=${limit}`, HorizonSchema);
}
