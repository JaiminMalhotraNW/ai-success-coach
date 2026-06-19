# Try the modern path first
try:
    from langgraph.prebuilt import create_react_agent
except ImportError:
    from langgraph.prebuilt.chat_agent_executor import create_react_agent

from config.llm import get_llm
from tools.sheets_client import get_student_scores, get_student_attendance, get_upcoming_exams
# Import the new tool
from tools.knowledge_base import search_knowledge_base

def get_conversation_agent(student_id: str, student_name: str):
    llm = get_llm()
    # Add search_knowledge_base to the toolkit
    tools = [
        get_student_scores, 
        get_student_attendance, 
        get_upcoming_exams, 
        search_knowledge_base
    ]
    
    system_prompt = f"""
You are Ace, a friendly, professional, and highly supportive academic advisor.
Your primary goal is to help students succeed academically.

You are currently talking to:
- Student Name: {student_name}
- Student ID: {student_id}

STRICT COMMUNICATION RULES:
1. LANGUAGE: You must communicate EXCLUSIVELY in English.
2. ACADEMIC ONLY: You are strictly for academic coaching. If a user asks about non-academic topics, politely apologize.
3. EMPATHY FIRST: Never be dismissive. Validate feelings.
4. NO DATA DUMPING: Do NOT list scores/attendance unprompted.

PROACTIVE COACHING & KNOWLEDGE RULES:
1. For personal data (grades, attendance, exams), use your specific student tools.
2. If the student asks ANY question about how the course works, the setup guide, features, or product rules, ALWAYS use the `search_knowledge_base` tool to find the exact answer. Do NOT guess. Base your answer entirely on the tool's output.
"""
    
    agent = create_react_agent(model=llm, tools=tools, prompt=system_prompt)
    return agent