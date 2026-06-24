import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ExternalLink, Network } from "lucide-react";
import type { Item, PriorityClass } from "@/api/items";
import { type FeedbackAction, postFeedback } from "@/api/feedback";
import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";

const PRIORITY_LABEL: Record<PriorityClass, string> = {
  immediate_priority: "Immediate priority",
  operational_update: "Operational update",
  horizon_signal: "Horizon signal",
  archive: "Archive",
};

const PRIORITY_VARIANT: Record<PriorityClass, BadgeProps["variant"]> = {
  immediate_priority: "danger",
  operational_update: "default",
  horizon_signal: "warning",
  archive: "secondary",
};

/**
 * Real EnrichedItem card (M6), wired to GET /items via the Zod-validated client.
 *
 * Invariants made visible: SOURCE FACT (summary) is kept distinct from INTERPRETATION
 * (why-it-matters / recommended action); the five scores show with hype labelled inverted; the
 * source link is always shown; and when the graph signal fired, its `why` is surfaced. The feedback
 * buttons (M7) POST to /items/{id}/feedback and refresh the ranked feed (an `ignore`d item leaves
 * the default feed; useful/save lift, not_useful demotes — all within the priority class).
 */
export function ItemCard({ item }: { item: Item }) {
  const { scores } = item;
  const queryClient = useQueryClient();
  const feedback = useMutation({
    mutationFn: (action: FeedbackAction) => postFeedback(item.id, action),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["items"] }),
  });
  const submitted = feedback.isSuccess ? feedback.variables : undefined;
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <h3 className="text-base font-semibold leading-snug">{item.title}</h3>
          <Badge variant={PRIORITY_VARIANT[item.priority_class]}>
            {PRIORITY_LABEL[item.priority_class]}
          </Badge>
        </div>
        <div className="text-xs text-muted-foreground">
          {item.source_name}
          {item.published_at ? ` · ${item.published_at.slice(0, 10)}` : ""}
        </div>
      </CardHeader>

      <CardContent className="space-y-3 text-sm">
        {item.graph_why ? (
          <div className="flex items-start gap-1.5 rounded-md bg-amber-50 px-2 py-1.5 text-xs text-amber-800">
            <Network className="mt-0.5 h-3 w-3 shrink-0" />
            <span>{item.graph_why}</span>
          </div>
        ) : null}

        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Summary (source fact)
          </div>
          <p>{item.summary}</p>
        </div>
        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Why it matters (interpretation)
          </div>
          <p>{item.why_it_matters}</p>
        </div>
        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Recommended action
          </div>
          <p>{item.recommended_action}</p>
        </div>

        <div className="flex flex-wrap gap-1.5 pt-1">
          <Badge variant="outline">relevance {scores.relevance}</Badge>
          <Badge variant="outline">novelty {scores.novelty}</Badge>
          <Badge variant="outline">actionability {scores.actionability}</Badge>
          <Badge variant="outline">strategic {scores.strategic_potential}</Badge>
          <Badge variant="outline">hype {scores.hype} (0=signal)</Badge>
        </div>

        <a
          href={item.source_url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
        >
          <ExternalLink className="h-3 w-3" />
          Source
        </a>
      </CardContent>

      <CardFooter className="flex flex-wrap items-center gap-2">
        {/* Feedback buttons (M7) — POST /items/{id}/feedback, then refresh the ranked feed. */}
        <Button
          size="sm"
          variant={submitted === "useful" ? "default" : "outline"}
          disabled={feedback.isPending}
          onClick={() => feedback.mutate("useful")}
        >
          Useful
        </Button>
        <Button
          size="sm"
          variant={submitted === "not_useful" ? "default" : "outline"}
          disabled={feedback.isPending}
          onClick={() => feedback.mutate("not_useful")}
        >
          Not useful
        </Button>
        <Button
          size="sm"
          variant={submitted === "save" ? "default" : "outline"}
          disabled={feedback.isPending}
          onClick={() => feedback.mutate("save")}
        >
          Save
        </Button>
        <Button
          size="sm"
          variant="ghost"
          disabled={feedback.isPending}
          onClick={() => feedback.mutate("ignore")}
        >
          Ignore
        </Button>
        {feedback.isError ? (
          <span className="text-xs text-red-600">Couldn’t save feedback.</span>
        ) : submitted ? (
          <span className="text-xs text-muted-foreground">Saved “{submitted}”.</span>
        ) : null}
      </CardFooter>
    </Card>
  );
}
