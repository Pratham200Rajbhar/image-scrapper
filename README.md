# Image Scraper

Python image scraper for Google and Bing without APIs.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### API (Recommended)

```bash
# Start server
uvicorn main:app --reload

# Make requests
curl "http://localhost:8000/scrape?query=cats&engine=bing&num_images=10"

# Health/root
curl "http://localhost:8000/"

# Another example (URL-encode spaces as %20)
curl "http://localhost:8000/scrape?query=golden%20retriever&engine=bing&num_images=5"

# Google (may be blocked more often than Bing)
curl "http://localhost:8000/scrape?query=cats&engine=google&num_images=5"
```

### Command Line

```bash
python scraper.py "cats" bing 10
```

### Python

```python
from scraper import ImageScraper
scraper = ImageScraper()
result = scraper.scrape("cats", "bing", 50)
```

## Output

```json
{
  "query": "cats",
  "engine": "bing",
  "image_count": 10,
  "images": [
    {"index": 0, "image_url": "https://..."}
  ]
}
```

## Notes

- Use Bing (Google blocks scrapers)
- Educational purposes only

