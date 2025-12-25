import time
from app.scraper import ImageScraper
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from langchain_core.messages import HumanMessage
from langchain_google_genai import GoogleGenerativeAI
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import Redis
from fastapi_cache.decorator import cache
from app.llm import get_ollama_model, get_google_model, get_openrouter_model
import os

load_dotenv()

app = FastAPI()
scraper = ImageScraper()

if os.getenv("LLM_PROVIDER") == "OLLAMA":
    model = get_ollama_model()
    fallback_model = None
else:
    model = get_google_model()
    fallback_model = get_openrouter_model()


@app.get("/")
def root():
    return {"message": "Image Scraper API", "endpoint": "/scrape"}


@app.middleware("http")
async def logs(request, call_next):
    print(f"Incoming request: {request.method} {request.url.path}")
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    print(f"{request.method} {request.url.path} completed in {process_time:.2f}ms")
    return response


@app.on_event("startup")
def startup():
    redis_client = Redis(host="localhost", port=6379, db=0)
    
    original_set = redis_client.set
    def logged_set(name, *args, **kwargs):
        print(f" [REDIS UPDATE] Key: {name}")
        return original_set(name, *args, **kwargs)
    
    redis_client.set = logged_set
    FastAPICache.init(RedisBackend(redis_client), prefix="image-scraper")
    print("Redis caching initialized with logging.")


@app.get("/scrape")
@cache(expire=3600)
def scrape_images(
    query: str = Query(...),
    engine: str = Query("bing"),
    num_images: int = Query(50, ge=1, le=100),
):
    if engine not in ["google", "bing"]:
        raise HTTPException(status_code=400, detail="Invalid engine")

    optimized_query = optimize_query(query)
    return scraper.scrape(optimized_query, engine, num_images)


def optimize_query(prompt: str) -> str:
    system_prompt = (
        "Convert the user input into a concise, optimized Google Image search query.\n"
        "Rules:\n"
        "- Return ONLY the query\n"
        "- No explanations\n"
        "- No quotes\n"
        "- Focus on visual keywords"
    )

    messages = [
        HumanMessage(content=system_prompt),
        HumanMessage(content=prompt),
    ]

    try:
        response = model.invoke(messages)
        if hasattr(response, "content"):
            return response.content.strip()
        return response.strip()
    except Exception as e:
        print(f"Primary model failed: {e}")
        if fallback_model:
            print("Switching to fallback model (OpenRouter)...")
            try:
                response = fallback_model.invoke(messages)
                if hasattr(response, "content"):
                    return response.content.strip()
                return response.strip()
            except Exception as fe:
                print(f"Fallback model also failed: {fe}")
                raise HTTPException(status_code=500, detail="All LLM providers failed")
        else:
            raise HTTPException(status_code=500, detail=f"LLM request failed: {e}")


print("Image Scraper API is running...")
import socket

print(f"Server IP Address: {socket.gethostbyname(socket.gethostname())}")
