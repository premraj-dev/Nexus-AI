import streamlit as st

from graph.debate_graph import generate_clarifying_questions, run_debate, route_query, answer_direct
from db import init_db, log_answer, fetch_recent

st.set_page_config(page_title="Nexus AI", layout="centered")
init_db()

st.title("Nexus AI")
st.caption("Clarify → LLM1 vs LLM2 debate → LLM3 synthesizes one final answer")

DEFAULTS = {
    "stage": "query",
    "user_query": "",
    "clarification_questions": [],
    "clarification_answers": "",
    "debate_result": None,
    "direct_answer": None,
    "router_reasoning": "",
}
for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val


def reset():
    for key, val in DEFAULTS.items():
        st.session_state[key] = val


# ---------------- Sidebar: recent history ----------------
with st.sidebar:
    st.subheader("Recent answers")
    if st.button("New query"):
        reset()
        st.rerun()
    for row in fetch_recent(15):
        with st.expander(row["user_query"][:60] + ("…" if len(row["user_query"]) > 60 else "")):
            st.markdown(row["final_recommendation"])
            st.caption(f"{row['rounds_run']} round(s) · {row['timestamp']}")

# ---------------- Stage 1: query input ----------------
if st.session_state.stage == "query":
    query = st.text_area("What decision are you weighing?", height=100,
                          placeholder="e.g. Should I use PostgreSQL or MongoDB for my AI app with 10,000 users?")
    if st.button("Start", type="primary", disabled=not query.strip()):
        st.session_state.user_query = query.strip()
        with st.spinner("Routing your query..."):
            try:
                decision = route_query(query.strip())
                st.session_state.router_reasoning = decision.reasoning
                if decision.mode == "DIRECT":
                    with st.spinner("Answering directly..."):
                        st.session_state.direct_answer = answer_direct(query.strip())
                        st.session_state.stage = "direct"
                        st.rerun()
                else:
                    st.session_state.clarification_questions = generate_clarifying_questions(query.strip())
                    st.session_state.stage = "clarify"
                    st.rerun()
            except Exception as e:
                st.error(f"Routing/clarification step failed: {e}")

# ---------------- Stage: DIRECT answer (no debate) ----------------
elif st.session_state.stage == "direct":
    st.markdown(f"**Your question:** {st.session_state.user_query}")
    st.caption(f"Routed as DIRECT — {st.session_state.router_reasoning}")
    st.subheader("Answer")
    st.markdown(st.session_state.direct_answer)
    if st.button("Ask another question", type="primary"):
        reset()
        st.rerun()

# ---------------- Stage 2: clarification form ----------------
elif st.session_state.stage == "clarify":
    st.markdown(f"**Your question:** {st.session_state.user_query}")
    st.markdown("A few quick questions before the debate starts:")
    answers = []
    with st.form("clarification_form"):
        for i, q in enumerate(st.session_state.clarification_questions):
            answers.append(st.text_input(q, key=f"clarify_{i}"))
        submitted = st.form_submit_button("Get my answer", type="primary")
    if submitted:
        combined = "\n".join(
            f"Q: {q}\nA: {a}" for q, a in zip(st.session_state.clarification_questions, answers) if a.strip()
        )
        st.session_state.clarification_answers = combined
        with st.spinner("LLM1 and LLM2 are debating, then LLM3 will decide..."):
            try:
                result = run_debate(st.session_state.user_query, combined)
                st.session_state.debate_result = result
                log_answer(
                    user_query=st.session_state.user_query,
                    clarification_answers=combined,
                    option_a_json=result.option_a.model_dump_json(),
                    option_b_json=result.option_b.model_dump_json(),
                    final_recommendation=result.synthesis.final_recommendation,
                    synthesis_json=result.synthesis.model_dump_json(),
                    rounds_run=result.rounds_run,
                    converged=result.converged,
                )
                st.session_state.stage = "answer"
                st.rerun()
            except Exception as e:
                st.error(f"Debate failed: {e}")

# ---------------- Stage 3: show the single synthesized answer ----------------
elif st.session_state.stage == "answer":
    result = st.session_state.debate_result
    synthesis = result.synthesis

    st.markdown(f"**Your question:** {st.session_state.user_query}")
    st.caption(f"Routed as DECISION — {st.session_state.router_reasoning}")
    st.caption(f"{result.rounds_run} round(s) of internal debate · Converged: {result.converged}")

    st.subheader("Recommendation")
    st.markdown(synthesis.final_recommendation)

    st.subheader("Why")
    st.markdown(synthesis.reasoning)

    st.subheader("Key points")
    for point in synthesis.key_points:
        st.markdown(f"- {point}")

    if synthesis.caveats:
        st.subheader("Caveats")
        for c in synthesis.caveats:
            st.markdown(f"- {c}")

    with st.expander("See the raw debate (LLM1 vs LLM2)"):
        st.markdown(f"**LLM1's final position — {result.option_a.option_title}**")
        st.markdown(result.option_a.tagline)
        for h in result.option_a.key_highlights:
            st.markdown(f"- {h}")
        st.markdown(f"**LLM2's final position — {result.option_b.option_title}**")
        st.markdown(result.option_b.tagline)
        for h in result.option_b.key_highlights:
            st.markdown(f"- {h}")

    if st.button("Ask another question", type="primary"):
        reset()
        st.rerun()