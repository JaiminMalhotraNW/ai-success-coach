import streamlit as st
from agents.conversation_agent import get_conversation_agent
from langchain_core.messages import HumanMessage, AIMessage
from tools.sheets_client import get_roster
from tools.memory_manager import commit_session_to_memory, get_student_memory

from tools.signal_detector import detect_signal
from tools.sheets_client import append_signal

@st.cache_data(ttl=600)
def fetch_roster():
    return get_roster()

def render_student_view():
    # 1. Initialize State INSIDE the render function
    # This guarantees it runs for every new user session on Streamlit Cloud
    if "selection_made" not in st.session_state:
        st.session_state.selection_made = False
    if "messages" not in st.session_state:
        st.session_state.messages = []

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
                history = get_student_memory(st.session_state.current_student_id)
                
                if history:
                    # History exists, generate personalized greeting
                    agent = get_conversation_agent(
                        st.session_state.current_student_id, 
                        st.session_state.current_student_name
                    )
                    system_nudge = "[SYSTEM: Greet the student by name, briefly acknowledge a specific fact or struggle from their past history, and ask how they are doing today regarding that. Keep it warm and under 3 sentences.]"
                    initial_response = agent.invoke({"messages": [HumanMessage(content=system_nudge)]})
                    greeting = initial_response["messages"][-1].content
                else:
                    # First time session
                    greeting = f"Hello {st.session_state.current_student_name}! 👋 I'm Ace, your Success Coach AI. How are your classes going today?"
            
            # Store messages as standard dictionaries
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

        # Display Chat 
        for msg in st.session_state.messages:
            with st.chat_message("assistant" if msg["role"] == "ai" else "user"):
                st.markdown(msg["content"])

        # M4, M5, & M6: End Session, Save Memory, and Detect Signals
        if st.button("🛑 End Session & Save Memory", type="secondary"):
            if st.session_state.messages:
                with st.spinner("Saving summary and analyzing session..."):
                    
                    # 1. M4: Save the memory to Mem0
                    saved = commit_session_to_memory(
                        st.session_state.current_student_id, 
                        st.session_state.messages
                    )
                    
                    # 2. M6: Detect if there is a signal in the chat
                    signal_output = detect_signal(st.session_state.messages)
                    
                    # 3. M6: If a signal exists, push it to Google Sheets
                    if signal_output.has_signal:
                        append_signal(
                            st.session_state.current_student_id,
                            st.session_state.current_student_name,
                            signal_output
                        )

                if saved:
                    st.success("Session saved successfully!")
            
            # Reset state for the next session
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