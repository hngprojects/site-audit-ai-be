from typing import List
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from openai import OpenAI
from app.platform.config import settings
import os

PROMPT_PATH = os.path.join(
    os.path.dirname(__file__), "../utils/PROMPT.md"
)

def load_prompt_template():
    with open(PROMPT_PATH, "r") as f:
        return f.read()

class DiscoveryService:
    @staticmethod
    def discover_pages(url: str) -> List[str]:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        visited = set()
        to_visit = [url]
        pages = []

        while to_visit and len(visited) < 100:
            current = to_visit.pop()
            if current in visited:
                continue
            visited.add(current)
            driver.get(current)
            pages.append(current)
            links = driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                href = link.get_attribute("href")
                if href and href.startswith(url) and href not in visited:
                    to_visit.append(href)
        driver.quit()
        return pages

    @staticmethod
    def filter_important_pages(
        pages: List[str],
        top_n: int = 20,
        referer: str = "",
        site_title: str = ""
    ) -> List[str]:
        """Send pages to OpenRouter GLM-4.5 Air and get top N important pages."""
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY
        )
        prompt_template = load_prompt_template()
        prompt = prompt_template.format(
            top_n=top_n,
            urls="\n".join(pages)
        )
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": referer,
                "X-Title": site_title,
            },
            extra_body={},
            model="z-ai/glm-4.5-air:free",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        text = completion.choices[0].message.content
        important_pages = [line.strip() for line in text.splitlines() if "http" in line]
        return important_pages