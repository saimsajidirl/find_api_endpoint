import json
import time
import os
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from dotenv import load_dotenv
from scrawlee import BrowserClient, BrowserResponse
from loguru import logger

load_dotenv()

EXTRACTED_APIS_DIR = Path("Extracted_APIs")
XHR_FETCH_DIR = EXTRACTED_APIS_DIR / "Xhr_Fetch_APIs"
ALL_APIS_DIR = EXTRACTED_APIS_DIR / "All_APIs"

EXTRACTED_APIS_DIR.mkdir(exist_ok=True)
XHR_FETCH_DIR.mkdir(exist_ok=True)
ALL_APIS_DIR.mkdir(exist_ok=True)

logger.info(f"API extraction directories created at {EXTRACTED_APIS_DIR}")


@dataclass
class APIRequest:
    """Stores API request details.
    Contains method, URL, headers, body, and query params.
    Used to structure request data for logging."""
    method: str
    url: str
    headers: Dict[str, str]
    body: Optional[str] = None
    query_params: Optional[Dict[str, str]] = None


@dataclass
class APIResponse:
    """Stores API response details.
    Contains status code, headers, body, content type, and size.
    Used to structure response data for logging."""
    status_code: int
    headers: Dict[str, str]
    body: Any
    content_type: str
    size_bytes: int


@dataclass
class APILog:
    """Stores complete API transaction.
    Combines request, response, timestamp, and error info.
    Used to log full API call details."""
    timestamp: str
    resource_type: str  # "xhr", "fetch", "other"
    request: Dict[str, Any]
    response: Dict[str, Any]
    duration_ms: float
    error: Optional[str] = None


class ProxyManager:
    """Manages proxy rotation from .env file.
    Loads proxies and rotates through them.
    Returns next proxy in sequence."""

    def __init__(self):
        self.proxies: List[str] = []
        self.current_index = 0
        self.load_proxies()

    def load_proxies(self):
        """Load proxies from .env file.
        Parses comma or newline separated proxy list.
        Stores proxies for rotation."""
        proxies_str = os.getenv("PROXIES", "")

        if not proxies_str:
            logger.warning("No PROXIES found in .env file. Running without proxy.")
            return

        proxies = [p.strip() for p in proxies_str.replace("\n", ",").split(",") if p.strip()]

        if proxies:
            self.proxies = proxies
            logger.info(f"Loaded {len(proxies)} proxies from .env")
            for i, proxy in enumerate(proxies[:3]):
                masked = self._mask_proxy(proxy)
                logger.debug(f"Proxy {i+1}: {masked}")
        else:
            logger.warning("PROXIES field in .env is empty")

    def _mask_proxy(self, proxy: str) -> str:
        """Hide proxy credentials in logs.
        Replaces username/password with asterisks.
        Keeps domain visible for debugging."""
        if "@" in proxy:
            parts = proxy.split("@")
            return f"***@{parts[-1]}"
        return proxy

    def get_next_proxy(self) -> Optional[str]:
        """Return next proxy from list.
        Rotates through available proxies.
        Returns None if no proxies configured."""
        if not self.proxies:
            return None

        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy

class NetworkInterceptor:
    """Captures and logs network requests.
    Stores API calls in memory for later export.
    Separates XHR/fetch from other requests."""

    def __init__(self):
        self.api_logs: List[APILog] = []
        self.xhr_fetch_logs: List[APILog] = []
        self.request_count = 0
        self.api_count = 0
        self.xhr_fetch_count = 0

    def log_api_request(
        self,
        method: str,
        url: str,
        resource_type: str,
        headers: Dict[str, str],
        body: Optional[str] = None,
        status_code: int = 0,
        response_headers: Optional[Dict[str, str]] = None,
        response_body: Optional[Any] = None,
        response_size: int = 0,
        duration_ms: float = 0,
        error: Optional[str] = None,
    ):
        """Record API request and response details.
        Creates log entry with timestamp and metadata.
        Separates XHR/fetch from other requests."""
        self.request_count += 1
        self.api_count += 1

        if resource_type in ("xhr", "fetch"):
            self.xhr_fetch_count += 1

        timestamp = datetime.now().isoformat()

        request_obj = {
            "method": method,
            "url": url,
            "headers": headers,
            "body": body,
        }

        response_obj = {
            "status_code": status_code,
            "headers": response_headers or {},
            "body": response_body,
            "content_type": (response_headers or {}).get("content-type", "unknown"),
            "size_bytes": response_size,
        }

        api_log = APILog(
            timestamp=timestamp,
            resource_type=resource_type,
            request=request_obj,
            response=response_obj,
            duration_ms=duration_ms,
            error=error,
        )

        self.api_logs.append(api_log)

        if resource_type in ("xhr", "fetch"):
            self.xhr_fetch_logs.append(api_log)

        log_msg = f"{resource_type.upper()} {status_code} {method} {url}"
        if error:
            logger.error(f"{log_msg} | Error: {error}")
        else:
            logger.info(log_msg)

    def save_api_responses(self):
        """Export captured APIs to JSON files.
        Saves XHR/fetch and all APIs separately.
        Also creates individual files per API."""
        logger.info(f"Saving {len(self.api_logs)} API responses...")

        if self.xhr_fetch_logs:
            xhr_file = XHR_FETCH_DIR / "xhr_fetch_apis.json"
            self._save_to_file(xhr_file, self.xhr_fetch_logs)
            logger.success(f"Saved {len(self.xhr_fetch_logs)} XHR/Fetch APIs to {xhr_file}")

        if self.api_logs:
            all_file = ALL_APIS_DIR / "all_apis.json"
            self._save_to_file(all_file, self.api_logs)
            logger.success(f"Saved {len(self.api_logs)} total APIs to {all_file}")

        self._save_individual_apis()

    def _save_to_file(self, filepath: Path, logs: List[APILog]):
        """Write logs to JSON file.
        Converts dataclass objects to dictionaries.
        Uses pretty formatting for readability."""
        try:
            data = [asdict(log) for log in logs]
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            logger.debug(f"Saved {len(logs)} logs to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save to {filepath}: {e}")

    def _save_individual_apis(self):
        """Create separate JSON file per API.
        Names files using method, endpoint, and timestamp.
        Organizes into XHR/fetch or all APIs folders."""
        logger.info("Saving individual API responses...")

        for i, api_log in enumerate(self.api_logs, 1):
            try:
                url = api_log.request["url"]
                method = api_log.request["method"]

                from urllib.parse import urlparse
                parsed = urlparse(url)
                endpoint = parsed.path.replace("/", "_").lstrip("_")[:50]

                if not endpoint:
                    endpoint = "root"

                timestamp = api_log.timestamp.replace(":", "-").replace("T", "_").split(".")[0]
                filename = f"{i:03d}_{method}_{endpoint}_{timestamp}.json"

                if api_log.resource_type in ("xhr", "fetch"):
                    filepath = XHR_FETCH_DIR / filename
                else:
                    filepath = ALL_APIS_DIR / filename

                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(asdict(api_log), f, indent=2, ensure_ascii=False, default=str)

                logger.debug(f"Saved individual API: {filename}")

            except Exception as e:
                logger.error(f"Failed to save individual API {i}: {e}")

    def get_summary(self) -> Dict[str, Any]:
        """Return statistics about captured requests.
        Includes total, API, XHR/fetch, and other counts.
        Used for session summary display."""
        return {
            "total_requests": self.request_count,
            "api_calls": self.api_count,
            "xhr_fetch_calls": self.xhr_fetch_count,
            "other_apis": self.api_count - self.xhr_fetch_count,
        }


class SiteActions(ABC):
    """Base class for site interactions.
    Defines interface for custom site actions.
    Subclasses implement specific scraping logic."""

    def __init__(self, response: BrowserResponse, interceptor: NetworkInterceptor):
        self.response = response
        self.interceptor = interceptor

    @abstractmethod
    def run(self) -> Dict[str, Any]:
        """Execute site-specific actions.
        Must be implemented by subclasses.
        Returns extracted data as dictionary."""
        pass


class DefaultActions(SiteActions):
    """Basic page metadata extractor.
    Collects title and element counts.
    Used when no custom actions needed."""

    def run(self) -> Dict[str, Any]:
        """Extract basic page information.
        Gets title and counts links, images, scripts, forms.
        Returns metadata dictionary."""
        logger.info("Running default page collection...")

        try:
            title_elem = self.response.html.css_first("title")
            title_text = title_elem.text() if title_elem else "No title"

            links = len(self.response.html.css("a")) if self.response.html else 0
            images = len(self.response.html.css("img")) if self.response.html else 0
            scripts = len(self.response.html.css("script")) if self.response.html else 0
            forms = len(self.response.html.css("form")) if self.response.html else 0

            logger.debug(f"Page contains: {links} links, {images} images, {scripts} scripts, {forms} forms")

            return {
                "title": title_text,
                "url": self.response.url,
                "status_code": self.response.status_code,
                "element_counts": {
                    "links": links,
                    "images": images,
                    "scripts": scripts,
                    "forms": forms,
                },
                "status": "success",
            }
        except Exception as e:
            logger.error(f"Error in DefaultActions: {e}", exc_info=True)
            return {"error": str(e), "status": "failed"}


class EcommerceActions(SiteActions):
    """E-commerce product scraper.
    Extracts product titles and prices.
    Demonstrates custom action implementation."""

    def run(self) -> Dict[str, Any]:
        """Extract product data from page.
        Finds product elements and gets title and price.
        Returns list of products with details."""
        logger.info("Running e-commerce scraper...")

        try:
            products = []
            product_elements = self.response.html.css("[data-product], .product-item, .product-card")

            for elem in product_elements[:10]:
                try:
                    title = elem.css_first("h2, .title, [data-product-name]")
                    price = elem.css_first(".price, [data-price]")
                    products.append({
                        "title": title.text() if title else "N/A",
                        "price": price.text() if price else "N/A",
                    })
                except Exception as e:
                    logger.debug(f"Error parsing product: {e}")

            logger.debug(f"Extracted {len(products)} products")

            return {
                "products_found": len(products),
                "products": products,
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Error in EcommerceActions: {e}", exc_info=True)
            return {"error": str(e), "status": "failed"}

class NetworkSnifferBot:
    """Main bot for network sniffing.
    Opens browser and captures all API calls.
    Supports custom site actions and proxies."""

    def __init__(
        self,
        url: str,
        headless: bool = False,
        action_class=None,
    ):
        self.url = url
        self.headless = headless
        self.action_class = action_class or DefaultActions
        self.interceptor = NetworkInterceptor()
        self.proxy_manager = ProxyManager()
        self.start_time = None

    def run(self):
        """Start browser and capture network traffic.
        Opens URL, runs actions, waits for API calls.
        Saves results and prints summary."""
        self.start_time = time.time()

        logger.info("=" * 80)
        logger.info("Network Sniffer Bot Started")
        logger.info("=" * 80)
        logger.info(f"Target URL: {self.url}")
        logger.info(f"Headless: {self.headless}")
        logger.info(f"Block Images: True")
        logger.info(f"Chrome Profile: Enabled")
        logger.info(f"Extracted APIs Directory: {EXTRACTED_APIS_DIR}")

        try:
            proxy = self.proxy_manager.get_next_proxy()
            if proxy:
                logger.info(f"Using proxy: {self.proxy_manager._mask_proxy(proxy)}")

            with BrowserClient(
                headless=self.headless,
                proxy=proxy,
                profile="scrawlee_network_logger",
                block_images=True,
                bypass_cloudflare=False,
                via_google=True,
            ) as client:

                logger.info(f"Opening URL: {self.url}")
                response = client.get(self.url)

                logger.info(f"Page loaded | Status: {response.status_code}")

                response_headers = {}
                if hasattr(response, 'headers'):
                    response_headers = dict(response.headers)
                elif hasattr(response, 'response_headers'):
                    response_headers = dict(response.response_headers)

                self.interceptor.log_api_request(
                    method="GET",
                    url=response.url,
                    resource_type="document",
                    headers=response_headers,
                    status_code=response.status_code,
                    response_headers=response_headers,
                    response_body=response.text[:500] if response.text else None,
                    response_size=len(response.text.encode('utf-8')) if response.text else 0,
                    duration_ms=response.elapsed.total_seconds() * 1000 if hasattr(response, 'elapsed') else 0,
                )

                logger.info("Executing site actions...")
                actions = self.action_class(response, self.interceptor)
                action_results = actions.run()
                logger.info(f"Action results: {action_results}")

                logger.info("Collecting background traffic for 30 seconds...")
                for i in range(30):
                    time.sleep(1)
                    if (i + 1) % 5 == 0:
                        logger.debug(f"Waiting... {i + 1}/30 seconds")

                logger.success("Network sniffer bot completed successfully")

        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            self.interceptor.log_api_request(
                method="GET",
                url=self.url,
                resource_type="document",
                headers={},
                status_code=0,
                error=str(e),
            )

        finally:
            self._finalize()

    def _finalize(self):
        """Save captured data and show summary.
        Exports APIs to JSON files.
        Displays session statistics."""
        duration = time.time() - self.start_time

        logger.info("=" * 80)
        logger.info("Finalizing...")
        logger.info("=" * 80)

        self.interceptor.save_api_responses()

        summary = self.interceptor.get_summary()
        logger.info("\n" + "=" * 80)
        logger.info("Session Summary")
        logger.info("=" * 80)
        logger.info(f"Duration: {duration:.2f}s")
        logger.info(f"Total Requests: {summary['total_requests']}")
        logger.info(f"API Calls: {summary['api_calls']}")
        logger.info(f"XHR/Fetch Calls: {summary['xhr_fetch_calls']}")
        logger.info(f"Other APIs: {summary['other_apis']}")
        logger.info(f"\nExtracted APIs saved to: {EXTRACTED_APIS_DIR}")
        logger.info("=" * 80 + "\n")


def main():
    """Parse arguments and run the bot.
    Handles command line input for URL and options.
    Creates bot instance and starts execution."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Advanced Network Logger Bot using Scrawlee"
    )
    parser.add_argument(
        "--url",
        required=True,
        help="Website URL to monitor",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode (default: headful)",
    )
    parser.add_argument(
        "--action",
        choices=["default", "ecommerce"],
        default="default",
        help="Which site action class to use",
    )

    args = parser.parse_args()

    action_class = EcommerceActions if args.action == "ecommerce" else DefaultActions

    bot = NetworkSnifferBot(
        url=args.url,
        headless=args.headless,
        action_class=action_class,
    )

    bot.run()


if __name__ == "__main__":
    main()