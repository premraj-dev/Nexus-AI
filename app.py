import streamlit as st
from dispatcher import route_and_execute
from services.ollama_service import ollama_service

# Page Configuration
st.set_page_config(page_title="Nexus AI", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# Custom CSS Styling
st.markdown("""
    <style>
    .header-container { text-align: center; padding-top: 20px; padding-bottom: 25px; }
    .main-title {
        font-size: 3.2rem; font-weight: 800; margin-bottom: 0px;
        background: linear-gradient(90deg, #FF4B4B, #FF8E53);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .sub-title { font-size: 1.5rem; font-weight: 500; margin-top: -5px; margin-bottom: 8px; color: #E0E0E0; }
    .tech-stack { font-size: 0.9rem; color: #999999; font-style: italic; }
    .hero-container { max-width: 750px; margin: 0 auto; padding-top: 40px; text-align: center; }
    div[data-testid="stSidebarNav"] {display: none;}
    </style>
""", unsafe_allow_html=True)

# Session State Initialization
if "messages" not in st.session_state: st.session_state.messages = []
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "current_step" not in st.session_state: st.session_state.current_step = "input"
if "temp_user_query" not in st.session_state: st.session_state.temp_user_query = ""
if "questions" not in st.session_state: st.session_state.questions = []
if "show_search" not in st.session_state: st.session_state.show_search = False
if "last_result" not in st.session_state: st.session_state.last_result = {}

# Sidebar Management
with st.sidebar:
    col_hdr1, col_hdr2 = st.columns([4, 1])
    with col_hdr1: st.markdown("### **Nexus AI**")
    with col_hdr2:
        if st.button("🔍", key="btn_toggle_search"):
            st.session_state.show_search = not st.session_state.show_search

    search_term = ""
    if st.session_state.show_search:
        search_term = st.text_input("Search chats...", key="search_chat_input")

    st.markdown("")

    if st.button("➕ New chat", use_container_width=True, type="secondary"):
        st.session_state.messages = []
        st.session_state.current_step = "input"
        st.session_state.temp_user_query = ""
        st.session_state.questions = []
        st.session_state.last_result = {}
        st.rerun()

    st.button("💬 Chats", use_container_width=True)
    st.button("📂 Projects", use_container_width=True)
    st.button("📦 Artifacts", use_container_width=True)

    st.markdown("---")
    st.caption("**Recents**")

    if not st.session_state.chat_history:
        st.caption("No recent chats yet.")
    else:
        filtered_history = [
            (idx, item) for idx, item in enumerate(reversed(st.session_state.chat_history))
            if search_term.lower() in item['title'].lower()
        ]
        for idx, item in filtered_history:
            title_disp = item['title'][:26] + "..." if len(item['title']) > 26 else item['title']
            if st.button(f"📄 {title_disp}", key=f"hist_{idx}", use_container_width=True):
                st.session_state.messages = item['messages'].copy()
                st.session_state.current_step = "chat"
                st.rerun()

# STEP 1: Main Landing & Input View
if st.session_state.current_step == "input":
    st.markdown("""
        <div class="hero-container">
            <div class="main-title">Nexus AI</div>
            <div class="sub-title">Smart Multi-Agent & Dynamic Router Engine</div>
            <div class="tech-stack">Powered by Local LLM Debate Routing & Hybrid Processing</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.write("")
    st.write("")
    
    col_l, col_mid, col_r = st.columns([1, 4, 1])
    with col_mid:
        with st.form("centered_prompt_form"):
            user_input = st.text_input("Ask anything...", placeholder="Ask for code, quick facts, or strategic architectural choices...", label_visibility="collapsed")
            btn_submit = st.form_submit_button("🚀 Submit Query", use_container_width=True, type="primary")

        if btn_submit and user_input.strip():
            st.session_state.temp_user_query = user_input
            st.session_state.messages.append({"role": "user", "content": user_input})
            
            with st.spinner("Classifying intent & running multi-agent dispatcher..."):
                res = route_and_execute(user_input)
                st.session_state.last_result = res
                mode = res.get("mode", "DIRECT")

                if mode in ["DIRECT", "EXPERT", "DECISION"]:
                    output_text = res.get("output", "No response generated.")
                    st.session_state.messages.append({"role": "assistant", "content": output_text})
                    st.session_state.chat_history.append({"title": user_input, "messages": st.session_state.messages.copy()})
                    st.session_state.current_step = "chat"
                    st.rerun()
                elif mode == "CLARIFY":
                    st.session_state.questions = res.get("clarifications", [
                        "What is your target scale or user count?",
                        "Are there specific system latency or infrastructure constraints?"
                    ])
                    st.session_state.current_step = "clarify"
                    st.rerun()

# STEP 2: Clarification Preferences Form
elif st.session_state.current_step == "clarify":
    st.markdown("""
        <div class="header-container">
            <div class="main-title">Nexus AI</div>
            <div class="sub-title">Parameters & Clarification Step</div>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    with st.chat_message("assistant"):
        st.markdown("### 📋 System Refinement Form")
        st.caption("Provide additional details to help the debate engine select the optimal answer.")
        answers = []
        with st.form("clarification_form"):
            for idx, q in enumerate(st.session_state.questions, 1):
                ans = st.text_input(f"Q{idx}: {q}", key=f"ans_{idx}")
                answers.append(f"Q: {q} | A: {ans}")
            
            extra_info = st.text_area("📝 Additional Requirements / Constraints:", placeholder="Specify hardware, throughput, latency, or budget goals...", key="extra_info_input")
            submitted = st.form_submit_button("✨ Run Full Debate Engine", type="primary")

        if submitted:
            if extra_info.strip(): answers.append(f"Additional Notes: {extra_info.strip()}")
            formatted_answers = "\n".join(answers)
            enriched_query = f"{st.session_state.temp_user_query}\nContext/Constraints:\n{formatted_answers}"
            
            with st.spinner("Evaluating trade-offs & triggering adversarial debate..."):
                res = route_and_execute(enriched_query)
                st.session_state.last_result = res
                output_text = res.get("output", "")
                
                st.session_state.messages.append({"role": "assistant", "content": output_text})
                st.session_state.chat_history.append({"title": st.session_state.temp_user_query, "messages": st.session_state.messages.copy()})
                st.session_state.current_step = "chat"
                st.rerun()

# STEP 3: Chat History & Output View
elif st.session_state.current_step == "chat":
    st.markdown("""
        <div class="header-container">
            <div class="main-title">Nexus AI</div>
        </div>
    """, unsafe_allow_html=True)
    
    # Render Execution Telemetry Badges
    if st.session_state.last_result:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Routed Execution Mode", st.session_state.last_result.get("mode", "N/A"))
        with col2:
            st.metric("Multi-Agent Debate Rounds", st.session_state.last_result.get("rounds_run", 0))
    
    st.markdown("---")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): 
            st.markdown(msg["content"], unsafe_allow_html=True)

    follow_up = st.chat_input("Continue talking with Nexus AI...")
    if follow_up:
        st.session_state.messages.append({"role": "user", "content": follow_up})
        with st.chat_message("user"): 
            st.markdown(follow_up)
            
        with st.chat_message("assistant"):
            with st.spinner("Nexus AI is processing follow-up..."):
                conversation_context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
                prompt = f"You are Nexus AI. Respond helpfully to the follow-up request.\n\nConversation History:\n{conversation_context}"
                
                try:
                    response_text = ollama_service.generate(prompt)
                except Exception:
                    res = route_and_execute(follow_up)
                    response_text = res.get("output", "")

                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                st.rerun()
