import streamlit as st
from ui.student_view import render_student_view

# Configure the browser tab
st.set_page_config(
    page_title="Success Coach AI", 
    page_icon="🤖", 
    layout="centered"
)

# Render the interface
render_student_view()