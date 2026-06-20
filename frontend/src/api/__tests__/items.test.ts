import { describe, expect, it } from "vitest";
import { ItemSchema } from "@/api/items";
import { sampleItem } from "@/test/fixtures";

describe("ItemSchema (Zod)", () => {
  it("parses a valid item payload", () => {
    const parsed = ItemSchema.parse(sampleItem);
    expect(parsed.id).toBe("1");
    expect(parsed.scores.hype).toBe(1);
  });

  it("rejects a malformed payload (bad priority_class)", () => {
    const bad = { ...sampleItem, priority_class: "not_a_class" };
    expect(() => ItemSchema.parse(bad)).toThrow();
  });

  it("rejects a payload missing the source_url", () => {
    const { source_url: _omit, ...bad } = sampleItem;
    expect(() => ItemSchema.parse(bad)).toThrow();
  });

  it("rejects a payload with a non-numeric score", () => {
    const bad = { ...sampleItem, scores: { ...sampleItem.scores, relevance: "high" } };
    expect(() => ItemSchema.parse(bad)).toThrow();
  });
});
