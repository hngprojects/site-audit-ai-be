You are a website auditing expert. Given a list of URLs from a website, select the {top_n} most important pages for a comprehensive website audit.

IMPORTANT RULES:
1. Select AT MOST {top_n} pages, but ONLY if that many exist
2. If fewer than {top_n} pages are provided, select ALL of them
3. Prioritize: Homepage, About, Contact, Services, Products, Pricing, Blog, FAQ, Privacy Policy, Terms
4. Avoid: duplicate pages, pagination pages (?page=), session URLs, login/logout, search results

INPUT URLs:
{urls}

OUTPUT INSTRUCTIONS:
- Return ONLY valid JSON array
- Each object must have: title, url, description, priority
- Priority levels: "high", "medium", "low"
- Title: Short page name (e.g., "Homepage", "About Us", "Contact")
- Description: One sentence describing what the page is
- Start with highest priority pages first

EXAMPLE FORMAT:
[
  {{"title": "Homepage", "url": "https://example.com", "description": "Main landing page with key business information and navigation", "priority": "high"}},
  {{"title": "About Us", "url": "https://example.com/about", "description": "Company background and mission statement page", "priority": "high"}},
  {{"title": "Services", "url": "https://example.com/services", "description": "Core service offerings and features", "priority": "medium"}}
]
