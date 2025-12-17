from fastapi import FastAPI, HTTPException, Query
from scraper import ImageScraper
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

scraper = ImageScraper()

model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.2
)

@app.get("/")
def root():
    return {"message": "Image Scraper API", "endpoint": "/scrape"}


@app.get("/scrape")
def scrape_images(
    query: str = Query(...),
    engine: str = Query("bing"),
    num_images: int = Query(50, ge=1, le=100)
):
    optimized_query = queryOptimizer(query)

    if engine not in ["google", "bing"]:
        raise HTTPException(status_code=400, detail="Invalid engine")

    return scraper.scrape(optimized_query, engine, num_images)


def queryOptimizer(prompt: str) -> str:
    system_prompt = (
        "Convert the user input into a concise, optimized Google Image search query.\n"
        "Rules:\n"
        "- Return ONLY the query\n"
        "- No explanations\n"
        "- No quotes\n"
        "- Focus on visual keywords"
    )   

    response = model.invoke([
        HumanMessage(content=system_prompt),
        HumanMessage(content=prompt)
    ])

    return response.content.strip()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
