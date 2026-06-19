import os
from dotenv import load_dotenv

load_dotenv()  # reads .env into os.environ, if present

import streamlit as st
from mem0 import MemoryClient


def _get_secret(key: str):
    """Get a secret from .env first, falling back to st.secrets if present.

    st.secrets raises StreamlitSecretNotFoundError the moment it's accessed
    (even via .get()) if no secrets.toml file exists anywhere on disk — so
    we can't just chain `st.secrets.get(...) or os.getenv(...)`. We check
    the environment first and only touch st.secrets inside a try/except.
    """
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
    st.error(
        "MEM0_API_KEY not found. Add it to a .env file in your project root "
        "(MEM0_API_KEY=your_key_here) or to .streamlit/secrets.toml."
    )
    st.stop()

client = MemoryClient(api_key=api_key)

def commit_session_to_memory(student_id: str, chat_history: list):
    """Saves a list of dictionaries to Mem0."""
    # Mem0 expects OpenAI-style roles ("user" / "assistant"), but our UI
    # stores the assistant turn as "ai". Normalize before sending.
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
    Retrieves and formats a student's history from Mem0 to inject into the AI's prompt.
    """
    try:
        # Search Mem0 for context about this specific student
        # We use a broad query to pull in both facts and session summaries
        results = client.search(
            query="What are the key facts, recurring issues, stress triggers, and past session summaries for this student?",
            filters={"user_id": student_id}, 
            limit=10 
        )
        
        # If no memories exist yet, return a blank string
        if not results:
            return ""
            
        # Mem0 returns a list of dictionaries. We need to extract the 'memory' string.
        memory_strings = []
        for r in results:
            if isinstance(r, dict) and 'memory' in r:
                memory_strings.append(f"- {r['memory']}")
                
        if not memory_strings:
            return ""
            
        # Combine into a clean block of text for the LLM
        formatted_memory = "Here is the student's history from past sessions:\n" + "\n".join(memory_strings)
        return formatted_memory
        
    except Exception as e:
        print(f"DEBUG: Failed to retrieve memory: {e}")
        return "" # Fail silently so the chat doesn't break if retrieval fails