import json
import time
import os
import logging
import argparse
from abc import ABC, abstractmethod
from playwright.sync_api import sync_playwright

os.makedirs("logs", exist_ok=True)

API_LOG = "logs/apis_xhr_fetch.jsonl"
IMG_LOG = "logs/images_media.jsonl"
OTHER_LOG = "logs/other_requests.jsonl"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("network-logger")

class NetworkLogger:

    def log_response(self, response):
        try:
            req = response.request

            record = {
                "ts": time.time(),
                "method": req.method,
                "url": response.url,
                "status": response.status,
                "resource_type": req.resource_type,
                "content_type": response.headers.get("content-type", ""),
                "request_headers": dict(req.headers),
            }

            if req.post_data:
                record["request_body"] = req.post_data[:3000]

            ct = record["content_type"].lower()
            rt = req.resource_type

            try:
                if "json" in ct:
                    record["body"] = response.json()
                elif "text" in ct or "html" in ct or "xml" in ct:
                    record["body"] = response.text()[:5000]
            except Exception as e:
                record["body_error"] = str(e)

            if rt in ("xhr", "fetch"):
                logfile = API_LOG
                logger.info(f"API {record['status']} {record['method']} {record['url']}")
            elif rt in ("image", "media", "font"):
                logfile = IMG_LOG
            else:
                logfile = OTHER_LOG

            with open(logfile, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        except Exception as e:
            logger.error(f"Logging error: {e}")

    def log_request(self, request):
        logger.debug(f"REQ {request.method} {request.url}")


class SiteActions(ABC):
    """All site interaction logic goes here (future)."""

    def __init__(self, page):
        self.page = page

    @abstractmethod
    def run(self):
        pass


class DefaultActions(SiteActions):
    """Currently does nothing. Placeholder for future logic."""

    def run(self):
        logger.info("No site actions implemented yet (placeholder).")
        pass

class NetworkSnifferBot:

    def __init__(self, url: str, headless=False):
        self.url = url
        self.headless = headless
        self.net_logger = NetworkLogger()

    def run(self):

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless, slow_mo=120)

            context = browser.new_context(
                viewport={"width": 1400, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                )
            )

            page = context.new_page()

            page.on("response", self.net_logger.log_response)
            page.on("request", self.net_logger.log_request)
            page.on("requestfailed", lambda r: logger.warning(f"FAILED {r.method} {r.url}"))

            logger.info(f"Opening: {self.url}")
            page.goto(self.url, wait_until="networkidle", timeout=90000)

            actions = DefaultActions(page)
            actions.run()

            logger.info("Collecting background traffic...")
            time.sleep(25)

            logger.info("Finished. Logs are in /logs folder.")
            browser.close()

def main():
    parser = argparse.ArgumentParser(description="Universal Website Network Logger Bot")
    parser.add_argument("--url", required=True, help="Website URL to open")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")

    args = parser.parse_args()

    bot = NetworkSnifferBot(url=args.url, headless=args.headless)
    bot.run()


if __name__ == "__main__":
    main()
