import time
from scraper import ImageScraper
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from langchain_core.messages import HumanMessage
from langchain_google_genai import GoogleGenerativeAI
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import Redis
from fastapi_cache.decorator import cache
from llm import get_ollama_model
from llm import get_google_model
import os

load_dotenv()

app = FastAPI()
scraper = ImageScraper()

if os.getenv("LLM_PROVIDER") == "OLLAMA":
    model = get_ollama_model()
else:
    model = get_google_model()

@app.get("/")
def root():
    return {"message": "Image Scraper API", "endpoint": "/scrape"}


@app.middleware("http")
async def logs(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    print(f"{request.method} {request.url.path} completed in {process_time:.2f}ms")
    return response


@app.on_event("startup")
def startup():
    redis = Redis(host="localhost", port=6379, db=0)
    FastAPICache.init(RedisBackend(redis), prefix="image-scraper")

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

    response = model.invoke(
        [
            HumanMessage(content=system_prompt),
            HumanMessage(content=prompt),
        ]
    )

    if (os.getenv("LLM_PROVIDER") == "OLLAMA"):
        return response.content.strip()
    else:
        return response.strip()