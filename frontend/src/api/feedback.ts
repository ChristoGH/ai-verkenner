import { z } from "zod";
import { apiPost } from "./client";

/**
 * POST /items/{id}/feedback (M7). The item id is the Event id; the action folds into ranking
 * transparently (useful/save lift, not_useful demote, ignore removes from the default feed) without
 * changing the priority class.
 */
export const FEEDBACK_ACTIONS = ["useful", "not_useful", "save", "ignore"] as const;
export type FeedbackAction = (typeof FEEDBACK_ACTIONS)[number];

export const FeedbackSchema = z.object({
  id: z.number(),
  event_id: z.number(),
  action: z.string(),
  created_at: z.string(),
});

export type Feedback = z.infer<typeof FeedbackSchema>;

export function postFeedback(itemId: string, action: FeedbackAction): Promise<Feedback> {
  return apiPost(`/items/${itemId}/feedback`, { action }, FeedbackSchema);
}
