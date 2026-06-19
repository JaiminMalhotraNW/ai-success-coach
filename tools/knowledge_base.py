import os
from pathlib import Path
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.tools import tool

# Get the absolute path to the project root
BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / "chroma_db"
DATA_FILE = BASE_DIR / "data" / "knowledge.md"

def initialize_knowledge_base():
    """Initializes the ChromaDB with an absolute path."""
    if os.path.exists(DB_DIR):
        return

    try:
        # Load the document
        loader = TextLoader(str(DATA_FILE))
        documents = loader.load()

        # Split text
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_documents(documents)

        # Create embeddings and store
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        
        # Explicitly set the directory
        Chroma.from_documents(
            documents=chunks, 
            embedding=embeddings, 
            persist_directory=str(DB_DIR)
        )
    except Exception as e:
        print(f"Error initializing knowledge base: {e}")

@tool
def search_knowledge_base(query: str) -> str:
    """Use this to answer questions about the course."""
    try:
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        # Use absolute path here too
        vector_store = Chroma(
            persist_directory=str(DB_DIR), 
            embedding_function=embeddings
        )
        results = vector_store.similarity_search(query, k=3)
        return "\n\n".join([doc.page_content for doc in results])
    except Exception as e:
        return f"Could not search knowledge base: {str(e)}"