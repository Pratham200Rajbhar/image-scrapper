from langchain_ollama import ChatOllama
from langchain_google_genai import GoogleGenerativeAI
from langchain_openai import ChatOpenAI
import os

def get_ollama_model():
    model = ChatOllama(model="gemma3:4b", temperature=0)
    return model

def get_google_model():
    model = GoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0.0)
    return model

def get_openrouter_model():
    model = ChatOpenAI(
        model="google/gemini-2.0-flash-exp:free",
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=0
    )
    return model

