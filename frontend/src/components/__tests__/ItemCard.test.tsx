import { describe, expect, it, vi } from "vitest";
import { screen, fireEvent, waitFor } from "@testing-library/react";
import { renderWithProviders } from "@/test/render";
import { sampleItem } from "@/test/fixtures";

// Mock the feedback POST so the wired buttons don't hit the network. `vi.hoisted` makes the spy
// available to the hoisted `vi.mock` factory.
const { postFeedback } = vi.hoisted(() => ({
  postFeedback: vi.fn(async () => ({
    id: 1,
    event_id: 1,
    action: "useful",
    created_at: "2026-06-22T00:00:00+00:00",
  })),
}));
vi.mock("@/api/feedback", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/feedback")>();
  return { ...actual, postFeedback };
});

import { ItemCard } from "@/components/ItemCard";

describe("ItemCard", () => {
  it("renders all fields, keeping fact separate from interpretation", () => {
    renderWithProviders(<ItemCard item={sampleItem} />);

    expect(screen.getByText(sampleItem.title)).toBeInTheDocument();
    expect(screen.getByText(/OpenAI Blog/)).toBeInTheDocument();
    expect(screen.getByText("Operational update")).toBeInTheDocument();
    expect(screen.getByText(/Summary \(source fact\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Why it matters \(interpretation\)/i)).toBeInTheDocument();
    expect(screen.getByText(sampleItem.summary)).toBeInTheDocument();
    expect(screen.getByText(sampleItem.why_it_matters)).toBeInTheDocument();
    expect(screen.getByText(sampleItem.recommended_action)).toBeInTheDocument();
    expect(screen.getByText(/relevance 4/)).toBeInTheDocument();
    expect(screen.getByText(/hype 1 \(0=signal\)/)).toBeInTheDocument();
    expect(screen.getByText(/convergence: 'RAG' across 4 sources/)).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /source/i });
    expect(link).toHaveAttribute("href", sampleItem.source_url);
  });

  it("posts feedback when a button is clicked (M7)", async () => {
    renderWithProviders(<ItemCard item={sampleItem} />);
    const useful = screen.getByRole("button", { name: "Useful" });
    expect(useful).toBeEnabled();

    fireEvent.click(useful);
    await waitFor(() => expect(postFeedback).toHaveBeenCalledWith(sampleItem.id, "useful"));
    expect(await screen.findByText(/Saved/)).toBeInTheDocument();
  });
});
