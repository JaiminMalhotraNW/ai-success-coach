import streamlit as st
from config.llm import get_llm
from langchain_core.messages import HumanMessage, AIMessage

def render_student_view():
    st.title("🧑‍🎓 Student Support Portal")
    st.write("Welcome! Ask me anything or let me know how you're feeling.")
    
    # Initialize chat memory for this session
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display history
    for msg in st.session_state.messages:
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        with st.chat_message(role):
            st.markdown(msg.content)

    # Handle input
    if prompt := st.chat_input("Type your message here..."):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append(HumanMessage(content=prompt))

        # Get response from our LLM factory
        llm = get_llm()
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""
            
            # Stream the response chunk by chunk
            for chunk in llm.stream(st.session_state.messages):
                full_response += chunk.content
                response_placeholder.markdown(full_response + "▌")
            
            response_placeholder.markdown(full_response)
            
        st.session_state.messages.append(AIMessage(content=full_response))