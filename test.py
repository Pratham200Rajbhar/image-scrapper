import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

URL = "http://159.89.166.91:8001/scrape"

HEADERS = {
    "accept": "application/json"
}

SEARCH_QUERIES = [
    "blockchain",
    "artificial intelligence",
    "quantum computing",
    "cloud computing",
    "cybersecurity",
    "machine learning",
    "data science",
    "web3",
    "internet of things",
    "edge computing",
]


def make_request(query):
    params = {
        "query": query,
        "engine": "bing",
        "num_images": 10,
    }

    start = time.perf_counter()
    response = requests.get(URL, params=params, headers=HEADERS)
    elapsed = time.perf_counter() - start

    return query, response.status_code, elapsed


def main():
    overall_start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=len(SEARCH_QUERIES)) as executor:
        futures = [
            executor.submit(make_request, query)
            for query in SEARCH_QUERIES
        ]

        for future in as_completed(futures):
            query, status, elapsed = future.result()
            print(f"Query='{query}' | status={status} | time={elapsed:.4f}s")

    total_time = time.perf_counter() - overall_start
    print(f"\nTotal elapsed time: {total_time:.4f}s")


if __name__ == "__main__":
    main()
