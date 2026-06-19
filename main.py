import streamlit as st
from ui.student_view import render_student_view

# Configure the browser tab
st.set_page_config(
    page_title="Success Coach AI", 
    page_icon="🤖", 
    layout="centered"
)

# Initialize the starting page
if "current_page" not in st.session_state:
    st.session_state.current_page = "Home"

# Route: Landing Page
if st.session_state.current_page == "Home":
    st.title("Welcome to Success Coach AI")
    st.write("Please select your portal to continue:")
    
    # Selection in the middle of the page
    role = st.radio("Select View:", ["Student", "Coach"], index=0)
    
    # Button to move to the next page
    if st.button("Move ➔", type="primary"):
        st.session_state.current_page = role
        st.rerun()

# Route: Student Portal
elif st.session_state.current_page == "Student":
    if st.button("← Back to Home"):
        st.session_state.current_page = "Home"
        st.rerun()
    render_student_view()

# Route: Coach Portal
elif st.session_state.current_page == "Coach":
    if st.button("← Back to Home"):
        st.session_state.current_page = "Home"
        st.rerun()
    st.title("👩‍💼 Coach Dashboard")
    st.info("The daily planner and alerts dashboard will be built here in Phase 4!")