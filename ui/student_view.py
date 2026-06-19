import streamlit as st
from agents.conversation_agent import get_conversation_agent
from langchain_core.messages import HumanMessage, AIMessage
from tools.sheets_client import get_roster
from tools.memory_manager import commit_session_to_memory

# Ensure State is initialized
if "selection_made" not in st.session_state:
    st.session_state.selection_made = False
if "messages" not in st.session_state:
    st.session_state.messages = []

@st.cache_data(ttl=600)
def fetch_roster():
    return get_roster()

def handle_save_and_reset():
    """Isolated function to handle saving without state conflicts."""
    if st.session_state.messages:
        with st.spinner("Saving summary..."):
            commit_session_to_memory(
                st.session_state.get("current_student_id", "unknown"), 
                st.session_state.messages
            )
        st.success("Session saved!")
    
    st.session_state.messages = []
    st.session_state.selection_made = False
    st.rerun()

def render_student_view():
    # --- STEP 1: LOGIN SCREEN ---
    if not st.session_state.selection_made:
        st.title("🧑‍🎓 Student Login")
        roster = fetch_roster()
        if not roster:
            st.warning("Loading roster...")
            return

        options = {f"{r['student_id']} - {r['name']}": r for r in roster}
        selected_option = st.selectbox("Select profile:", list(options.keys()))
        
        if st.button("Start Coaching Session ➔", type="primary"):
            st.session_state.student_data = options[selected_option]
            st.session_state.current_student_id = st.session_state.student_data["student_id"]
            st.session_state.current_student_name = st.session_state.student_data["name"]
            st.session_state.messages = [
                AIMessage(content=f"Hello {st.session_state.current_student_name}! 👋 I'm Ace.")
            ]
            st.session_state.selection_made = True
            st.rerun()

    # --- STEP 2: CHAT SCREEN ---
    else:
        st.title(f"💬 Chatting with Ace")
        
        # Navigation
        if st.button("← Change Student"):
            st.session_state.messages = []
            st.session_state.selection_made = False
            st.rerun()

        # Display Chat
        for msg in st.session_state.messages:
            role = "user" if isinstance(msg, HumanMessage) else "assistant"
            with st.chat_message(role):
                st.markdown(msg.content)

        # M4: End Session Trigger
        if st.button("🛑 End Session & Save Memory", type="secondary"):
            handle_save_and_reset()

        # Chat Input
        if prompt := st.chat_input("Ask Ace a question..."):
            st.session_state.messages.append(HumanMessage(content=prompt))
            
            # Agent processing
            agent = get_conversation_agent(
                st.session_state.current_student_id, 
                st.session_state.current_student_name
            )
            
            with st.chat_message("assistant"):
                response_placeholder = st.empty()
                full_response = ""
                for chunk in agent.stream({"messages": st.session_state.messages}, stream_mode="messages"):
                    message_chunk = chunk[0]
                    if isinstance(message_chunk, AIMessage) and message_chunk.content:
                        full_response += message_chunk.content
                        response_placeholder.markdown(full_response + "▌")
                response_placeholder.markdown(full_response)
                st.session_state.messages.append(AIMessage(content=full_response))
            st.rerun()