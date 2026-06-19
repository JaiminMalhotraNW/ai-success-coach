import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# This loads the variables (like your API key) from the .env file
load_dotenv()

def get_llm():
    """
    Single factory for the OpenAI LLM used across the system.
    If we ever need to swap models, we only change it here.
    """
    return ChatOpenAI(
        model="gpt-5.4-mini-2026-03-17",  # Using a fast, efficient model for the coach
        temperature=0.7,      # Balances creativity and focus
        streaming=True        # Enabled so the UI can show responses live
    )