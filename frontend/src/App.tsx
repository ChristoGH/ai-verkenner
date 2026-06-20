import { Suspense, lazy } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { cn } from "@/lib/utils";
import { Dashboard } from "@/pages/Dashboard";
import { Items } from "@/pages/Items";
import { Horizon } from "@/pages/Horizon";
import { Sources } from "@/pages/Sources";
import { Digests } from "@/pages/Digests";
import { Settings } from "@/pages/Settings";

// Code-split the Graph route — Cosmograph (WebGL) is heavy and only needed here.
const Graph = lazy(() => import("@/pages/Graph").then((m) => ({ default: m.Graph })));

const NAV = [
  { to: "/", label: "Core Radar", end: true },
  { to: "/items", label: "Items", end: false },
  { to: "/horizon", label: "Horizon", end: false },
  { to: "/graph", label: "Graph", end: false },
  { to: "/sources", label: "Sources", end: false },
  { to: "/digests", label: "Digests", end: false },
  { to: "/settings", label: "Settings", end: false },
];

export default function App() {
  return (
    <div className="min-h-screen">
      <header className="border-b">
        <div className="mx-auto flex max-w-5xl items-center gap-6 px-4 py-3">
          <span className="font-semibold">AI Verkenner</span>
          <nav className="flex gap-1">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  cn(
                    "rounded-md px-3 py-1.5 text-sm transition-colors",
                    isActive ? "bg-muted font-medium" : "text-muted-foreground hover:bg-muted"
                  )
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/items" element={<Items />} />
          <Route path="/horizon" element={<Horizon />} />
          <Route
            path="/graph"
            element={
              <Suspense fallback={<p className="text-sm text-muted-foreground">Loading graph…</p>}>
                <Graph />
              </Suspense>
            }
          />
          <Route path="/sources" element={<Sources />} />
          <Route path="/digests" element={<Digests />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}
