import streamlit as st
from agents.conversation_agent import get_conversation_agent
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from tools.sheets_client import get_roster
from tools.memory_manager import commit_session_to_memory, get_student_memory
from tools.signal_detector import detect_signal
from tools.sheets_client import append_signal

@st.cache_data(ttl=600)
def fetch_roster():
    return get_roster()

def render_student_view():
    # 1. Initialize State 
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
                    agent = get_conversation_agent(
                        st.session_state.current_student_id, 
                        st.session_state.current_student_name
                    )
                    system_nudge = "[SYSTEM: Greet the student by name, briefly acknowledge a specific fact or struggle from their past history, and ask how they are doing today regarding that. Keep it warm and under 3 sentences.]"
                    initial_response = agent.invoke({"messages": [HumanMessage(content=system_nudge)]})
                    greeting = initial_response["messages"][-1].content
                else:
                    greeting = f"Hello {st.session_state.current_student_name}! 👋 I'm Ace, your Success Coach AI. How are your classes going today?"
            
            # Store ACTUAL LangChain messages
            st.session_state.messages = [AIMessage(content=greeting)]
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

        # Display Chat (Safely filter out background tool messages)
        for msg in st.session_state.messages:
            if isinstance(msg, HumanMessage):
                with st.chat_message("user"):
                    st.markdown(msg.content)
            elif isinstance(msg, AIMessage) and msg.content:
                # Only display AI messages that actually have text to say
                with st.chat_message("assistant"):
                    st.markdown(msg.content)

        # --- M4 & M6: END SESSION, SAVE MEMORY, DETECT SIGNALS ---
        if st.button("🛑 End Session & Save Memory", type="secondary"):
            if st.session_state.messages:
                with st.spinner("Saving summary and analyzing session..."):
                    
                    # Convert Langchain messages to dicts for our custom saving functions
                    dict_messages = [{"role": "user" if isinstance(m, HumanMessage) else "ai", "content": m.content} 
                                     for m in st.session_state.messages if getattr(m, 'content', None)]
                    
                    saved = commit_session_to_memory(st.session_state.current_student_id, dict_messages)
                    signal_output = detect_signal(dict_messages)
                    
                    if signal_output.has_signal:
                        append_signal(st.session_state.current_student_id, st.session_state.current_student_name, signal_output)

                if saved:
                    st.success("Session saved successfully!")
            
            st.session_state.messages = []
            st.session_state.selection_made = False
            st.rerun()

        # --- THE GHOSTING FAILSAFE LOGIC ---
        MAX_MESSAGES = 10 
        user_message_count = sum(1 for msg in st.session_state.messages if isinstance(msg, HumanMessage))

        if user_message_count >= MAX_MESSAGES:
            st.warning("⚠️ **Session Limit Reached:** Please click the **'🛑 End Session & Save Memory'** button to submit this conversation.")
            prompt = st.chat_input("Session limit reached. Please save.", disabled=True)
        elif user_message_count >= MAX_MESSAGES - 2:
            st.info("💡 *Just a heads up: Our session is almost at its time limit. Don't forget to save our progress when we wrap up!*")
            prompt = st.chat_input("Type your message here...")
        else:
            prompt = st.chat_input("Ask Ace a question...")

        # --- CHAT INPUT & LLM GENERATION ---
        if prompt:
            # Append actual HumanMessage
            new_msg = HumanMessage(content=prompt)
            st.session_state.messages.append(new_msg)
            
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                agent = get_conversation_agent(
                    st.session_state.current_student_id, 
                    st.session_state.current_student_name
                )
                
                # Show a spinner while the agent thinks and uses its tools
                with st.spinner("Ace is checking your records..."):
                    try:
                        # .invoke() runs the full graph, including all tool calls!
                        result = agent.invoke({"messages": st.session_state.messages})
                        
                        # OVERWRITE our session state with the agent's complete memory
                        # This perfectly saves all invisible ToolMessages so the AI doesn't forget
                        st.session_state.messages = result["messages"]
                        
                        # Find the very last message the AI generated and display it
                        final_ai_msg = st.session_state.messages[-1]
                        st.markdown(final_ai_msg.content)
                        
                    except Exception as e:
                        # Failsafe if a tool crashes
                        error_msg = f"Sorry, I encountered an error accessing my tools: {e}"
                        st.error(error_msg)
                        st.session_state.messages.append(AIMessage(content=error_msg))
                        
            st.rerun()