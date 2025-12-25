from langchain_ollama import ChatOllama
from langchain_google_genai import GoogleGenerativeAI

def get_ollama_model():
    model = ChatOllama(model="gemma3:4b", temperature=0)
    return model

def get_google_model():
    model = GoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0.0)
    return model

