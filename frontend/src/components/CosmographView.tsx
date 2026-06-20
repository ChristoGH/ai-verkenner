import {
  Cosmograph,
  CosmographProvider,
  CosmographSearch,
  CosmographTimeline,
} from "@cosmograph/react";
import type { GraphLink, GraphNode } from "@/api/graph";

/**
 * The Cosmograph network + timeline + search (M6). GPU/WebGL rendering of the /graph projection.
 *
 * Kept thin and isolated: the data fetching, the "click an entity → filter the Items list"
 * behaviour, and the page shell live in the Graph page; this component only renders the canvas and
 * reports entity clicks/search selections. Tests mock this module (WebGL doesn't run under jsdom).
 *
 * Accessor params are cast to our node/link types — Cosmograph's generics don't infer through the
 * provider context, and this keeps the typed surface honest at the call sites.
 */
const ENTITY_TYPE_COLOR: Record<string, string> = {
  org: "#2563eb",
  model: "#7c3aed",
  person: "#db2777",
  tool: "#059669",
  concept: "#d97706",
};

function nodeColor(node: GraphNode): string {
  if (node.kind === "event") return "#94a3b8";
  return (node.type && ENTITY_TYPE_COLOR[node.type]) || "#0ea5e9";
}

export function CosmographView({
  nodes,
  links,
  onSelectEntity,
}: {
  nodes: GraphNode[];
  links: GraphLink[];
  onSelectEntity: (node: GraphNode) => void;
}) {
  const handleSelect = (node?: GraphNode) => {
    if (node && node.kind === "entity") onSelectEntity(node);
  };

  return (
    <CosmographProvider nodes={nodes} links={links}>
      <div className="relative h-[480px] w-full overflow-hidden rounded-lg border bg-slate-950">
        <Cosmograph
          nodeLabelAccessor={(n) => (n as GraphNode).label}
          nodeColor={(n) => nodeColor(n as GraphNode)}
          nodeSize={(n) => ((n as GraphNode).kind === "event" ? 3 : 5)}
          linkColor={() => "rgba(148,163,184,0.4)"}
          linkWidth={1}
          simulationGravity={0.2}
          simulationRepulsion={1}
          simulationLinkDistance={8}
          onClick={(node) => handleSelect(node as GraphNode | undefined)}
        />
        <div className="absolute right-2 top-2 z-10 w-56">
          <CosmographSearch onSelectResult={(node) => handleSelect(node as GraphNode | undefined)} />
        </div>
      </div>
      <CosmographTimeline
        filterType="links"
        accessor={(d) => {
          const ts = (d as GraphLink).ts;
          return ts ? new Date(ts) : new Date(0);
        }}
      />
    </CosmographProvider>
  );
}
