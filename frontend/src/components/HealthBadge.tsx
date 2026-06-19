import { useQuery } from "@tanstack/react-query";
import { Activity, AlertTriangle, WifiOff } from "lucide-react";
import { fetchHealth } from "@/api/health";
import { Badge } from "@/components/ui/badge";

/**
 * Polls GET /health every 30s and renders one of three states:
 *   OK         — backend reachable and reporting status "ok"
 *   degraded   — backend reachable but not "ok"
 *   unreachable — request failed
 */
export function HealthBadge() {
  const { data, isError, isLoading } = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    refetchInterval: 30000,
    retry: false,
  });

  if (isLoading) {
    return (
      <Badge variant="secondary">
        <Activity className="mr-1 h-3 w-3 animate-pulse" />
        Checking…
      </Badge>
    );
  }

  if (isError) {
    return (
      <Badge variant="danger">
        <WifiOff className="mr-1 h-3 w-3" />
        Backend unreachable
      </Badge>
    );
  }

  if (data?.status === "ok") {
    // Surface any derived store that is reachable-down (M2). The backend itself is still OK.
    const downStores = Object.entries(data.dependencies ?? {})
      .filter(([, status]) => status !== "ok")
      .map(([name]) => name);

    if (downStores.length > 0) {
      return (
        <Badge variant="warning">
          <AlertTriangle className="mr-1 h-3 w-3" />
          Backend OK · {downStores.join(", ")} unreachable
        </Badge>
      );
    }

    return (
      <Badge variant="success">
        <Activity className="mr-1 h-3 w-3" />
        Backend OK
        {data.version ? <span className="ml-1 opacity-80">v{data.version}</span> : null}
      </Badge>
    );
  }

  return (
    <Badge variant="warning">
      <AlertTriangle className="mr-1 h-3 w-3" />
      Backend degraded
    </Badge>
  );
}
