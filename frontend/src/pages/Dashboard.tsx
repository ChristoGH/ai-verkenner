import { HealthBadge } from "@/components/HealthBadge";
import { ItemCard } from "@/components/ItemCard";

export function Dashboard() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Core Radar</h1>
          <p className="text-sm text-muted-foreground">
            What happened across your trusted sources. Ranked items arrive in Task 006.
          </p>
        </div>
        <HealthBadge />
      </div>

      <div className="rounded-md border border-dashed p-3 text-sm text-muted-foreground">
        Placeholder feed — the card below illustrates the intended layout. No data is wired yet.
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <ItemCard />
      </div>
    </div>
  );
}
