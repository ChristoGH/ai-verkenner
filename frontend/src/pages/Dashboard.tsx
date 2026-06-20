import { useState } from "react";
import { HealthBadge } from "@/components/HealthBadge";
import { ItemsFeed } from "@/components/ItemsFeed";
import type { PriorityClass } from "@/api/items";

export function Dashboard() {
  const [priority, setPriority] = useState<PriorityClass | "all">("all");
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Core Radar</h1>
          <p className="text-sm text-muted-foreground">
            What happened across your trusted sources — ranked by priority class, then hype-aware
            salience and graph convergence.
          </p>
        </div>
        <HealthBadge />
      </div>

      <ItemsFeed priorityFilter={priority} onPriorityChange={setPriority} />
    </div>
  );
}
