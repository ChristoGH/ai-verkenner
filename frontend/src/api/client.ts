import { z } from "zod";

export const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";

/**
 * Typed fetch helper. Performs the request, then parses the JSON response through the supplied
 * Zod schema so nothing untyped escapes the API layer.
 */
export async function apiGet<T>(path: string, schema: z.ZodType<T>): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status} ${res.statusText}`);
  }
  const data = await res.json();
  return schema.parse(data);
}

/**
 * Typed POST helper. Sends a JSON body, then parses the JSON response through the supplied Zod
 * schema so nothing untyped escapes the API layer.
 */
export async function apiPost<T>(path: string, body: unknown, schema: z.ZodType<T>): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status} ${res.statusText}`);
  }
  const data = await res.json();
  return schema.parse(data);
}
