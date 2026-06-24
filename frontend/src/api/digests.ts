import { z } from "zod";
import { apiGet } from "./client";

/**
 * GET /digests + /digests/{id} (M7) — the decision-oriented weekly briefings. The list is a summary
 * (counts + provenance); the detail carries the rendered markdown and the Events it drew from.
 */
export const DigestSummarySchema = z.object({
  id: z.number(),
  period_start: z.string().nullable(),
  period_end: z.string().nullable(),
  generated_at: z.string(),
  method: z.string(), // "llm" | "fallback"
  item_count: z.number(),
  noise_count: z.number(),
  graphrag: z.boolean(),
});

export const DigestSchema = DigestSummarySchema.extend({
  content_md: z.string(),
  event_ids: z.array(z.number()),
});

export const DigestListSchema = z.array(DigestSummarySchema);

export type DigestSummary = z.infer<typeof DigestSummarySchema>;
export type Digest = z.infer<typeof DigestSchema>;

export function fetchDigests(): Promise<DigestSummary[]> {
  return apiGet("/digests", DigestListSchema);
}

export function fetchDigest(id: number): Promise<Digest> {
  return apiGet(`/digests/${id}`, DigestSchema);
}
