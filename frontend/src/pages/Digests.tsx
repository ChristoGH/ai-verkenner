import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Network } from "lucide-react";
import { fetchDigest, fetchDigests, type DigestSummary } from "@/api/digests";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { cn } from "@/lib/utils";

function periodLabel(d: DigestSummary): string {
  const s = d.period_start ? d.period_start.slice(0, 10) : "?";
  const e = d.period_end ? d.period_end.slice(0, 10) : "?";
  return `${s} → ${e}`;
}

/**
 * Digests page (M7) — the decision-oriented weekly briefings. Lists stored digests (newest first)
 * and renders the selected one. Each digest is composed over already-enriched Events, with its
 * weak-signals section drawn from the hub-dampened convergence. Generate one with
 * `python -m app.cli digest`.
 */
export function Digests() {
  const list = useQuery({ queryKey: ["digests"], queryFn: fetchDigests });
  const [selected, setSelected] = useState<number | null>(null);
  const activeId = selected ?? list.data?.[0]?.id ?? null;

  const detail = useQuery({
    queryKey: ["digest", activeId],
    queryFn: () => fetchDigest(activeId as number),
    enabled: activeId != null,
  });

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Digests</h1>
        <p className="text-sm text-muted-foreground">
          Decision-oriented weekly briefings — composed over enriched events, with weak signals drawn
          from graph convergence. Not a link list.
        </p>
      </div>

      {list.isLoading ? (
        <p className="text-sm text-muted-foreground">Loading digests…</p>
      ) : list.isError ? (
        <p className="text-sm text-red-600">
          Failed to load digests: {(list.error as Error).message}
        </p>
      ) : !list.data || list.data.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No digests yet. Generate one with <code>python -m app.cli digest</code>.
        </p>
      ) : (
        <div className="grid gap-4 md:grid-cols-[16rem_1fr]">
          <ul className="space-y-1">
            {list.data.map((d) => (
              <li key={d.id}>
                <button
                  onClick={() => setSelected(d.id)}
                  className={cn(
                    "w-full rounded-md border px-3 py-2 text-left text-sm transition-colors",
                    d.id === activeId ? "bg-muted font-medium" : "hover:bg-muted"
                  )}
                >
                  <div>{periodLabel(d)}</div>
                  <div className="mt-0.5 flex flex-wrap gap-1 text-xs text-muted-foreground">
                    <Badge variant="outline">{d.method}</Badge>
                    {d.graphrag ? (
                      <Badge variant="outline">
                        <Network className="mr-1 h-3 w-3" />
                        GraphRAG
                      </Badge>
                    ) : null}
                    <Badge variant="secondary">{d.noise_count} noise</Badge>
                  </div>
                </button>
              </li>
            ))}
          </ul>

          <Card>
            <CardHeader>
              {detail.data ? (
                <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                  <span>Generated {detail.data.generated_at.slice(0, 10)}</span>
                  <Badge variant="outline">{detail.data.item_count} in body</Badge>
                  <Badge variant="secondary">{detail.data.noise_count} noise</Badge>
                  <Badge variant="outline">{detail.data.event_ids.length} sources</Badge>
                </div>
              ) : null}
            </CardHeader>
            <CardContent>
              {detail.isLoading ? (
                <p className="text-sm text-muted-foreground">Loading digest…</p>
              ) : detail.data ? (
                <article className="whitespace-pre-wrap text-sm leading-relaxed">
                  {detail.data.content_md}
                </article>
              ) : (
                <p className="text-sm text-muted-foreground">Select a digest.</p>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
