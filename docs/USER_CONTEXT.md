# USER_CONTEXT — who this radar is for

> Drafted from the Obsidian vault (`10-Projects/`, `20-Areas/`) on 2026-06-22. **Hand-edit this** —
> it is the ground truth AI Verkenner uses to score `relevance` and `connection_to_user_work`.
> Keep it current; it is the cheapest lever on output quality.

## Who

Christo Strydom — solo builder and PwC AI-platform engineer in South Africa, trading as **CS AI &
ML Consultancy (Pty) Ltd / KonteksWerke**. Runs many parallel build threads; ships RAG, knowledge-
graph, and LLM-application systems end to end.

## Active work (an item is relevant if it touches these)

- **ARQ Platform** (PwC) — 25+ containerised AI apps on **Azure Kubernetes (AKS)** with
  **Knative scale-to-zero**; **FastAPI**, hybrid **Qdrant + SQLite**. Open decision: **Lakebase
  pgvector vs Qdrant**.
- **repo_ingest** — production repo-to-vector-store pipeline: **tree-sitter** chunking,
  **Voyage/OpenAI embeddings**, **Qdrant** with incremental git-diff updates. RAG backbone across
  ARQ apps.
- **Commission Intelligence** — evidence-graph pipeline over SA commission-of-inquiry transcripts;
  **Qdrant + Neo4j + spaCy + Claude SDK + React**; an *evidence* graph (Mention ≠ Claim ≠ Finding ≠
  Fact). Same stack/philosophy as AI Verkenner.
- **AI Verkenner** — this project: personal AI intelligence / early-warning; Qdrant + Neo4j +
  Cosmograph + Claude.
- **MedVoice** — voice-assisted clinical documentation; **FastAPI, React, Firebase Auth, SQLite,
  Qdrant, Cloud Run, Google STT, Claude**; healthcare compliance.
- **BellBook** — school-comms PWA; React, **Clickatell** OTP, **Paystack/Ozow** payments (SA edtech).
- **SmartSolar** — Sunsynk inverter / home-energy optimisation with AI (MVP).

## Strong relevance signals (elevate)

Qdrant · Neo4j · GraphRAG / knowledge-graph extraction · vector-DB trade-offs (pgvector / Lakebase
/ Qdrant) · **Claude / Anthropic model + Agent SDK releases** · agentic frameworks · RAG techniques
· embeddings (Voyage, sentence-transformers, OpenAI) · FastAPI · React · **Cursor** · AKS / Knative
/ Cloud Run · entity/relationship extraction · South African tech & regulatory context.

## Weak relevance (demote)

Generic consumer-AI news, marketing/hype, funding-round noise, and frameworks/languages outside the
stack above — unless they intersect a strong signal.
