from fastapi import FastAPI, HTTPException, Query
from scraper import ImageScraper

app = FastAPI()
scraper = ImageScraper()


@app.get("/")
def root():
    return {"message": "Image Scraper API", "endpoint": "/scrape"}


@app.get("/scrape")
def scrape_images(
    query: str = Query(...),
    engine: str = Query("bing"),
    num_images: int = Query(50, ge=1, le=100)
):
    if engine not in ["google", "bing"]:
        raise HTTPException(400, "Invalid engine")
    
    try:
        return scraper.scrape(query, engine, num_images)
    except Exception as e:
        raise HTTPException(500, str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
