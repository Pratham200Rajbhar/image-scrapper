#!/usr/bin/env python3
import html
import json
import re
import sys
from typing import List, Set, Dict, Any
from urllib.parse import quote
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class ImageScraper:
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

    def __init__(self, timeout: int = 10, max_retries: int = 3):
        self.timeout = timeout
        self.session = self._create_session(max_retries)

    def _create_session(self, max_retries: int) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            backoff_factor=1,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": self.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

    def _validate_url(self, url: str) -> bool:
        if not url or len(url) < 30:
            return False
        url = url.replace("&quot;", "").replace("\\", "").strip()
        if not url.startswith(("http://", "https://")):
            return False
        if any(x in url.lower() for x in ["doubleclick", "google.com/url", "google.com/ads"]):
            return False
        return True

    def _clean_url(self, url: str) -> str:
        if not url:
            return ""
        url = url.replace("&quot;", "").replace("&amp;", "&").replace("\\/", "/").strip()
        # Do not split on commas here; commas appear in valid URLs and in `srcset` strings.
        return url.strip()

    def _is_likely_thumbnail(self, url: str) -> bool:
        if not url:
            return True
        lower = url.lower()
        return any(
            s in lower
            for s in [
                "encrypted-tbn0.gstatic.com",
                "gstatic.com/images?q=tbn",
                "googleusercontent.com/proxy",
                "mm.bing.net/th",
                "bing.com/th?",
                "bing.com/th?id=",
            ]
        )

    def _pick_best_from_srcset(self, srcset: str) -> str:
        """Return the highest-width URL from a `srcset` attribute."""
        if not srcset:
            return ""
        candidates = []
        for part in srcset.split(","):
            part = part.strip()
            if not part:
                continue
            tokens = part.split()
            candidate_url = self._clean_url(tokens[0])
            width = 0
            if len(tokens) > 1:
                m = re.match(r"^(\\d+)(w|x)$", tokens[1])
                if m:
                    width = int(m.group(1))
            candidates.append((width, candidate_url))
        candidates.sort(key=lambda t: t[0])
        for _, candidate_url in reversed(candidates):
            if self._validate_url(candidate_url) and not self._is_likely_thumbnail(candidate_url):
                return candidate_url
        # fallback
        return candidates[-1][1] if candidates else ""

    def scrape_google(self, query: str, num_images: int = 50) -> List[str]:
        images: Set[str] = set()
        url = f"https://www.google.com/search?q={quote(query)}&tbm=isch&ijn=0"

        try:
            headers = self._get_headers()
            headers["Referer"] = "https://www.google.com/"
            response = self.session.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            for pattern in [r'"ou":"([^"]+)"', r'"imgurl":"([^"]+)"']:
                for match in re.findall(pattern, response.text):
                    match = self._clean_url(match)
                    if self._validate_url(match) and not self._is_likely_thumbnail(match):
                        images.add(match)

            # Note: <img src> / data-src on Google Images are frequently thumbnails.
            # Prefer full-resolution URLs from embedded JSON patterns above.

        except requests.RequestException as e:
            print(f"Error: {e}", file=sys.stderr)

        return list(images)[:num_images]

    def scrape_bing(self, query: str, num_images: int = 50) -> List[str]:
        images: Set[str] = set()
        url = f"https://www.bing.com/images/search?q={quote(query)}"

        try:
            headers = self._get_headers()
            headers["Referer"] = "https://www.bing.com/"
            response = self.session.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Primary extraction: Bing stores the full-resolution image URL in the "m" JSON
            # on <a class="iusc" ...> elements as "murl".
            for a in soup.select("a.iusc"):
                m_attr = a.get("m")
                if not m_attr:
                    continue
                try:
                    m_json = json.loads(html.unescape(m_attr))
                except Exception:
                    continue
                for key in ["murl", "imgurl"]:
                    candidate = self._clean_url(str(m_json.get(key, "")))
                    if self._validate_url(candidate) and not self._is_likely_thumbnail(candidate):
                        images.add(candidate)

            # Fallback: regex extraction (still filter thumbnails)
            for pattern in [r'"murl":"([^"]+)"', r'"imgurl":"([^"]+)"']:
                for match in re.findall(pattern, response.text):
                    match = self._clean_url(match.replace("\\/", "/"))
                    if self._validate_url(match) and not self._is_likely_thumbnail(match):
                        images.add(match)

            # Avoid <img src> scraping here: it is frequently thumbnails from mm.bing.net.

        except requests.RequestException as e:
            print(f"Error: {e}", file=sys.stderr)

        return list(images)[:num_images]

    def scrape(self, query: str, engine: str = "google", num_images: int = 50) -> Dict[str, Any]:
        if engine.lower() == "google":
            image_urls = self.scrape_google(query, num_images)
        elif engine.lower() == "bing":
            image_urls = self.scrape_bing(query, num_images)
        else:
            raise ValueError(f"Unsupported engine: {engine}")

        unique_urls = list(set(image_urls))
        images_data = [{"index": idx, "image_url": url} for idx, url in enumerate(unique_urls)]

        return {
            "query": query,
            "engine": engine.lower(),
            "image_count": len(images_data),
            "images": images_data,
        }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python scraper.py <query> [engine] [num_images]"}))
        sys.exit(1)

    query = sys.argv[1]
    engine = sys.argv[2].lower() if len(sys.argv) > 2 else "google"
    num_images = int(sys.argv[3]) if len(sys.argv) > 3 else 50

    if engine not in ["google", "bing"]:
        print(json.dumps({"error": f"Invalid engine: {engine}"}))
        sys.exit(1)

    scraper = ImageScraper()
    result = scraper.scrape(query, engine, num_images)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
