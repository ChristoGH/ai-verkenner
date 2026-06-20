import { describe, expect, it, vi } from "vitest";
import { screen, fireEvent } from "@testing-library/react";
import { renderWithProviders } from "@/test/render";

// --- Mock the API modules (dynamic import inside factory: vi.mock is hoisted) ---
vi.mock("@/api/items", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/items")>();
  const { sampleItem } = await import("@/test/fixtures");
  return { ...actual, fetchItems: vi.fn(async () => [sampleItem]) };
});
vi.mock("@/api/horizon", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/horizon")>();
  const { sampleHorizonItem } = await import("@/test/fixtures");
  return {
    ...actual,
    fetchHorizon: vi.fn(async () => ({ items: [sampleHorizonItem], graph_available: true })),
  };
});
vi.mock("@/api/graph", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/graph")>();
  const { sampleGraph } = await import("@/test/fixtures");
  return { ...actual, fetchGraph: vi.fn(async () => sampleGraph) };
});

// --- Mock the WebGL Cosmograph wrapper (doesn't run under jsdom) ---
vi.mock("@/components/CosmographView", () => ({
  CosmographView: ({ onSelectEntity }: { onSelectEntity: (n: { label: string }) => void }) => (
    <button onClick={() => onSelectEntity({ label: "RAG" })}>select-RAG</button>
  ),
}));

import { Items } from "@/pages/Items";
import { Horizon } from "@/pages/Horizon";
import { Graph } from "@/pages/Graph";

describe("Items page", () => {
  it("renders the ranked feed from /items", async () => {
    renderWithProviders(<Items />);
    expect(await screen.findByText("OpenAI ships GPT-5")).toBeInTheDocument();
    // Priority filter is present.
    expect(screen.getByRole("button", { name: "Horizon" })).toBeInTheDocument();
  });
});

describe("Horizon page", () => {
  it("renders the weak-signal quadrant with convergence + contributing sources", async () => {
    renderWithProviders(<Horizon />);
    expect(await screen.findByText("A quietly converging RAG technique")).toBeInTheDocument();
    expect(screen.getByText(/convergence 5/)).toBeInTheDocument();
    expect(screen.getByText("arXiv cs.CL")).toBeInTheDocument();
    expect(screen.getByText(/convergence: 'RAG' across 5 sources/)).toBeInTheDocument();
  });
});

describe("Graph page", () => {
  it("renders Cosmograph and clicking an entity filters the items list", async () => {
    renderWithProviders(<Graph />);
    // Cosmograph (mocked) renders once the /graph data loads.
    const select = await screen.findByRole("button", { name: "select-RAG" });
    fireEvent.click(select);
    // The entity drilldown appears, with the filtered items beneath it.
    expect(await screen.findByText(/Items mentioning/)).toBeInTheDocument();
    expect(await screen.findByText("OpenAI ships GPT-5")).toBeInTheDocument();
  });
});
