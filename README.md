# Nexus AI

**Live demo:** https://nexus-pro-ai.streamlit.app/

Nexus AI is a query-triage assistant that answers simple questions directly and
routes genuine trade-off decisions through a structured, multi-agent debate —
instead of sending every prompt through one generic LLM call.

---

## The problem this solves

Most single-model chatbots treat every question the same way: one prompt in, one
answer out. That works fine for facts, but falls apart on decisions — "should I
use X or Y?" questions where the right answer depends on unstated context, and a
single model pass tends to either hedge ("it depends") or commit to one option
without seriously engaging the other side.

Nexus AI splits these two cases apart and handles each on its own terms.

---

## How it works

```
User query
   │
   ▼
┌─────────────┐
│   Router    │  LLM3 classifies the query
└──────┬──────┘
       │
   ┌───┴────┐
   ▼        ▼
DIRECT   DECISION
   │        │
   │        ▼
   │   ┌─────────────────┐
   │   │  Clarification   │  LLM3 asks 2-3 questions
   │   │   (LLM3)          │  that would change the answer
   │   └────────┬─────────┘
   │            ▼
   │   ┌─────────────────┐
   │   │  Ideator (LLM1)  │◄──┐
   │   │  proposes Option A│   │  loop up to 3 rounds
   │   └────────┬─────────┘   │
   │            ▼             │
   │   ┌─────────────────┐    │
   │   │  Critic (LLM2)   │    │
   │   │  challenges + B  │────┘
   │   └────────┬─────────┘
   │            ▼
   │   ┌─────────────────┐
   │   │  Convergence     │  LLM3 judges: stop or
   │   │  check (LLM3)    │  loop again? (never picks
   │   └────────┬─────────┘  a winner here)
   │            ▼
   │   ┌─────────────────┐
   │   │  Synthesis       │  LLM3 reads the full debate,
   │   │  (LLM3)          │  gives ONE final recommendation
   │   └────────┬─────────┘
   ▼            ▼
┌─────────────────────────┐
│   Answer shown to user   │
│   Logged to SQLite       │
└──────────────────────────┘
```

**Why three LLM "roles" instead of one call:** the Ideator and Critic are
prompted adversarially — one argues for the ambitious/feature-rich option, the
other for the lean/pragmatic alternative, and each is instructed to engage the
other's strongest point rather than strawman it. The Referee (LLM3) never picks
a winner mid-debate; it only judges whether another round would add anything.
Once the debate ends, the Referee reads the entire transcript and produces one
grounded recommendation — this is the step that actually needs the most
reasoning, since it has to weigh both sides honestly rather than just repeat one.

**Important technical note:** "LLM1 / LLM2 / LLM3" are three different *prompted
roles*, not three different models. All three currently call the same
underlying model with different system prompts. The architecture is
model-agnostic — swapping in a stronger or cheaper model for any single role is
a one-line config change, not a rewrite.

---

## What kind of questions go where

| Query type | Example | Path |
|---|---|---|
| Fact / definition / explanation | "What is PostgreSQL?", "Explain how OAuth works" | **DIRECT** — one plain answer, no debate |
| Comparison / trade-off | "Should I use PostgreSQL or MongoDB?", "React vs Vue for my team" | **DECISION** — clarification → debate → synthesis |

The router is itself an LLM call (not a keyword rule), prompted with explicit
criteria and worked examples to reduce misclassification — e.g. any query
naming two or more options being weighed against each other routes to DECISION,
everything else routes to DIRECT.

---

## Retrieval (RAG)

The Ideator and Critic don't argue from model priors alone. Before the debate
starts, a lightweight retriever pulls relevant passages from a local knowledge
base (`knowledge/*.md`) and injects them into both agents' context.

- **Method:** pure keyword-overlap matching, no embeddings, no vector database,
  no external API — deliberately simple and fully inspectable.
- **Dataset:** a small curated set of Markdown files covering common technical
  trade-offs (database choice, cloud hosting, frontend frameworks, build-vs-buy
  auth, cloud database hosting). This is a **hand-written starter dataset**, not
  a scraped or fine-tuned corpus — swapping in a different domain is just
  adding more `.md` files to `knowledge/`, no code changes required.
- **Fallback behavior:** if no knowledge chunk matches the query well enough,
  the retriever returns nothing and the agents fall back to general reasoning
  instead of forcing irrelevant context into the prompt.

---

## Tools & stack

| Layer | Tool | Why |
|---|---|---|
| LLM inference | **Groq API** (`llama-3.1-8b-instant`) | Fast, low-cost hosted inference; swappable model |
| Agent orchestration | **LangGraph** | Cyclic state graph — needed for the round-based debate loop with a conditional exit (convergence check), which a simple prompt chain can't express |
| Structured output | **Pydantic** | Every LLM call is schema-validated (question lists, debate proposals, convergence verdicts, final answers) with automatic retry on invalid JSON |
| Retrieval | Custom Python (stdlib only) | Keyword-overlap RAG over local Markdown files |
| Persistence | **SQLite** (stdlib `sqlite3`) | Logs every query + final answer for history |
| Frontend | **Streamlit** | Query input, clarification form, results display, session state across the multi-step flow |
| Config / secrets | **python-dotenv** | Loads `GROQ_API_KEY` locally; Streamlit Cloud's secrets manager handles it in production |
| Hosting | **Streamlit Community Cloud** | Free tier, deploys directly from this GitHub repo |

---

## Running it locally

```bash
git clone https://github.com/premraj-dev/Nexus-AI.git
cd Nexus-AI
python -m venv venv
venv\Scripts\Activate.ps1        # Windows PowerShell
pip install -r requirements.txt
```

Create a `.env` file in the project root:
```
GROQ_API_KEY=your_key_here
```

Then run:
```bash
streamlit run app.py
```

---

## Honest limitations

- **Model size vs. quality:** `llama-3.1-8b-instant` is fast and cheap, but
  noticeably weaker at nuanced comparative reasoning than a frontier model —
  synthesis answers can lean one-sided rather than fully weighing both debated
  options. This is a known trade-off, not an oversight; the architecture is
  designed so the model is swappable.
- **RAG dataset is small and hand-written**, not a large curated or fine-tuned
  corpus. It demonstrates the retrieval mechanism, not domain-scale coverage.
- **No formal evaluation set yet** — there's currently no benchmark quantifying
  routing accuracy or synthesis quality; this is the planned next step.
- **SQLite runs on the app server** — on Streamlit Cloud's free tier, history
  resets when the app sleeps/restarts. Fine for a demo, not meant as durable
  storage.

---

## Roadmap

- [ ] Labeled evaluation set (query → expected route + quality scoring)
- [ ] Expand the knowledge base beyond the current starter topics
- [ ] Force the synthesis step to explicitly address the non-chosen option's
      strongest point, not just the winning one
- [ ] Swap keyword-overlap retrieval for embedding-based retrieval once the
      knowledge base grows large enough to need it
