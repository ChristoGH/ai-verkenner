import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ItemsFeed } from "@/components/ItemsFeed";
import type { PriorityClass } from "@/api/items";

export function Items() {
  const [priority, setPriority] = useState<PriorityClass | "all">("all");
  // An ?entity=… param (set by clicking a Cosmograph node) filters the feed to that entity.
  const [searchParams, setSearchParams] = useSearchParams();
  const entity = searchParams.get("entity") ?? undefined;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Items</h1>
        <p className="text-sm text-muted-foreground">
          The full, filterable enriched feed (GET /items).
        </p>
      </div>

      {entity ? (
        <div className="flex items-center gap-2 text-sm">
          <span className="rounded-md bg-muted px-2 py-1">
            Filtered by entity: <span className="font-medium">{entity}</span>
          </span>
          <button
            className="text-blue-600 hover:underline"
            onClick={() => {
              searchParams.delete("entity");
              setSearchParams(searchParams);
            }}
          >
            clear
          </button>
        </div>
      ) : null}

      <ItemsFeed
        entity={entity}
        priorityFilter={priority}
        onPriorityChange={setPriority}
      />
    </div>
  );
}
