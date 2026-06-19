import streamlit as st
from agents.conversation_agent import get_conversation_agent
from langchain_core.messages import HumanMessage, AIMessage
from tools.sheets_client import get_roster

@st.cache_data(ttl=600)
def fetch_roster():
    """Caches the roster to improve performance."""
    return get_roster()

def render_student_view():
    # Initialize state for flow control
    if "selection_made" not in st.session_state:
        st.session_state.selection_made = False

    # --- STEP 1: DROPDOWN SCREEN ---
    if not st.session_state.selection_made:
        st.title("🧑‍🎓 Student Login")
        roster = fetch_roster()
        if not roster:
            st.warning("Loading roster... check your Google Sheets connection.")
            return

        options = {f"{r['student_id']} - {r['name']}": r for r in roster}
        selected_option = st.selectbox("Select your profile to continue:", list(options.keys()))
        
        if st.button("Start Coaching Session ➔", type="primary"):
            st.session_state.student_data = options[selected_option]
            st.session_state.current_student_id = st.session_state.student_data["student_id"]
            st.session_state.current_student_name = st.session_state.student_data["name"]
            
            # Initial personalized greeting from Ace
            st.session_state.messages = [
                AIMessage(content=f"Hello {st.session_state.current_student_name}! 👋 I'm Ace, your Success Coach AI. How are your classes going today?")
            ]
            st.session_state.selection_made = True
            st.rerun()

    # --- STEP 2: CHAT SCREEN ---
    else:
        st.title(f"💬 Chatting with Ace")
        if st.button("← Change Student"):
            st.session_state.selection_made = False
            st.rerun()

        # Chat display
        for msg in st.session_state.messages:
            role = "user" if isinstance(msg, HumanMessage) else "assistant"
            if msg.type in ["human", "ai"] and msg.content:
                with st.chat_message(role):
                    st.markdown(msg.content)

        # Handle user input
        if prompt := st.chat_input("Ask Ace a question about your studies..."):
            st.chat_message("user").markdown(prompt)
            st.session_state.messages.append(HumanMessage(content=prompt))

            # Instantiate agent with current student context
            agent = get_conversation_agent(
                st.session_state.current_student_id, 
                st.session_state.current_student_name
            )
            
            with st.chat_message("assistant"):
                response_placeholder = st.empty()
                full_response = ""
                
                # Stream the agent's response
                for chunk in agent.stream({"messages": st.session_state.messages}, stream_mode="messages"):
                    message_chunk = chunk[0]
                    if isinstance(message_chunk, AIMessage) and message_chunk.content:
                        full_response += message_chunk.content
                        response_placeholder.markdown(full_response + "▌")
                
                response_placeholder.markdown(full_response)
                st.session_state.messages.append(AIMessage(content=full_response))