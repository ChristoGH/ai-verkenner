import { useQuery } from "@tanstack/react-query";
import { ExternalLink, TrendingUp } from "lucide-react";
import { fetchHorizon, type HorizonItem } from "@/api/horizon";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

/**
 * The Horizon page (M6) — the project's reason to exist. The weak-signal quadrant
 * (horizon_signal/archive) ranked by **graph convergence**: quietly-emerging developments that the
 * class-first Core Radar buries. Each card shows its evidence — the `why` and the contributing
 * sources — so the "Weak Signal of the Week" is reachable.
 */
function HorizonCard({ item }: { item: HorizonItem }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <h3 className="text-base font-semibold leading-snug">{item.title}</h3>
          <Badge variant="warning">convergence {item.convergence}</Badge>
        </div>
        <div className="text-xs text-muted-foreground">
          {item.source_name}
          {item.published_at ? ` · ${item.published_at.slice(0, 10)}` : ""}
        </div>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        {item.graph_why ? (
          <div className="flex items-start gap-1.5 rounded-md bg-amber-50 px-2 py-1.5 text-xs text-amber-800">
            <TrendingUp className="mt-0.5 h-3 w-3 shrink-0" />
            <span>{item.graph_why}</span>
          </div>
        ) : null}

        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Summary (source fact)
          </div>
          <p>{item.summary}</p>
        </div>

        {item.contributing_sources.length > 0 ? (
          <div>
            <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Contributing sources ({item.contributing_sources.length})
            </div>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {item.contributing_sources.map((s) => (
                <Badge key={s} variant="outline">
                  {s}
                </Badge>
              ))}
            </div>
          </div>
        ) : null}

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
    </Card>
  );
}

export function Horizon() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["horizon"],
    queryFn: () => fetchHorizon(50),
  });

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Horizon</h1>
        <p className="text-sm text-muted-foreground">
          Weak signals — the low-relevance quadrant ranked by graph convergence (distinct sources
          quietly pointing the same way). Not the Core Radar order.
        </p>
      </div>

      {data && !data.graph_available ? (
        <div className="rounded-md border border-dashed p-3 text-xs text-muted-foreground">
          Neo4j is unreachable — showing the weak-signal quadrant without convergence ranking.
        </div>
      ) : null}

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading horizon…</p>
      ) : isError ? (
        <p className="text-sm text-red-600">Failed to load horizon: {(error as Error).message}</p>
      ) : !data || data.items.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No weak signals yet. Run <code>python -m app.cli run</code> to populate the graph.
        </p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {data.items.map((item) => (
            <HorizonCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
