import json
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# Added get_upcoming_exams here
from tools.sheets_client import get_student_scores, get_student_attendance, get_upcoming_exams, get_open_signals
from tools.memory_manager import get_student_memory

# 1. Define the Strict Output Schema
class PreMeetingBrief(BaseModel):
    academic_overview: str = Field(description="Short summary of their recent scores, attendance, and any upcoming exams.")
    historical_shifts: str = Field(description="What has changed, improved, or recurred based on their past session memory.")
    open_concerns: str = Field(description="The main active issue or signal needing attention today.")
    conversation_starters: list[str] = Field(description="3 custom, empathetic talking points to start the meeting.")

# 2. The Generation Logic
def generate_student_brief(student_id: str, student_name: str) -> PreMeetingBrief:
    """
    Pulls data from Sheets, Mem0, and Signals to compile a 360-degree view of the student.
    """
    # A. Fetch Live Academic Data
    try:
        scores = get_student_scores.invoke({"student_id": student_id})
        attendance = get_student_attendance.invoke({"student_id": student_id})
        exams = get_upcoming_exams.invoke({"student_id": student_id}) # New!
    except Exception:
        scores = "Could not fetch scores."
        attendance = "Could not fetch attendance."
        exams = "Could not fetch upcoming exams."
        
    # B. Fetch Historical Memory (This safely pulls our new clean synthesized profile!)
    memory = get_student_memory(student_id)
    
    # C. Fetch Active Signals for this specific student
    open_signals = get_open_signals()
    student_signals = [s for s in open_signals if str(s.get("student_id")) == student_id]
    signal_context = json.dumps(student_signals) if student_signals else "No active crisis signals."

    # D. Construct the Prompt
    system_prompt = f"""You are an expert Success Coach Assistant.
    Your job is to read the raw data for {student_name} (ID: {student_id}) and generate a concise, highly actionable Pre-Meeting Brief for the human coach.

    RAW DATA:
    ---
    ACADEMIC SCORES:
    {scores}
    
    ATTENDANCE:
    {attendance}
    
    UPCOMING EXAMS:
    {exams}
    
    PAST MEMORY/HISTORY:
    {memory}
    
    ACTIVE SIGNALS/CONCERNS:
    {signal_context}
    ---

    Synthesize this information into a structured brief. Be professional, direct, and highlight any immediate risks.
    """

    llm = ChatOpenAI(model="gpt-5.4-mini-2026-03-17", temperature=0).with_structured_output(PreMeetingBrief)
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="Generate the pre-meeting brief.")
    ]
    
    try:
        return llm.invoke(messages)
    except Exception as e:
        print(f"DEBUG: Brief generation failed: {e}")
        # Failsafe return
        return PreMeetingBrief(
            academic_overview="Data compilation failed.",
            historical_shifts="Data compilation failed.",
            open_concerns="Data compilation failed.",
            conversation_starters=["How are you doing today?"]
        )