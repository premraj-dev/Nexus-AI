import random

import streamlit as st

from cloud_storage import (
    CloudChatStore,
    GuestChatStore,
    is_configured,
    make_client,
    session_tokens,
    sign_in,
    sign_up,
)
from graph.debate_graph import (
    answer_direct,
    answer_explain,
    answer_live,
    generate_clarifying_questions,
    route_query,
    run_debate,
)


st.set_page_config(page_title="Nexus AI", page_icon="✦", layout="wide")

LOADING_MESSAGES = [
    "Gathering the relevant context...",
    "Checking the important details...",
    "Comparing the available information...",
    "Verifying the response...",
    "Organizing a clear answer...",
    "Thinking through the question...",
]


def format_history(messages: list[dict], limit: int = 12) -> str:
    recent = messages[-limit:]
    return "\n".join(f"{item['role'].title()}: {item['content']}" for item in recent)


def final_debate_text(result) -> str:
    synthesis = result.synthesis
    sections = [synthesis.final_recommendation, "\n**Why:**\n" + synthesis.reasoning]
    if synthesis.key_points:
        sections.append("\n**Key points:**\n" + "\n".join(f"- {point}" for point in synthesis.key_points))
    if synthesis.caveats:
        sections.append("\n**Caveats:**\n" + "\n".join(f"- {caveat}" for caveat in synthesis.caveats))
    return "\n".join(sections)


def live_text(result) -> str:
    text = result.answer
    if result.sources:
        text += "\n\n**Sources:**\n" + "\n".join(
            f"- [{source.title}]({source.url})" for source in result.sources
        )
    return text


def get_authenticated_user(client):
    saved_session = st.session_state.get("supabase_session")
    if not saved_session:
        return None
    try:
        refreshed = client.auth.set_session(
            saved_session["access_token"], saved_session["refresh_token"]
        )
        if getattr(refreshed, "session", None):
            st.session_state.supabase_session = session_tokens(refreshed.session)
        response = client.auth.get_user()
        return response.user
    except Exception:
        st.session_state.pop("supabase_session", None)
        return None


def migrate_guest_after_login(client, guest_store: GuestChatStore) -> str | None:
    response = client.auth.get_user()
    user = response.user
    cloud_store = CloudChatStore(client, user.id)
    if not guest_store.list_chats():
        return None
    active_cloud_id = guest_store.migrate_to_cloud(cloud_store)
    st.session_state.guest_chats = {}
    st.session_state.guest_messages = {}
    return active_cloud_id


def show_auth_controls(client, guest_store: GuestChatStore) -> None:
    if not is_configured():
        st.info("Guest mode is available. Add Supabase settings to enable saved cross-device chats.")
        return

    with st.expander("Sign in to save your chats", expanded=False):
        st.caption("Guest chats are temporary. Sign in to save them and use the same history on another computer.")
        sign_in_tab, sign_up_tab = st.tabs(["Sign in", "Create account"])

        with sign_in_tab:
            with st.form("guest_sign_in_form"):
                email = st.text_input("Email", key="guest_sign_in_email")
                password = st.text_input("Password", type="password", key="guest_sign_in_password")
                submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)
            if submitted:
                try:
                    session = sign_in(client, email.strip(), password)
                    st.session_state.supabase_session = session_tokens(session)
                    migrated_id = migrate_guest_after_login(client, guest_store)
                    st.session_state.chat_id = migrated_id
                    st.session_state.pending_decision = None
                    st.success("Signed in. Your chats are now saved to your account.")
                    st.rerun()
                except Exception as error:
                    st.error(f"Sign-in failed: {error}")

        with sign_up_tab:
            with st.form("guest_sign_up_form"):
                email = st.text_input("Email", key="guest_sign_up_email")
                password = st.text_input("Password", type="password", key="guest_sign_up_password")
                password_again = st.text_input("Confirm password", type="password")
                submitted = st.form_submit_button("Create account", type="primary", use_container_width=True)
            if submitted:
                if password != password_again:
                    st.error("The passwords do not match.")
                elif len(password) < 6:
                    st.error("Use a password with at least 6 characters.")
                else:
                    try:
                        session, message = sign_up(client, email.strip(), password)
                        if session:
                            st.session_state.supabase_session = session_tokens(session)
                            migrated_id = migrate_guest_after_login(client, guest_store)
                            st.session_state.chat_id = migrated_id
                            st.session_state.pending_decision = None
                            st.success("Account created. Your chats are now saved.")
                            st.rerun()
                        st.success(message or "Account created. Check your email, then sign in to save chats.")
                    except Exception as error:
                        st.error(f"Account creation failed: {error}")


def process_message(store, chat_id: str, user_text: str) -> None:
    existing_messages = store.get_messages(chat_id)
    conversation = format_history(existing_messages)
    pending = st.session_state.get("pending_decision")
    store.add_message(chat_id, "user", user_text)

    try:
        if pending and pending.get("chat_id") == chat_id:
            clarification_answers = f"User clarification: {user_text}"
            with st.spinner(random.choice(LOADING_MESSAGES)):
                result = run_debate(
                    pending["original_query"],
                    clarification_answers,
                    conversation,
                )
            assistant_text = final_debate_text(result)
            st.session_state.pending_decision = None
        else:
            with st.spinner(random.choice(LOADING_MESSAGES)):
                decision = route_query(user_text, conversation)

            if decision.mode == "DIRECT":
                with st.spinner(random.choice(LOADING_MESSAGES)):
                    assistant_text = answer_direct(user_text, conversation)
            elif decision.mode == "EXPLAIN":
                with st.spinner(random.choice(LOADING_MESSAGES)):
                    assistant_text = answer_explain(user_text, conversation).answer
            elif decision.mode == "LIVE":
                with st.spinner(random.choice(LOADING_MESSAGES)):
                    assistant_text = live_text(answer_live(user_text, decision, conversation))
            else:
                with st.spinner(random.choice(LOADING_MESSAGES)):
                    questions = generate_clarifying_questions(user_text, conversation)
                numbered = "\n".join(
                    f"{index}. {question}" for index, question in enumerate(questions, 1)
                )
                assistant_text = (
                    "To give you a useful answer, please share a little more context:\n\n"
                    f"{numbered}\n\n"
                    "You can answer in one message."
                )
                st.session_state.pending_decision = {
                    "chat_id": chat_id,
                    "original_query": user_text,
                    "questions": questions,
                }

        store.add_message(chat_id, "assistant", assistant_text)
    except Exception as error:
        # Never expose API keys, provider responses, token limits, or stack details in chat.
        print(f"Nexus AI request failed: {error}")
        store.add_message(
            chat_id,
            "assistant",
            "I’m temporarily unable to complete that answer. Please wait a moment and try again. "
            "You can also ask the question in a shorter form.",
        )


# Guest storage always exists in the current browser session. It never reaches Supabase.
guest_store = GuestChatStore(st.session_state)

supabase = None
if is_configured():
    try:
        supabase = make_client()
    except Exception as error:
        st.sidebar.warning(f"Cloud history is unavailable: {error}")

user = get_authenticated_user(supabase) if supabase else None
if user:
    store = CloudChatStore(supabase, user.id)
    storage_mode = f"cloud:{user.id}"
else:
    store = guest_store
    storage_mode = "guest"

if st.session_state.get("storage_mode") != storage_mode:
    st.session_state.storage_mode = storage_mode
    st.session_state.pop("chat_id", None)
    st.session_state.pending_decision = None

if "pending_decision" not in st.session_state:
    st.session_state.pending_decision = None

if "chat_id" not in st.session_state:
    chats = store.list_chats()
    st.session_state.chat_id = chats[0]["id"] if chats else store.create_chat()["id"]

search_query = ""
with st.sidebar:
    st.title("Nexus AI")
    if user:
        st.success("Signed in: cloud history enabled")
        st.caption(user.email)
    else:
        st.info("Guest mode: chats are temporary in this browser session.")
        if supabase:
            show_auth_controls(supabase, guest_store)
        else:
            st.caption("Sign-in becomes available after Supabase is configured.")

    if st.button("＋ New chat", use_container_width=True, type="primary"):
        st.session_state.chat_id = store.create_chat()["id"]
        st.session_state.pending_decision = None
        st.rerun()

    search_query = st.text_input("Search chats", placeholder="Search conversations...")
    chats = store.list_chats(search_query)
    st.divider()

    for chat in chats:
        pin_label = "Unpin" if chat.get("is_pinned") else "Pin"
        col_chat, col_pin = st.columns([5, 1])
        with col_chat:
            if st.button(
                chat["title"][:42],
                key=f"select_{chat['id']}",
                use_container_width=True,
                type="primary" if chat["id"] == st.session_state.chat_id else "secondary",
            ):
                st.session_state.chat_id = chat["id"]
                st.session_state.pending_decision = None
                st.rerun()
        with col_pin:
            if st.button("★" if chat.get("is_pinned") else "☆", key=f"pin_{chat['id']}", help=pin_label):
                store.set_pinned(chat["id"], not chat.get("is_pinned", False))
                st.rerun()

    st.divider()
    with st.expander("Chat settings"):
        active = store.get_chat(st.session_state.chat_id)
        if active:
            new_title = st.text_input("Chat name", value=active["title"], key="chat_title_input")
            if st.button("Rename chat", use_container_width=True):
                store.rename_chat(st.session_state.chat_id, new_title)
                st.rerun()
            if st.button("Delete this chat", use_container_width=True):
                store.delete_chat(st.session_state.chat_id)
                remaining = store.list_chats()
                st.session_state.chat_id = remaining[0]["id"] if remaining else store.create_chat()["id"]
                st.session_state.pending_decision = None
                st.rerun()

    if user:
        st.divider()
        if st.button("Sign out", use_container_width=True):
            supabase.auth.sign_out()
            st.session_state.pop("supabase_session", None)
            st.session_state.pop("chat_id", None)
            st.session_state.pop("storage_mode", None)
            st.session_state.pending_decision = None
            st.rerun()

active_chat = store.get_chat(st.session_state.chat_id)
if active_chat is None:
    st.session_state.chat_id = store.create_chat()["id"]
    st.rerun()

st.title("Nexus AI")
if user:
    st.caption("Your chats are saved to your account and available on other computers.")
else:
    st.caption("Use Nexus AI freely as a guest. Sign in from the sidebar whenever you want to save your chats.")

messages = store.get_messages(st.session_state.chat_id)
if not messages:
    if user:
        st.info("Ask a question to begin. This conversation will be saved in your account.")
    else:
        st.info("Ask a question to begin. Guest chats are temporary; sign in from the sidebar to save them.")

for message in messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_text = st.chat_input("Message Nexus AI")
if user_text and user_text.strip():
    clean_text = user_text.strip()
    if active_chat["title"] == "New chat":
        store.rename_chat(st.session_state.chat_id, clean_text)
    process_message(store, st.session_state.chat_id, clean_text)
    st.rerun()
