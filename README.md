# Ecommerce Voicebot with Agentic AI

## Overview

This project implements a **real-time AI-powered Ecommerce Voicebot** using **Agentic AI architecture**.  
The system allows users to interact with an ecommerce platform via **voice or text** to:

- Search products
- Get product recommendations
- Ask FAQs and policy questions
- Track orders (with authentication checks)
- Request human agent escalation

The project demonstrates **agent orchestration, RAG, knowledge graphs, memory, observability, and voice AI**, aligned with concepts taught in the Generative AI & Agentic AI course.

---

## Core Capabilities

### 1. Voice & Text Interaction
- WebSocket-based voice interaction
- STT → Agent → TTS pipeline
- Text fallback via REST API

### 2. Agentic Architecture
- Planner → Executor → Evaluator → Reflexion
- Task-based execution with MCP-style tool calls
- Safe fallbacks and clarification handling

### 3. Retrieval-Augmented Generation (RAG)
- Vector search using Chroma
- Product, FAQ, and Policy retrieval
- Constraint-aware selection (color, size, price)

### 4. Knowledge Graph (Neo4j)
- Product similarity using graph traversal
- Explicit relationships: Product → Material → Price Band
- Used for “similar products” recommendations

### 5. Session Memory
- Implicit follow-ups (e.g., “What is the price?”)
- Last product tracking across turns
- Context-aware responses

### 6. Order Tracking with Authentication
- Order status retrieval from PostgreSQL
- Session-based authentication checks
- Safe refusal for unauthenticated users

### 7. Observability & Monitoring
- Prometheus metrics (requests, latency, STT, LLM)
- Grafana dashboards
- LangSmith tracing for agent execution
- Helicone integration for OpenAI call observability (best-effort)

---

## Tech Stack

- **Backend:** Python, FastAPI
- **Agent Framework:** Custom AutoGen-style orchestration
- **LLM:** OpenAI (Chat Completions)
- **STT:** Whisper
- **TTS:** WAV streaming over WebSocket
- **Vector Store:** Chroma
- **Knowledge Graph:** Neo4j
- **Database:** PostgreSQL
- **Observability:** Prometheus, Grafana, LangSmith, Helicone

---

## Project Structure (High Level)

backend/
├── agents/ # Planner, Executor, Evaluator
├── core/ # App entrypoint, LLM client
├── rag/ # Vector search logic
├── graph/ # Neo4j similarity queries
├── observability/ # Metrics & tracing
├── data/ # Demo datasets
├── tools/ # MCP middleware and server
frontend/
├── index.html # Voice UI


---

## Demo Use Cases Covered

1. Product search via voice
2. Ambiguous query → clarification
3. Similar product recommendations (KG)
4. In-session memory follow-up
5. FAQ query
6. Policy query
7. Order tracking (authenticated)
8. Human agent escalation
9. PII-safe handling

---

## Known Limitations / Future Improvements

- Helicone logging works intermittently after recent refactors and needs further debugging.
- STT and LLM metrics require explicit `.inc()` instrumentation coverage verification.
- UI can be further polished for production readiness.
- Retry and cost-guardrails can be expanded for large-scale deployment.

---

## Author

**Mitalee Bakare**  
Capstone Project — Generative AI & Agentic AI Development  
Boston Institute of Analysis
