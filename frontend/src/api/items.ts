import { z } from "zod";

/**
 * Placeholder schema describing the intended EnrichedItem shape. No endpoint is wired in
 * Task 001 — real /items integration arrives in Task 006. Kept here so the typed surface and
 * the ItemCard placeholder agree.
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
  published_at: z.string(),
  priority_class: PriorityClassSchema,
  summary: z.string(),
  why_it_matters: z.string(),
  recommended_action: z.string(),
  scores: ScoresSchema,
});

export type Item = z.infer<typeof ItemSchema>;
export type PriorityClass = z.infer<typeof PriorityClassSchema>;
