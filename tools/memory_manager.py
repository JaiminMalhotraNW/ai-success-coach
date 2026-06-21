import os
from dotenv import load_dotenv

load_dotenv()  # reads .env into os.environ, if present

import streamlit as st
from mem0 import MemoryClient
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool

def _get_secret(key: str):
    """Get a secret from .env first, falling back to st.secrets if present."""
    val = os.getenv(key)
    if val:
        return val
    try:
        return st.secrets[key]
    except Exception:
        return None

# Initialize client
api_key = _get_secret("MEM0_API_KEY")
if not api_key:
    st.error("MEM0_API_KEY not found. Add it to a .env file.")
    st.stop()

client = MemoryClient(api_key=api_key)

def commit_session_to_memory(student_id: str, chat_history: list):
    """Saves a list of dictionaries to Mem0."""
    normalized = [
        {"role": "assistant" if m["role"] == "ai" else m["role"], "content": m["content"]}
        for m in chat_history
    ]
    try:
        client.add(normalized, user_id=student_id)
        return True
    except Exception as e:
        st.error(f"Mem0 API Error: {str(e)}")
        return False
    
def get_student_memory(student_id: str) -> str:
    """
    BRAIN 1: CORE MEMORY SYNTHESIZER
    Retrieves memories using the safe 'search' method and synthesizes them.
    """
    try:
        # FIX: We use a broad search with filters (which matches your mem0 version syntax)
        # to pull up to 40 historical facts for the AI to synthesize.
        results = client.search(
            query="Retrieve all historical facts, past sessions, and context.",
            filters={"user_id": student_id},
            limit=40
        )
        
        if not results:
            return "No prior history with this student."
            
        items = results.get("results", results) if isinstance(results, dict) else results
        memory_strings = [f"- {r['memory']}" for r in items if isinstance(r, dict) and 'memory' in r]
        
        if not memory_strings:
            return "No prior history with this student."
            
        raw_history = "\n".join(memory_strings)
        
        # Fast, cheap synthesis step
        llm = ChatOpenAI(model="gpt-5.4-mini-2026-03-17", temperature=0)
        system_prompt = """You are an expert AI data synthesizer. Read the following raw memory logs for a student.
        Create a highly concise, bulleted profile divided into exactly two sections:
        1. PERMANENT FACTS (e.g., job, family, learning style)
        2. CURRENT STATUS (e.g., recent struggles, active goals)
        Keep it brief so it doesn't overwhelm the AI coach reading it."""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"RAW MEMORY LOGS:\n{raw_history}")
        ]
        
        response = llm.invoke(messages)
        return response.content
        
    except Exception as e:
        print(f"DEBUG: Failed to synthesize memory: {e}")
        return ""

@tool
def search_past_sessions(student_id: str, query: str) -> str:
    """
    Use this tool to search the student's history when they ask you about specific details 
    from past sessions (e.g., "what did we agree on?", "what book did you recommend?").
    """
    try:
        # FIX: Added filters={"user_id": student_id} to fix the TypeError crash!
        results = client.search(
            query=query, 
            filters={"user_id": student_id}, 
            limit=5
        )
        
        if not results:
            return "No specific details found in past sessions regarding this."
            
        items = results.get("results", results) if isinstance(results, dict) else results
        memory_strings = [f"- {r['memory']}" for r in items if isinstance(r, dict) and 'memory' in r]
        
        if not memory_strings:
             return "No specific details found in past sessions regarding this."
             
        return "Found these episodic details in past sessions:\n" + "\n".join(memory_strings)
    except Exception as e:
        return f"Error searching past sessions: {str(e)}"