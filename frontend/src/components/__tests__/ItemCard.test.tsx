import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ItemCard } from "@/components/ItemCard";
import { sampleItem } from "@/test/fixtures";

describe("ItemCard", () => {
  it("renders all fields, keeping fact separate from interpretation", () => {
    render(<ItemCard item={sampleItem} />);

    expect(screen.getByText(sampleItem.title)).toBeInTheDocument();
    expect(screen.getByText(/OpenAI Blog/)).toBeInTheDocument();
    // Priority badge.
    expect(screen.getByText("Operational update")).toBeInTheDocument();
    // Fact vs interpretation are labelled separately.
    expect(screen.getByText(/Summary \(source fact\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Why it matters \(interpretation\)/i)).toBeInTheDocument();
    expect(screen.getByText(sampleItem.summary)).toBeInTheDocument();
    expect(screen.getByText(sampleItem.why_it_matters)).toBeInTheDocument();
    expect(screen.getByText(sampleItem.recommended_action)).toBeInTheDocument();
    // Scores incl. the inverted-hype label.
    expect(screen.getByText(/relevance 4/)).toBeInTheDocument();
    expect(screen.getByText(/hype 1 \(0=signal\)/)).toBeInTheDocument();
    // The graph "why".
    expect(screen.getByText(/convergence: 'RAG' across 4 sources/)).toBeInTheDocument();
    // Source link preserved.
    const link = screen.getByRole("link", { name: /source/i });
    expect(link).toHaveAttribute("href", sampleItem.source_url);
  });

  it("renders inert feedback buttons (wired in M7)", () => {
    render(<ItemCard item={sampleItem} />);
    expect(screen.getByRole("button", { name: "Useful" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
  });
});
