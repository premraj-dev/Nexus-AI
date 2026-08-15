import streamlit as st
from dispatcher import route_and_execute

st.set_page_config(page_title="Nexus AI", layout="wide")
st.title("Nexus AI")
st.caption("Smart Multi-Agent & Dynamic Router Engine")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Process input query safely
if prompt := st.chat_input("Continue talking with Nexus AI..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Processing request..."):
            try:
                res = route_and_execute(prompt)
                response_text = res.get("response", "No response generated.")
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
            except Exception as e:
                error_msg = f"Execution Error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
