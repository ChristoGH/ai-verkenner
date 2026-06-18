import { z } from "zod";
import { apiGet } from "./client";

export const HealthSchema = z.object({
  status: z.string(),
  service: z.string().optional(),
  version: z.string().optional(),
});

export type Health = z.infer<typeof HealthSchema>;

export function fetchHealth(): Promise<Health> {
  return apiGet("/health", HealthSchema);
}
