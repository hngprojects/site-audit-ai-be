"""
GO THROUGH THIS FILE!!! 
IMPORTANT TO UNDERSTAND FLOW OF THE SERVICES AS IS STRUCTURED FOR STRESS FREE CONTRIBUTIONS

Scan Services

Organized by responsibility for optimal efficiency:

1. discovery/ - URL enumeration and page discovery
   - page_discovery.py: Page crawling and link extraction

2. scraping/ - Browser automation and content capture
   - browser_pool.py: Browser instance management
   - page_scraper.py: HTML, screenshot, DOM capture
   - content_hasher.py: SHA256 hashing for cache keys

3. extraction/ - Parsing and metric computation
   - seo_extractor.py: Title, meta, headings, links
   - accessibility_extractor.py: ARIA, alt text, heading hierarchy
   - performance_extractor.py: TTFB, LCP, FCP, load time
   - design_extractor.py: Responsive, fonts, contrast

4. analysis/ - LLM integration
   - page_selector.py: LLM Call #1 - Select important pages
   - page_analyzer.py: LLM Call #2 - Score and find issues with methods like: analyze_accesibility(), analyze_seo(), analyze_performance() etc. 

# 5. orchestration/ - Job coordination
#    - job_coordinator.py: Main orchestration logic
#    - result_aggregator.py: Compute job-level results
#    - cache_manager.py: Redis cache operations

# 6. storage/ - Filesystem operations
#    - artifact_storage.py: Save HTML, screenshots, DOM
#    - job_storage.py: Job folder structure

7. issue/ - Issue management and formatting
   - issue_service.py: Fetch and format scan issues for API responses

"""
# Note: Some service modules are marked TODO and need implementation.