import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing import Annotated, TypedDict

# Import ALL your tools from the sheets client and knowledge base
from tools.sheets_client import get_student_scores, get_student_attendance, get_upcoming_exams
from tools.knowledge_base import search_knowledge_base

# Import your Mem0 memory manager
from tools.memory_manager import get_student_memory

# 1. Define the complete list of tools
tools = [
    get_student_scores,
    get_student_attendance,
    get_upcoming_exams,
    search_knowledge_base
]

# 2. Define State
class State(TypedDict):
    messages: Annotated[list, add_messages]

# 3. Build the Agent Node
def build_agent_node(student_id: str, student_name: str):
    
    # --- M5: FETCH MEM0 HISTORY ---
    student_history = get_student_memory(student_id)
    
    # --- M2, M3, M5: COMPREHENSIVE SYSTEM PROMPT ---
    system_prompt = f"""You are Ace, an empathetic and highly effective Success Coach AI at NxtWave.
You are currently speaking with a student named {student_name} (ID: {student_id}).

YOUR MEMORY AND CONTEXT:
{student_history}
(If the history mentions specific stress triggers, recurring issues, or past plans you both made, USE THAT context naturally in your conversation. Do not explicitly say "According to my memory vault..." just seamlessly pick up where you left off.)

YOUR STRICT TOOL DIRECTIVES:
1. EXAM SCORES/MARKS: When asked about academic performance, exam scores, marks, or failing classes, YOU MUST use the `get_student_scores` tool. Pass '{student_id}'.
2. ATTENDANCE: When asked about attendance percentages, missed classes, or attendance track records, YOU MUST use the `get_student_attendance` tool. Pass '{student_id}'.
3. UPCOMING EXAMS: When asked about future exams, timetables, or upcoming tests, YOU MUST use the `get_upcoming_exams` tool. Pass '{student_id}'.
4. PLATFORM POLICIES & FEATURES: When asked about NxtWave platform features (e.g., My Journey, Bookmarks, Certificates, Course Exams, LastMinute Pro, rules), YOU MUST use the `search_knowledge_base` tool.

CRITICAL RULES:
- NEVER guess grades, attendance, exam dates, or platform rules. ALWAYS fetch the real data using your tools first.
- Be concise, practical, and warm. Avoid sounding like a generic chatbot.
"""

    # CRITICAL FIX: Restored your specific model!
    llm = ChatOpenAI(model="gpt-5.4-mini-2026-03-17", temperature=0)
    llm_with_tools = llm.bind_tools(tools)
    
    def chatbot(state: State):
        # Inject the system prompt invisibly before the chat history
        messages = [SystemMessage(content=system_prompt)] + state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}
        
    return chatbot

# 4. Build the Graph
def get_conversation_agent(student_id: str, student_name: str):
    graph_builder = StateGraph(State)
    
    chatbot_node = build_agent_node(student_id, student_name)
    tool_node = ToolNode(tools=tools)
    
    graph_builder.add_node("chatbot", chatbot_node)
    graph_builder.add_node("tools", tool_node)
    
    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_conditional_edges("chatbot", tools_condition)
    graph_builder.add_edge("tools", "chatbot")
    
    # Compile the graph
    return graph_builder.compile()