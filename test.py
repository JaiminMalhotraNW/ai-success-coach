import os
import time
from mem0 import MemoryClient
from dotenv import load_dotenv

load_dotenv()

def test_connection():
    api_key = os.getenv("MEM0_API_KEY")
    client = MemoryClient(api_key=api_key)

    student_id = "student_test_123"
    
    # 1. Add memory
    print("Adding memory...")
    client.add("The student is learning Python.", user_id=student_id)
    
    # 2. Wait for indexing
    print("Waiting 3 seconds for index...")
    time.sleep(3)

    # 3. Search with a REAL query
    print("Retrieving memory with a query...")
    # Use a real string for the query
    response = client.search("What is the student learning?", filters={"user_id": student_id})
    
    print(f"\nFull response object: {response}")
    
if __name__ == "__main__":
    test_connection()