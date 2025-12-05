# URL Discovery Feature Documentation

## Overview

The URL Discovery feature allows authenticated users to discover and rank the most important URLs from a website. This feature combines lightweight web crawling with AI-powered page importance ranking.

## Endpoint

### POST `/api/v1/scan/discovery/discover-urls`

**Authentication:** Required (Bearer token)

**Description:** Discovers up to 15 pages from a website and returns the top 10 most important URLs ranked by an LLM.

## Request

### Request Body

```json
{
  "url": "https://example.com"
}
```

**Fields:**
- `url` (required, HttpUrl): The base URL of the website to discover pages from

### Headers

```
Authorization: Bearer <your_access_token>
Content-Type: application/json
```

## Response

### Success Response (200 OK)

```json
{
  "status_code": 200,
  "status": "success",
  "message": "Successfully discovered 10 important URLs",
  "data": {
    "base_url": "https://example.com",
    "discovered_count": 15,
    "important_urls": [
      {
        "url": "https://example.com",
        "rank": 1
      },
      {
        "url": "https://example.com/about",
        "rank": 2
      },
      {
        "url": "https://example.com/contact",
        "rank": 3
      },
      {
        "url": "https://example.com/services",
        "rank": 4
      },
      {
        "url": "https://example.com/products",
        "rank": 5
      },
      {
        "url": "https://example.com/pricing",
        "rank": 6
      },
      {
        "url": "https://example.com/blog",
        "rank": 7
      },
      {
        "url": "https://example.com/faq",
        "rank": 8
      },
      {
        "url": "https://example.com/privacy",
        "rank": 9
      },
      {
        "url": "https://example.com/terms",
        "rank": 10
      }
    ],
    "message": "Successfully discovered 10 important URLs"
  }
}
```

### No URLs Found (200 OK)

```json
{
  "status_code": 200,
  "status": "success",
  "message": "No URLs found for the given website",
  "data": {
    "base_url": "https://example.com",
    "discovered_count": 0,
    "important_urls": [],
    "message": "No URLs found for the given website"
  }
}
```

### Error Responses

#### 400 Bad Request - Invalid URL

```json
{
  "detail": "Invalid URL: Invalid URL format: missing domain"
}
```

#### 401 Unauthorized - Missing/Invalid Token

```json
{
  "detail": "Not authenticated"
}
```

#### 500 Internal Server Error - Discovery Failed

```json
{
  "detail": "Failed to discover URLs: <error message>"
}
```

## How It Works

### Process Flow

1. **URL Validation**
   - Validates the input URL format
   - Ensures the URL has a valid scheme (http/https) and domain

2. **Page Discovery (Max 15 Pages)**
   - Uses Selenium with headless Chrome
   - Performs breadth-first search (BFS) crawling
   - Discovers up to 15 pages from the website
   - **Same Domain Validation**: Only includes URLs from the same base domain
     - Checks scheme (http/https) and netloc (domain)
     - Excludes subdomains and external links

3. **LLM-Based Ranking**
   - Sends discovered URLs to OpenRouter LLM (GLM-4.5-air:free)
   - LLM ranks pages based on importance for website audit
   - Prioritizes: Homepage, About, Contact, Services, Products, Pricing, Blog, FAQ, Privacy, Terms
   - Avoids: Login, Logout, Pagination, Search results

4. **Response Generation**
   - Returns top 10 most important URLs with ranking (1-10)
   - If fewer than 10 pages discovered, returns all discovered pages
   - If no pages found, returns empty array with appropriate message

## Features

### ✅ Implemented Requirements

- [x] **Max 15 URLs**: Discovers maximum of 15 pages from website
- [x] **Same Base URL Check**: Validates all URLs share the same base domain
- [x] **Authentication Check**: Requires logged-in user (Bearer token)
- [x] **POST Route**: Accepts URL in request body
- [x] **LLM Ranking**: Uses AI to rank pages by importance
- [x] **Top 10 Results**: Returns maximum of 10 most important URLs

### Key Features

1. **Smart Crawling**
   - Breadth-first search for better coverage
   - Automatic domain validation
   - Error handling for failed page loads

2. **Intelligent Selection**
   - LLM-powered importance ranking
   - Fallback heuristic if LLM fails
   - Deduplication and normalization

3. **Security**
   - Authentication required
   - URL validation and sanitization
   - Same-domain restriction prevents SSRF attacks

4. **Performance**
   - Lightweight discovery (max 15 pages)
   - Fast response times
   - Efficient crawling with BFS

## Example Usage

### cURL

```bash
curl -X POST "http://localhost:8000/api/v1/scan/discovery/discover-urls" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com"
  }'
```

### Python

```python
import requests

url = "http://localhost:8000/api/v1/scan/discovery/discover-urls"
headers = {
    "Authorization": "Bearer YOUR_ACCESS_TOKEN",
    "Content-Type": "application/json"
}
data = {
    "url": "https://example.com"
}

response = requests.post(url, headers=headers, json=data)
print(response.json())
```

### JavaScript (Fetch)

```javascript
const response = await fetch('http://localhost:8000/api/v1/scan/discovery/discover-urls', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer YOUR_ACCESS_TOKEN',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    url: 'https://example.com'
  })
});

const data = await response.json();
console.log(data);
```

## Technical Details

### Service Layer

#### PageDiscoveryService

**Location:** `app/features/scan/services/discovery/page_discovery.py`

**Key Methods:**
- `discover_pages(url, max_pages=15)`: Discovers pages using Selenium
- `_is_same_domain(url, base_domain)`: Validates same-domain URLs

**Technology:**
- Selenium WebDriver with Chrome
- Headless browser mode
- BFS crawling algorithm

#### PageSelectorService

**Location:** `app/features/scan/services/analysis/page_selector.py`

**Key Methods:**
- `filter_important_pages(pages, top_n=10)`: Selects important pages using LLM
- `_select_via_llm()`: Calls OpenRouter API for ranking
- `_fallback_selection()`: Heuristic-based selection if LLM fails

**Technology:**
- OpenRouter API (GLM-4.5-air:free model)
- Regex-based URL extraction
- Priority keyword matching

### Database

**Not Required:** This endpoint does not persist data to the database. It's a stateless operation that returns immediate results.

### Dependencies

- **Selenium**: Web browser automation
- **ChromeDriver**: Chrome browser driver
- **OpenRouter API**: LLM-based page ranking
- **FastAPI**: Web framework
- **Pydantic**: Data validation

## Performance Considerations

1. **Crawling Speed**: 
   - Approximately 1-3 seconds per page
   - Max 15 pages = ~15-45 seconds for discovery

2. **LLM API Call**: 
   - Approximately 2-5 seconds for ranking
   - Fallback to heuristics if LLM times out

3. **Total Response Time**: 
   - Typical: 20-50 seconds
   - Maximum: ~60 seconds (with timeouts)

## Error Handling

The endpoint includes comprehensive error handling:

1. **URL Validation Errors**: Returns 400 with specific error message
2. **Authentication Errors**: Returns 401 for missing/invalid tokens
3. **Crawling Errors**: Continues with successfully loaded pages
4. **LLM API Errors**: Falls back to heuristic-based selection
5. **System Errors**: Returns 500 with error details (in logs)

## Security Considerations

1. **Same-Domain Validation**: Prevents crawling external websites
2. **Authentication Required**: Only logged-in users can access
3. **Rate Limiting**: Consider implementing rate limits for production
4. **Input Validation**: URL format and scheme validation
5. **SSRF Prevention**: Same-domain check prevents server-side request forgery

## Future Enhancements

Potential improvements for future versions:

1. **Caching**: Cache discovery results for faster repeated requests
2. **Async Processing**: Queue discovery jobs for longer crawls
3. **Configurable Limits**: Allow users to specify max_pages and top_n
4. **Progress Updates**: WebSocket or SSE for real-time progress
5. **Advanced Filters**: Allow filtering by page type or content
6. **Export Options**: Export results in CSV or JSON format
7. **Scheduled Discovery**: Periodic URL discovery for monitoring

## Testing

See `tests/test_url_discovery.py` for comprehensive test suite.

**Test Coverage:**
- Same-domain validation
- URL discovery with mocked Selenium
- Authentication requirements
- LLM ranking integration
- Error handling scenarios
- Empty result handling

## Troubleshooting

### Common Issues

1. **ChromeDriver not found**
   - Solution: Set `CHROMEDRIVER_PATH` in environment variables
   - Or: Install chromedriver in system PATH

2. **Timeout errors**
   - Solution: Check network connectivity
   - Verify website is accessible
   - Consider increasing timeout values

3. **LLM API errors**
   - Solution: Verify `OPENROUTER_API_KEY` is set
   - Check API quota and rate limits
   - Fallback heuristics will be used automatically

4. **No URLs discovered**
   - Check if website blocks headless browsers
   - Verify website is accessible
   - Check for JavaScript-heavy SPAs (may need wait times)

## Support

For issues or questions:
- Check logs: `app/platform/logger.py`
- Review test suite: `tests/test_url_discovery.py`
- Contact development team

---

**Version:** 1.0.0  
**Last Updated:** December 5, 2025  
**Author:** Site Audit AI Team
