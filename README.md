# Network Sniffer Bot

A universal website network logger and API endpoint finder. This tool uses Playwright to navigate to a specified URL, monitors all network traffic, and logs the details (requests, responses, headers, and bodies) into categorized JSONL files.

## Features

- Captures XHR and Fetch requests (API endpoints).
- Logs request and response headers.
- Captures response bodies (JSON, Text, HTML, XML).
- Categorizes logs into:
    - `apis_xhr_fetch.jsonl`: API calls and data fetching.
    - `images_media.jsonl`: Images, fonts, and media files.
    - `other_requests.jsonl`: Scripts, CSS, and other documents.
- Support for both headed and headless browser modes.

## Installation

1. Install the required Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Install the Playwright browser binaries:
   ```bash
   playwright install chromium
   ```

## Usage

Run the script by providing a target URL:

```bash
python app.py --url "https://example.com"
```

### Arguments

- `--url`: (Required) The website URL you want to sniff.
- `--headless`: (Optional) Run the browser in background (headless) mode.

### Example

```bash
python app.py --url "https://www.google.com" --headless
```

## Output

All logs are stored in the `logs/` directory:

- `logs/apis_xhr_fetch.jsonl`: Contains all intercepted API calls.
- `logs/images_media.jsonl`: Contains all image and media requests.
- `logs/other_requests.jsonl`: Contains everything else.

Each entry in the log files is a JSON object containing timestamp, method, URL, status, resource type, headers, and body content.
