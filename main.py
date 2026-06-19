import streamlit as st
from ui.student_view import render_student_view
from tools.knowledge_base import initialize_knowledge_base

# 1. Initialize the Knowledge Base (Milestone 3)
# This builds the brain for Ace to answer questions
initialize_knowledge_base()

# Configure the browser tab
st.set_page_config(
    page_title="Success Coach AI", 
    page_icon="🤖", 
    layout="centered"
)

# Initialize the state for page routing
if "current_page" not in st.session_state:
    st.session_state.current_page = "Home"

# --- ROUTING LOGIC ---

if st.session_state.current_page == "Home":
    st.title("Welcome to Success Coach AI")
    st.write("Please select your portal to continue:")
    
    # Selection for Student or Coach
    role = st.radio("Select View:", ["Student", "Coach"], index=0)
    
    # Button to transition
    if st.button("Move ➔", type="primary"):
        st.session_state.current_page = role
        st.rerun()

elif st.session_state.current_page == "Student":
    # Button to go back
    if st.button("← Back to Home"):
        st.session_state.current_page = "Home"
        st.rerun()
    # Call the student view
    render_student_view()

elif st.session_state.current_page == "Coach":
    # Button to go back
    if st.button("← Back to Home"):
        st.session_state.current_page = "Home"
        st.rerun()
    
    st.title("👩‍💼 Coach Dashboard")
    st.info("The daily planner and alerts dashboard will be built here in Phase 4!")