from dotenv import load_dotenv
import os

load_dotenv()

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")

CHROMA_PATH = os.getenv("CHROMA_PATH")

COLLECTION_NAME = os.getenv("COLLECTION_NAME")

TOP_K = int(os.getenv("TOP_K"))