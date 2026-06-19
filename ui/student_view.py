import streamlit as st
from agents.conversation_agent import get_conversation_agent
from langchain_core.messages import HumanMessage, AIMessage
from tools.sheets_client import get_roster
from tools.memory_manager import commit_session_to_memory

@st.cache_data(ttl=600)
def fetch_roster():
    return get_roster()

def render_student_view():
    # 1. Initialize State as Dictionaries (NEVER as AIMessage objects)
    # NOTE: this must live inside the render function, not at module level.
    # Module-level code only runs once per server process, not once per
    # browser session — so a second concurrent user would hit a missing
    # session_state key if this lived at the top of the file.
    if "selection_made" not in st.session_state:
        st.session_state.selection_made = False
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # --- STEP 1: LOGIN ---
    if not st.session_state.selection_made:
        st.title("🧑‍🎓 Student Login")
        roster = fetch_roster()
        if not roster:
            st.warning("Loading roster...")
            return

        options = {f"{r['student_id']} - {r['name']}": r for r in roster}
        selected_option = st.selectbox("Select profile:", list(options.keys()))
        
        if st.button("Start Coaching Session ➔", type="primary"):
            st.session_state.current_student_id = options[selected_option]["student_id"]
            st.session_state.current_student_name = options[selected_option]["name"]
            st.session_state.messages = [{"role": "ai", "content": f"Hello {st.session_state.current_student_name}! 👋 I'm Ace."}]
            st.session_state.selection_made = True
            st.rerun()

    # --- STEP 2: CHAT ---
    else:
        st.title(f"💬 Chatting with Ace")
        if st.button("← Change Student"):
            st.session_state.messages = []
            st.session_state.selection_made = False
            st.rerun()

        # Display Chat (Dictionaries)
        for msg in st.session_state.messages:
            with st.chat_message("assistant" if msg["role"] == "ai" else "user"):
                st.markdown(msg["content"])

        # M4: End Session (Dictionary-safe)
        if st.button("🛑 End Session & Save Memory", type="secondary"):
            if st.session_state.messages:
                with st.spinner("Saving summary..."):
                    saved = commit_session_to_memory(st.session_state.current_student_id, st.session_state.messages)
                if saved:
                    st.success("Session saved!")
                # If saved is False, commit_session_to_memory already showed
                # st.error() internally — don't contradict it with a success msg.
            st.session_state.messages = []
            st.session_state.selection_made = False
            st.rerun()

        # Input
        if prompt := st.chat_input("Ask Ace a question..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Map Dictionaries back to LangChain for the Agent
            langchain_msgs = [HumanMessage(content=m["content"]) if m["role"] == "user" else AIMessage(content=m["content"]) for m in st.session_state.messages]
            
            with st.chat_message("assistant"):
                agent = get_conversation_agent(st.session_state.current_student_id, st.session_state.current_student_name)
                response_placeholder = st.empty()
                full_response = ""
                for chunk in agent.stream({"messages": langchain_msgs}, stream_mode="messages"):
                    if isinstance(chunk[0], AIMessage) and chunk[0].content:
                        full_response += chunk[0].content
                        response_placeholder.markdown(full_response + "▌")
                
                response_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "ai", "content": full_response})
            st.rerun()