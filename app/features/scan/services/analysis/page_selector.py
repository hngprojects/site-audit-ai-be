import os
from typing import List
from openai import OpenAI

from app.platform.config import settings

# Load prompt template from utils
PROMPT_PATH = os.path.join(
    os.path.dirname(__file__), "../utils/PROMPT.md"
)


def load_prompt_template():
    """Load the prompt template from PROMPT.md file. Might tweak later"""
    with open(PROMPT_PATH, "r") as f:
        return f.read()


class PageSelectorService:

    @staticmethod
    def filter_important_pages(
        pages: List[str],
        top_n: int = 15,
        referer: str = "",
        site_title: str = ""
    ) -> List[str]:

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
