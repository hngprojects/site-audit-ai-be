from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

# Replace with env vars in production
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY') 
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/"

client = OpenAI(
    api_key=GOOGLE_API_KEY,
    base_url=BASE_URL
)

gemini_model = "gemini-2.5-flash"

# --- 1. Define Child Models ---
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

# --- 2. Define Parent Model (The Fix) ---
class FullAuditResult(BaseModel):
    ux: UXAnalysis
    seo: SEOAnalysis
    speed: SpeedAnalysis

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
            response_format=output_model # Must be a Pydantic class, not 'dict'
        )
        # Returns an instance of the Pydantic model
        return response.choices[0].message.parsed

    async def analyze_page(self, url: str, content: str) -> FullAuditResult:
        # Note: When using structured outputs (.parse), you don't strictly need 
        # to describe the JSON format in the prompt, the SDK handles the schema.
        system_prompt = """
        You are an expert web auditor with knowledge in UX, SEO, and web performance.
        Analyze the provided page content thoroughly.
        """

        user_prompt = f"""
        Page URL: {url}
        Page Content:
        {content}
        """

        # PASS THE PARENT PYDANTIC MODEL HERE
        return self._call_llm(system_prompt, user_prompt, FullAuditResult)