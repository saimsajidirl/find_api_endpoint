# API Endpoint Extractor

A powerful network sniffer bot that captures and logs all API endpoints from any website. Built with Scrawlee, this tool automatically intercepts XHR, fetch, and other network requests, saving complete request/response data for analysis.

## Features

- **Automatic API Detection**: Captures XHR, fetch, and other network requests automatically
- **Complete Request/Response Logging**: Saves headers, body, status codes, and timing data
- **Organized Output**: Separates XHR/fetch APIs from other requests
- **Individual API Files**: Each API call saved as a separate JSON file with meaningful names
- **Proxy Support**: Rotate through multiple proxies from .env file
- **Custom Site Actions**: Extensible architecture for site-specific interactions
- **Chrome Profile**: Uses persistent browser profile for consistent behavior
- **Image Blocking**: Blocks images to speed up scraping and reduce bandwidth
- **Detailed Statistics**: Provides session summary with request counts

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd find_api_endpoint
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root (optional, for proxy support):
```env
PROXIES=http://proxy1:port,http://proxy2:port,http://proxy3:port
```

## Usage

### Basic Usage

Run the bot with a target URL:

```bash
python extract_api_endpoints.py --url https://example.com
```

### Command Line Options

- `--url` (required): Website URL to monitor
- `--headless`: Run in headless mode (default: headful with visible browser)
- `--action`: Choose site action class (default: `default`, options: `default`, `ecommerce`)

### Examples

**Headful mode (visible browser):**
```bash
python extract_api_endpoints.py --url https://example.com
```

**Headless mode (background):**
```bash
python extract_api_endpoints.py --url https://example.com --headless
```

**With e-commerce scraper:**
```bash
python extract_api_endpoints.py --url https://shop.example.com --action ecommerce
```

## Output Structure

The tool creates the following directory structure:

```
Extracted_APIs/
├── Xhr_Fetch_APIs/
│   ├── xhr_fetch_apis.json
│   ├── 001_GET_api_users_2024-05-03_10-30-00.json
│   ├── 002_POST_api_auth_2024-05-03_10-30-05.json
│   └── ...
└── All_APIs/
    ├── all_apis.json
    ├── 003_GET_document_2024-05-03_10-30-00.json
    ├── 004_GET_stylesheet_2024-05-03_10-30-01.json
    └── ...
```

### Output Files

- **xhr_fetch_apis.json**: Combined JSON of all XHR/fetch requests
- **all_apis.json**: Combined JSON of all captured requests
- **Individual files**: Each API call saved separately with format: `{index}_{method}_{endpoint}_{timestamp}.json`

### API Log Format

Each API log contains:

```json
{
  "timestamp": "2024-05-03T10:30:00.123456",
  "resource_type": "xhr",
  "request": {
    "method": "GET",
    "url": "https://api.example.com/users",
    "headers": {
      "Authorization": "Bearer token",
      "Content-Type": "application/json"
    },
    "body": null
  },
  "response": {
    "status_code": 200,
    "headers": {
      "content-type": "application/json",
      "content-length": "1234"
    },
    "body": { ... },
    "content_type": "application/json",
    "size_bytes": 1234
  },
  "duration_ms": 245.67,
  "error": null
}
```

## Architecture

### Core Components

1. **ProxyManager**: Handles proxy loading and rotation from .env file
2. **NetworkInterceptor**: Captures and stores all network requests
3. **SiteActions**: Abstract base class for site-specific interactions
4. **NetworkSnifferBot**: Main bot that orchestrates browser automation

### Data Classes

- **APIRequest**: Stores request details (method, URL, headers, body)
- **APIResponse**: Stores response details (status, headers, body, size)
- **APILog**: Combines request, response, timestamp, and error info

### Site Actions

- **DefaultActions**: Basic page metadata extraction (title, element counts)
- **EcommerceActions**: Example e-commerce product scraper (title, price)

## Customization

### Creating Custom Site Actions

Create a new class inheriting from `SiteActions`:

```python
class CustomActions(SiteActions):
    """Custom site-specific actions."""
    
    def run(self) -> Dict[str, Any]:
        """Execute custom scraping logic."""
        logger.info("Running custom actions...")
        
        # Your custom logic here
        data = self.response.html.css(".custom-selector")
        
        return {
            "custom_data": data,
            "status": "success"
        }
```

Then use it with the bot:

```python
bot = NetworkSnifferBot(
    url="https://example.com",
    headless=True,
    action_class=CustomActions
)
bot.run()
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Proxies (comma or newline separated)
PROXIES=http://user:pass@proxy1:8080,http://user:pass@proxy2:8080
```

### Browser Settings

The bot uses these default settings:
- Chrome profile: `scrawlee_network_logger`
- Image blocking: Enabled
- Cloudflare bypass: Disabled
- Google routing: Enabled

## Session Summary

After each run, the bot displays a summary:

```
================================================================================
Session Summary
================================================================================
Duration: 30.25s
Total Requests: 45
API Calls: 45
XHR/Fetch Calls: 23
Other APIs: 22

Extracted APIs saved to: Extracted_APIs
Logs saved to: logs
================================================================================
```

## Troubleshooting

### No APIs Captured

- Ensure the website makes API calls (XHR/fetch)
- Check if the site requires JavaScript to load
- Try increasing the wait time in the `run()` method

### Proxy Issues

- Verify proxy format: `http://user:pass@host:port`
- Check proxy credentials are correct
- Test proxy connectivity manually

### Browser Not Loading

- Ensure Chrome/Chromium is installed
- Check if headless mode works better
- Verify network connectivity

## Requirements

- scrawlee
- python-dotenv
- loguru

See `requirements.txt` for full dependency list.

## License

This project is open source and available under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Author

Created for API endpoint discovery and analysis.
