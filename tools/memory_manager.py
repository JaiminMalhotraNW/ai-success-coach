import os
from mem0 import MemoryClient
from dotenv import load_dotenv

load_dotenv()

client = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))

def commit_session_to_memory(student_id: str, chat_history: list):
    """Sends the full conversation history to Mem0 for auto-summarization."""
    formatted_messages = []
    
    for msg in chat_history:
        # Use .type and .content attributes for LangChain messages
        role = "assistant" if msg.type == "ai" else "user"
        content = msg.content
        formatted_messages.append(f"{role}: {content}")
        
    full_text = "\n".join(formatted_messages)
    
    # Send to Mem0
    client.add(full_text, user_id=student_id)

def get_student_history(student_id: str):
    """Retrieves all memory facts for a specific student."""
    response = client.search("What is the student's background and history?", filters={"user_id": student_id})
    # Extract the 'memory' text from the results list
    memories = [r.get('memory') for r in response.get('results', [])]
    return memories