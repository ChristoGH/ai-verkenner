import { z } from "zod";
import { apiGet } from "./client";

// Per-store reachability reported by GET /health (M2). Kept permissive (z.string) so a new or
// renamed status value never breaks parsing; known values are "ok" | "unreachable".
export const DependenciesSchema = z
  .object({
    qdrant: z.string(),
    neo4j: z.string(),
  })
  .partial();

export const HealthSchema = z.object({
  status: z.string(),
  service: z.string().optional(),
  version: z.string().optional(),
  // Additive and optional — pre-M2 responses (no dependencies) still parse.
  dependencies: DependenciesSchema.optional(),
});

export type Health = z.infer<typeof HealthSchema>;

export function fetchHealth(): Promise<Health> {
  return apiGet("/health", HealthSchema);
}
