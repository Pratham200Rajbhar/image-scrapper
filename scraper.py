import html
import json
import re
from typing import List, Set, Dict, Any
from urllib.parse import quote, urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class ImageScraper:
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
    BLOCKED_DOMAINS = {
        "researchgate.net",
        "www.researchgate.net",
        "localhost",
        "127.0.0.1",
    }
    SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg")

    def __init__(self, timeout: int = 10, max_retries: int = 3):
        self.timeout = timeout
        self.session = self._create_session(max_retries)

    def _create_session(self, max_retries: int) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            backoff_factor=1,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _headers(self, referer: str) -> Dict[str, str]:
        return {
            "User-Agent": self.USER_AGENT,
            "Accept": "text/html,*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": referer,
        }

    def _clean_url(self, url: str) -> str:
        return (
            url.replace("&quot;", "")
            .replace("&amp;", "&")
            .replace("\\/", "/")
            .strip(" \"'")
        )

    def _is_valid_image(self, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False

        host = (parsed.hostname or "").lower()
        if host in self.BLOCKED_DOMAINS:
            return False

        lower_url = url.lower()
        if any(x in lower_url for x in ["gstatic", "doubleclick", "bing.com/th"]):
            return False
        if lower_url.endswith(".webp"):
            return False

        path = (parsed.path or "").lower()
        return path.endswith(self.SUPPORTED_EXTENSIONS)

    def scrape_google(self, query: str, num_images: int) -> List[str]:
        url = f"https://www.google.com/search?q={quote(query)}&udm=2"
        response = self.session.get(
            url,
            headers=self._headers("https://www.google.com/"),
            timeout=self.timeout,
        )
        response.raise_for_status()

        images: Set[str] = set()
        text = html.unescape(response.text)

        for match in re.findall(r"https?://[^\s\"<>]+", text):
            url = self._clean_url(match)
            if self._is_valid_image(url):
                images.add(url)
            if len(images) >= num_images:
                break

        return list(images)

    def scrape_bing(self, query: str, num_images: int) -> List[str]:
        url = f"https://www.bing.com/images/search?q={quote(query)}"
        response = self.session.get(
            url,
            headers=self._headers("https://www.bing.com/"),
            timeout=self.timeout,
        )
        response.raise_for_status()

        images: Set[str] = set()
        soup = BeautifulSoup(response.text, "html.parser")

        for a in soup.select("a.iusc"):
            try:
                data = json.loads(html.unescape(a.get("m", "")))
                image_url = self._clean_url(data.get("murl", ""))
                if self._is_valid_image(image_url):
                    images.add(image_url)
            except Exception:
                continue

            if len(images) >= num_images:
                break

        return list(images)

    def scrape(self, query: str, engine: str, num_images: int) -> Dict[str, Any]:
        if engine == "google":
            urls = self.scrape_google(query, num_images)
        elif engine == "bing":
            urls = self.scrape_bing(query, num_images)
        else:
            raise ValueError("Unsupported engine")

        return {
            "query": query,
            "engine": engine,
            "image_count": len(urls),
            "images": [{"index": i, "image_url": url} for i, url in enumerate(urls)],
        }
