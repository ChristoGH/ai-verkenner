import { useQuery } from "@tanstack/react-query";
import { fetchItems, type PriorityClass } from "@/api/items";
import { ItemCard } from "@/components/ItemCard";
import { cn } from "@/lib/utils";

const PRIORITY_FILTERS: { value: PriorityClass | "all"; label: string }[] = [
  { value: "all", label: "All" },
  { value: "immediate_priority", label: "Immediate" },
  { value: "operational_update", label: "Operational" },
  { value: "horizon_signal", label: "Horizon" },
  { value: "archive", label: "Archive" },
];

/**
 * Ranked Core Radar feed: items from GET /items (priority class first, then hype-aware salience +
 * graph signal), with an optional priority filter and an optional `entity` filter (used when the
 * Cosmograph view drills into one entity).
 */
export function ItemsFeed({
  entity,
  priorityFilter,
  onPriorityChange,
  showFilter = true,
}: {
  entity?: string;
  priorityFilter?: PriorityClass | "all";
  onPriorityChange?: (value: PriorityClass | "all") => void;
  showFilter?: boolean;
}) {
  const active = priorityFilter ?? "all";
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["items", active, entity ?? null],
    queryFn: () =>
      fetchItems({
        priorityClass: active === "all" ? undefined : active,
        entity,
      }),
  });

  return (
    <div className="space-y-4">
      {showFilter ? (
        <div className="flex flex-wrap gap-1.5">
          {PRIORITY_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => onPriorityChange?.(f.value)}
              className={cn(
                "rounded-md border px-2.5 py-1 text-xs transition-colors",
                active === f.value
                  ? "bg-muted font-medium"
                  : "text-muted-foreground hover:bg-muted"
              )}
            >
              {f.label}
            </button>
          ))}
        </div>
      ) : null}

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading items…</p>
      ) : isError ? (
        <p className="text-sm text-red-600">
          Failed to load items: {(error as Error).message}
        </p>
      ) : !data || data.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No items yet. Run <code>python -m app.cli run</code> to populate the radar.
        </p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {data.map((item) => (
            <ItemCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
