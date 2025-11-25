from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

# Replace with OPENAI key for production. Right now I am using my google key and google's base URL
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/"

client = OpenAI(
    api_key=GOOGLE_API_KEY,
    base_url=BASE_URL
)

gemini_model = "gemini-2.5-flash"


class UXAnalysis(BaseModel):
    score: int
    issues: list[str]
    review: str


class SEOAnalysis(BaseModel):
    score: int
    issues: list[str]
    summary: str


class SpeedAnalysis(BaseModel):
    score: int
    warnings: list[str]
    summary: str


class PageAnalyzer:

    def __init__(self):
        self.client = client
        self.model = gemini_model

    def _call_llm(self, system_prompt: str, user_prompt: str, output_model: BaseModel):
        """Shared LLM calling method."""
        response = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format=output_model
        )

        return response.choices[0].message.parsed


    async def analyze_ux(self, url: str, content: str) -> UXAnalysis:

        system_prompt = """
        You are an expert UX auditor. Analyze a web page's structure and clarity.
        Respond ONLY in JSON with:
        - score: integer 0–100
        - issues: list of specific UI/UX issues
        - review: one-sentence summary
        """

        user_prompt = f"""
        Page URL: {url}

        Content:
        {content}
        """

        return self._call_llm(system_prompt, user_prompt, UXAnalysis)


    async def analyze_seo(self, url: str, content: str) -> SEOAnalysis:

        system_prompt = """
        You are an expert SEO analyst. You have been given the full frontend HTML source code of a web page. Your task is to thoroughly analyze the page’s content and SEO elements. 

Perform the following steps:

1. **Meta Information**  
   - Extract and evaluate the <title> tag. Comment on length, clarity, and keyword relevance.  
   - Extract and evaluate the meta description. Comment on presence, length, and relevance.  

2. **Heading Structure**  
   - Extract all headings (H1–H6).  
   - Assess hierarchy and keyword usage. Highlight missing or multiple H1 tags.  

3. **Content Analysis**  
   - Summarize the main content of the page.  
   - Identify primary keywords and topics.  
   - Comment on keyword density and natural flow (avoid keyword stuffing).  

4. **Links and Anchors**  
   - List internal and external links with anchor text.  
   - Flag missing alt text in linked images.  

5. **Images and Media**  
   - Extract images and check for alt attributes.  
   - Comment on SEO relevance of alt text.  

6. **Technical SEO Elements**  
   - Identify any canonical tags or structured data (JSON-LD, schema.org).  
   - Flag any missing or unusual technical SEO elements present in the HTML.  

7. **Scoring & Recommendations**  
   - Assign a **rough SEO score** (0–100) based only on the HTML content and structure.  
   - Provide actionable recommendations to improve SEO.  

Output your analysis in a **structured JSON format** like this:

{
  "meta": {...},
  "headings": {...},
  "content": {...},
  "links": {...},
  "images": {...},
  "technical": {...},
  "seo_score": 0-100,
  "recommendations": [...]
}

Notes:  
- Do not fetch external data; analyze only what is in the provided HTML.  
- Be detailed, concise, and actionable.  
- Focus on SEO best practices.

        """

        user_prompt = f"""
        URL: {url}

        Page Content:
        {content}
        """

        return self._call_llm(system_prompt, user_prompt, SEOAnalysis)


    async def analyze_speed(self, url: str, content: str) -> SpeedAnalysis:

        system_prompt = """
        You are a web performance expert. Analyze page performance factors
        based on structure and code hints (even without network profiling).
        Return ONLY JSON with:
        - score: integer 0–100
        - warnings: list of possible performance bottlenecks
        - summary: short explanation
        """

        user_prompt = f"""
        URL: {url}
        Content:
        {content}
        """

        return self._call_llm(system_prompt, user_prompt, SpeedAnalysis)
