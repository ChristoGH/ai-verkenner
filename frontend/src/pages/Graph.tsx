import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchGraph } from "@/api/graph";
import { CosmographView } from "@/components/CosmographView";
import { ItemsFeed } from "@/components/ItemsFeed";

/**
 * The Cosmograph view (M6): the knowledge graph as a network + timeline, capped to events + top
 * entities so it stays readable. Clicking an entity filters the Items list below it.
 */
export function Graph() {
  const [entity, setEntity] = useState<string | null>(null);
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["graph"],
    queryFn: () => fetchGraph({ limit: 150 }),
  });

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Graph</h1>
        <p className="text-sm text-muted-foreground">
          The knowledge graph — events and the entities they converge on. Click an entity to filter
          the items below.
        </p>
      </div>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading graph…</p>
      ) : isError ? (
        <p className="text-sm text-red-600">Failed to load graph: {(error as Error).message}</p>
      ) : !data || !data.available ? (
        <div className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
          The graph is unavailable — Neo4j is unreachable. Bring it up with{" "}
          <code>docker compose up neo4j</code> and run <code>python -m app.cli run</code>.
        </div>
      ) : data.nodes.length === 0 ? (
        <div className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
          No graph yet. Run <code>python -m app.cli run</code> to project entities + events.
        </div>
      ) : (
        <>
          <CosmographView
            nodes={data.nodes}
            links={data.links}
            onSelectEntity={(node) => setEntity(node.label)}
          />
          {data.truncated ? (
            <p className="text-xs text-muted-foreground">
              Showing the top {data.nodes.length} nodes (capped for legibility).
            </p>
          ) : null}
        </>
      )}

      {entity ? (
        <div className="space-y-3 border-t pt-4">
          <div className="flex items-center gap-2 text-sm">
            <span className="rounded-md bg-muted px-2 py-1">
              Items mentioning <span className="font-medium">{entity}</span>
            </span>
            <button className="text-blue-600 hover:underline" onClick={() => setEntity(null)}>
              clear
            </button>
          </div>
          <ItemsFeed entity={entity} showFilter={false} />
        </div>
      ) : null}
    </div>
  );
}
