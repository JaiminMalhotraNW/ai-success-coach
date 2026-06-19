import os
import streamlit as st
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# 1. Define the exact JSON structure we demand from the LLM
class SignalOutput(BaseModel):
    has_signal: bool = Field(description="True if the student expressed a concerning academic, emotional, or logistical issue. False if normal.")
    concern: str = Field(default="", description="A short 1-2 sentence summary of the specific issue. Empty if no signal.")
    severity: str = Field(default="", description="Must be one of: Low, Medium, High, Critical. Empty if no signal.")
    urgency: str = Field(default="", description="Must be one of: Today, Tomorrow. Empty if no signal.")

def detect_signal(chat_history: list) -> SignalOutput:
    """
    Reads the session transcript and extracts a structured signal if a concern is detected.
    """
    # 2. Convert the list of dicts into a readable transcript for the LLM
    transcript = ""
    for msg in chat_history:
        role_name = "Coach (Ace)" if msg["role"] == "ai" else "Student"
        transcript += f"{role_name}: {msg['content']}\n"

    # 3. The precise prompt telling the LLM how to grade the session
    system_prompt = """You are a backend monitoring AI for a student success coaching platform. 
    Read the following conversation transcript between the AI Coach (Ace) and a student.
    
    Your job is to detect if there is a 'Signal' — a concerning issue that a human coach needs to review.
    
    EXAMPLES OF SIGNALS:
    - Failing a class, missing multiple assignments, OR expressing significant stress about coursework
    - Extreme stress, anxiety, or mentions of dropping out.
    - Severe logistical blockers preventing them from studying.
    
    EXAMPLES OF NO SIGNAL (has_signal = False):
    - Normal check-ins, routine study planning.
    - Asking normal doubts related to academic.
    - Mild, normal exam anxiety that the student is managing.
    - Positive progress and updates.
    
    If there is a signal, categorize its severity (Low, Medium, High, Critical) and urgency (Today, Tomorrow).
    If there is NO signal, return has_signal=False and leave the rest blank.
    """

    # 4. Initialize the LLM and bind it to our Pydantic schema
    llm = ChatOpenAI(model="gpt-5.4-mini-2026-03-17", temperature=0).with_structured_output(SignalOutput)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Transcript:\n{transcript}")
    ]

    # 5. Extract the signal
    try:
        result = llm.invoke(messages)
        return result
    except Exception as e:
        print(f"DEBUG: Signal detection failed: {e}")
        # Fail safely: If the LLM crashes, assume no signal so we don't break the app
        return SignalOutput(has_signal=False, concern="", severity="", urgency="")