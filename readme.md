# AI-Health-Udgam: Core Engine

This Branch contains the core cognitive engine ("The Brain") for **AI-Health-Udgam**. It is a lightweight, modular backend designed to process health queries using a **3-Step Reasoning & Action (ReAct)** loop.

Instead of answering blindly, the Brain "thinks," searches the web for real-time medical data, and then synthesizes a safe, evidence-backed response.

##  Key Features

* **Modular LLM Wrapper (`llm.py`):** A clean abstraction for handling AI model calls (supports switching between models easily).
* **Active Reasoning Engine (`loop.py`):** Implements a "Think -> Act -> Observe" cycle to verify symptoms and treatments before answering.
* **Real-Time Medical Search (`search.py`):** Integrated web search tools to fetch the latest health guidelines and drug information.
* **Safety First (`prompts.py`):** specialized system prompts that enforce medical disclaimers and guardrails against dangerous advice.
* **Structured Data (`model.py`):** Uses Pydantic models to ensure strictly typed inputs and outputs.

---

##  Project Structure

The project logic is contained entirely within the `core/` directory:

```text
ai-health-udgam/
├── core/
│   ├── llm.py           # Wrapper class for LLM API calls (OpenAI/Anthropic)
│   ├── loop.py          # The main 3-step Reasoning Engine (Think-Act-Observe)
│   ├── search.py        # Functions to execute Web Search (Google/Exa.ai)
│   ├── prompts.py       # System prompts, templates, and safety guardrails
│   └── model.py         # Data structures (Pydantic models) for validation
├── main.py              # Entry point to run the Brain locally
├── requirements.txt     # Python dependencies
└── .env                 # API Keys (GitIgnored)
