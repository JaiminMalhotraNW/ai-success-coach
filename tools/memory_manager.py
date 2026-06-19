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