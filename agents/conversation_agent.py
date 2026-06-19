from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langchain_core.messages import SystemMessage
from typing_extensions import TypedDict, Annotated
from tools.memory_manager import get_student_memory

# Define the state schema
class State(TypedDict):
    messages: Annotated[list, add_messages]

def get_conversation_agent(student_id: str, student_name: str):
    """
    Creates the agent for a specific student, injecting their Mem0 history into the system prompt.
    """
    # Initialize the LLM (ensure OPENAI_API_KEY is in your .env or st.secrets)
    llm = ChatOpenAI(model="gpt-5.4-mini-2026-03-17", temperature=0.7)

    # 1. Retrieve the student's history from Mem0
    student_history = get_student_memory(student_id)

    # 2. Build the dynamic System Prompt
    system_prompt = f"""You are Ace, an empathetic and highly effective Success Coach AI.
You are currently speaking with a student named {student_name}.

Your goal is to help them navigate academic stress, build better habits, and succeed in their coursework.
Be concise, practical, and warm. Avoid sounding like a generic chatbot.

{student_history}

If the student's history mentions specific stress triggers, recurring issues, or past plans you both made, USE THAT context naturally in your conversation. Do not explicitly say "According to my memory vault..." just seamlessly pick up where you left off.
"""

    def chatbot(state: State):
        # Always prepend the dynamic system message to guide the LLM's behavior
        messages = [SystemMessage(content=system_prompt)] + state["messages"]
        response = llm.invoke(messages)
        return {"messages": [response]}

    # Build the graph
    workflow = StateGraph(State)
    workflow.add_node("chatbot", chatbot)
    workflow.add_edge(START, "chatbot")

    # Use an in-memory saver for the CURRENT session's rapid back-and-forth
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)

    # Return the compiled graph wrapped in a config for the specific student
    return app.with_config({"configurable": {"thread_id": student_id}})