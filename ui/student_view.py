import streamlit as st
from agents.conversation_agent import get_conversation_agent
from langchain_core.messages import HumanMessage, AIMessage
from tools.sheets_client import get_roster
from tools.memory_manager import commit_session_to_memory, get_student_memory

# 1. Initialize State as Dictionaries
if "selection_made" not in st.session_state:
    st.session_state.selection_made = False
if "messages" not in st.session_state:
    st.session_state.messages = []

@st.cache_data(ttl=600)
def fetch_roster():
    return get_roster()

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
            st.session_state.current_student_id = options[selected_option]["student_id"]
            st.session_state.current_student_name = options[selected_option]["name"]
            
            # --- M5: DYNAMIC MEMORY GREETING ---
            with st.spinner("Ace is reviewing your file..."):
                # 1. Check if the student has a history
                history = get_student_memory(st.session_state.current_student_id)
                
                if history:
                    # 2. If history exists, have Ace generate a personalized greeting
                    agent = get_conversation_agent(
                        st.session_state.current_student_id, 
                        st.session_state.current_student_name
                    )
                    
                    # Send a hidden prompt to the agent to generate the first message
                    system_nudge = "[SYSTEM: Greet the student by name, briefly acknowledge a specific fact or struggle from their past history, and ask how they are doing today regarding that. Keep it warm and under 3 sentences.]"
                    initial_response = agent.invoke({"messages": [HumanMessage(content=system_nudge)]})
                    greeting = initial_response["messages"][-1].content
                else:
                    # 3. If no history (first session), use standard greeting
                    greeting = f"Hello {st.session_state.current_student_name}! 👋 I'm Ace, your Success Coach AI. How are your classes going today?"
            
            # Save the greeting to our dictionary state
            st.session_state.messages = [{"role": "ai", "content": greeting}]
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

        # Display Chat (using dictionaries)
        for msg in st.session_state.messages:
            with st.chat_message("assistant" if msg["role"] == "ai" else "user"):
                st.markdown(msg["content"])

        # M4: End Session & Save
        if st.button("🛑 End Session & Save Memory", type="secondary"):
            if st.session_state.messages:
                with st.spinner("Saving summary to your memory vault..."):
                    saved = commit_session_to_memory(
                        st.session_state.current_student_id, 
                        st.session_state.messages
                    )
                if saved:
                    st.success("Session saved!")
            st.session_state.messages = []
            st.session_state.selection_made = False
            st.rerun()

        # Chat Input
        if prompt := st.chat_input("Ask Ace a question..."):
            # Append user message as dictionary
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Map dictionaries to LangChain format for the agent
            langchain_msgs = [
                HumanMessage(content=m["content"]) if m["role"] == "user" 
                else AIMessage(content=m["content"]) 
                for m in st.session_state.messages
            ]
            
            with st.chat_message("assistant"):
                agent = get_conversation_agent(
                    st.session_state.current_student_id, 
                    st.session_state.current_student_name
                )
                response_placeholder = st.empty()
                full_response = ""
                
                # Stream the response
                for chunk in agent.stream({"messages": langchain_msgs}, stream_mode="messages"):
                    if isinstance(chunk[0], AIMessage) and chunk[0].content:
                        full_response += chunk[0].content
                        response_placeholder.markdown(full_response + "▌")
                
                response_placeholder.markdown(full_response)
                
                # Append AI response as dictionary
                st.session_state.messages.append({"role": "ai", "content": full_response})
            st.rerun()