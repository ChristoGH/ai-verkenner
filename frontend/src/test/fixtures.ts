import type { Item } from "@/api/items";
import type { HorizonItem } from "@/api/horizon";
import type { GraphData } from "@/api/graph";

export const sampleItem: Item = {
  id: "1",
  title: "OpenAI ships GPT-5",
  source_name: "OpenAI Blog",
  source_url: "https://openai.com/blog/gpt-5",
  published_at: "2026-06-18T09:00:00+00:00",
  priority_class: "operational_update",
  category: "model_release",
  tags: ["llm", "openai"],
  scores: {
    relevance: 4,
    novelty: 5,
    actionability: 3,
    strategic_potential: 4,
    hype: 1,
  },
  summary: "OpenAI announced GPT-5 today. (Source fact.)",
  why_it_matters: "Could matter for the user's LLM tooling. (Interpretation.)",
  recommended_action: "Evaluate it this week.",
  is_weak_signal: false,
  horizon: null,
  graph_why: "convergence: 'RAG' across 4 sources",
  convergence: 4,
};

export const sampleHorizonItem: HorizonItem = {
  ...sampleItem,
  id: "2",
  title: "A quietly converging RAG technique",
  priority_class: "horizon_signal",
  graph_why: "convergence: 'RAG' across 5 sources",
  convergence: 5,
  graph_score: 5.8,
  contributing_sources: ["arXiv cs.CL", "Simon Willison", "LangChain Blog"],
};

export const sampleGraph: GraphData = {
  nodes: [
    { id: "entity:1", label: "RAG", kind: "entity", type: "concept" },
    { id: "entity:2", label: "Qdrant", kind: "entity", type: "tool" },
    { id: "event:1", label: "RAG convergence", kind: "event", priority_class: "horizon_signal" },
  ],
  links: [
    { source: "entity:2", target: "entity:1", kind: "interacts", ts: "2026-06-18T00:00:00+00:00" },
    { source: "event:1", target: "entity:1", kind: "mentions", ts: "2026-06-18T00:00:00+00:00" },
  ],
  truncated: false,
  available: true,
};
