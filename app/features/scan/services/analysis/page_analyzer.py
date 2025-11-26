import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import google.generativeai as genai
import json

from app.platform.config import settings

logger = logging.getLogger(__name__)

GOOGLE_GEMINI_API_KEY = settings.GOOGLE_GEMINI_API_KEY

class Problem(BaseModel):
    icon: str = Field(description="warning or alert icon type")
    title: str
    description: str

class PageAnalysisResult(BaseModel):
    url: str = Field(description="URL of the analyzed page")
    overall_score: int = Field(description="Overall page score out of 100")
    scan_date: str = Field(description="Timestamp of when the scan was performed")

    ux_score: int = Field(description="UX score out of 100")
    ux_title: str = Field(description="UX section title (e.g., 'Usability')")
    ux_impact_message: str = Field(
        description="How UX issues affect business (2-3 sentences)")
    ux_impact_score: int = Field(description="UX impact score")
    ux_business_benefits: list[str] = Field(
        description="3-4 bullet points of business benefits of fixing UX issues")
    ux_problems: list[Problem] = Field(
        description="List of specific UX problems found")

    performance_score: int = Field(description="Performance score out of 100")
    performance_title: str = Field(description="Performance section title")
    performance_impact_message: str = Field(
        description="How performance issues affect business (2-3 sentences)")
    performance_impact_score: int = Field(description="Performance impact score")
    performance_business_benefits: list[str] = Field(
        description="3-4 bullet points of business benefits of fixing performance issues")
    performance_problems: list[Problem] = Field(
        description="List of specific performance problems found")

    seo_score: int = Field(description="SEO score out of 100")
    seo_title: str = Field(description="SEO section title")
    seo_impact_message: str = Field(
        description="How SEO issues affect business (2-3 sentences)")
    seo_impact_score: int = Field(description="SEO impact score")
    seo_business_benefits: list[str] = Field(
        description="3-4 bullet points of business benefits of fixing SEO issues")
    seo_problems: list[Problem] = Field(
        description="List of specific SEO problems found")


class ExtractorResponse(BaseModel):
    """Response from extractor service"""
    status_code: int
    status: str
    message: str
    data: Dict[str, Any]


class PageAnalyzerService:
    """
    Service for comprehensive web page analysis.
    Converts extractor service data into organized insights via a single LLM call.
    Formats output for mobile-friendly audit display.
    """

    @staticmethod
    def analyze_page(extractor_response: Dict[str, Any]) -> PageAnalysisResult:
        """
        Main entry point: Analyze extractor data and return organized results.

        Process:
        1. Validate extractor response
        2. Extract and prepare data
        3. Build comprehensive analysis prompt
        4. Make single LLM call for all analysis
        5. Return structured results formatted for mobile audit display

        Args:
            extractor_response: Response dict from extractor service containing:
                - status_code, status, message, data (with heading_data, images_data, etc.)

        Returns:
            PageAnalysisResult with all analysis sections formatted for frontend

        Raises:
            ValueError: If response is invalid or missing required data
            Exception: If LLM call fails
        """
        try:
            PageAnalyzerService._validate_extractor_response(
                extractor_response)

            prepared_data = PageAnalyzerService._prepare_extractor_data(
                extractor_response.get("data", {})
            )

            analysis_prompt = PageAnalyzerService._build_analysis_prompt(
                prepared_data)

            raw = PageAnalyzerService._call_llm(analysis_prompt)
            result = PageAnalyzerService._clean_up_llm_response(raw.model_dump())
            
            logger.info(
                f"Page analysis complete: {result.get('overall_score')}/100 for {result.get('url')}")
            return result

        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during page analysis: {str(e)}")
            raise

    @staticmethod
    def _validate_extractor_response(response: Dict[str, Any]) -> None:
        """Validate extractor response structure and status."""
        if not response:
            raise ValueError("Extractor response is empty")

        if response.get("status_code") != 200:
            raise ValueError(
                f"Extractor returned status {response.get('status_code')}: "
                f"{response.get('message', 'Unknown error')}"
            )

        if not response.get("data"):
            raise ValueError("Extractor response contains no data")

        data = response.get("data", {})
        if not data.get("metadata_data", {}).get("url"):
            raise ValueError("No URL found in extractor response")

    @staticmethod
    def _prepare_extractor_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and prepare data from extractor response.
        Handles missing or incomplete data gracefully.
        """
        try:
            metadata = data.get("metadata_data", {})
            heading_data = data.get("heading_data", {})
            images_data = data.get("images_data", [])
            issues_data = data.get("issues_data", {})
            text_content = data.get("text_content_data", {})

            all_headings = []
            for key in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                all_headings.extend(heading_data.get(key, []))

            accessibility_issues = {
                "images_missing_alt": issues_data.get("images_missing_alt", []),
                "inputs_missing_label": issues_data.get("inputs_missing_label", []),
                "buttons_missing_label": issues_data.get("buttons_missing_label", []),
                "links_missing_label": issues_data.get("links_missing_label", []),
                "empty_headings": issues_data.get("empty_headings", [])
            }

            seo_issues = {
                "title": metadata.get("title", {}),
                "description": metadata.get("description", {}),
                "canonical_url": metadata.get("canonical_url"),
                "has_title": metadata.get("has_title", False),
                "has_description": metadata.get("has_description", False),
                "total_issues": metadata.get("total_issues", 0)
            }

            prepared = {
                "url": metadata.get("url"),
                "scan_date": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "heading_data": heading_data,
                "headings_count": len(all_headings),
                "images": images_data,
                "images_count": len(images_data),
                "images_with_alt": sum(1 for img in images_data if img.get("alt")),
                "accessibility_issues": accessibility_issues,
                "text_content": text_content,
                "word_count": text_content.get("word_count", 0),
                "readability_score": text_content.get("readability_score", 0),
                "keyword_analysis": text_content.get("keyword_analysis", {}),
                "seo_issues": seo_issues,
                "viewport": metadata.get("viewport"),
                "has_canonical": bool(metadata.get("canonical_url")),
                "metadata_overall_valid": metadata.get("overall_valid", False)
            }

            logger.info(f"Data prepared for URL: {prepared['url']}")
            return prepared

        except Exception as e:
            logger.error(f"Error preparing extractor data: {str(e)}")
            raise

    @staticmethod
    def _build_analysis_prompt(prepared_data: Dict[str, Any]) -> str:
        """Build comprehensive analysis prompt from prepared data."""
        return f"""
    You are an expert web auditor analyzing page performance across UX, Performance, and SEO.
    Format your response ONLY as valid JSON matching the specified schema.

    Analyze this page data:

    URL: {prepared_data['url']}
    Scan Date: {prepared_data['scan_date']}

    CONTENT METRICS:
    - Word Count: {prepared_data['word_count']}
    - Readability Score: {prepared_data['readability_score']}
    - Headings Count: {prepared_data['headings_count']}
    - H1 Tags: {len(prepared_data['heading_data'].get('h1', []))}
    - H2 Tags: {len(prepared_data['heading_data'].get('h2', []))}
    - Headings Data: {prepared_data['heading_data']}

    IMAGES & MEDIA:
    - Total Images: {prepared_data['images_count']}
    - Images with Alt Text: {prepared_data['images_with_alt']}
    - Sample Images: {prepared_data['images'][:5] if prepared_data['images'] else 'None'}

    ACCESSIBILITY ISSUES:
    - Missing Alt Text: {len(prepared_data['accessibility_issues']['images_missing_alt'])} images
    - Missing Input Labels: {len(prepared_data['accessibility_issues']['inputs_missing_label'])}
    - Missing Button Labels: {len(prepared_data['accessibility_issues']['buttons_missing_label'])}
    - Missing Link Labels: {len(prepared_data['accessibility_issues']['links_missing_label'])}
    - Empty Headings: {len(prepared_data['accessibility_issues']['empty_headings'])}
    - Details: {prepared_data['accessibility_issues']}

    SEO METRICS:
    - Title: {prepared_data['seo_issues']['title'].get('value')} (Length: {prepared_data['seo_issues']['title'].get('length')})
    - Title Valid: {prepared_data['seo_issues']['title'].get('is_valid')}
    - Title Issues: {prepared_data['seo_issues']['title'].get('issues', [])}
    - Description: {prepared_data['seo_issues']['description'].get('value')} (Length: {prepared_data['seo_issues']['description'].get('length')})
    - Description Valid: {prepared_data['seo_issues']['description'].get('is_valid')}
    - Description Issues: {prepared_data['seo_issues']['description'].get('issues', [])}
    - Has Canonical URL: {prepared_data['has_canonical']}
    - Canonical URL: {prepared_data['seo_issues']['canonical_url']}
    - Viewport: {prepared_data['viewport']}
    - Total Metadata Issues: {prepared_data['seo_issues']['total_issues']}

    KEYWORD ANALYSIS:
    {prepared_data['keyword_analysis']}

    For each section (UX, Performance, SEO), provide:
    1. A score (0-100)
    2. A title (e.g., "Usability", "Performance", "SEO")
    3. An impact_message explaining business consequences (2-3 sentences)
    4. An impact_score (0-100) for that specific metric
    5. business_benefits: 3-4 bullet points of what fixing issues would do
    6. problems: specific issues found with:
    - icon: "warning" or "alert"
    - title: problem name
    - description: specific issue details

    Use the accessibility_issues, text_content metrics, and SEO metadata to inform UX and SEO scores.
    Make scores realistic and actionable. Include real problems found.
    Calculate overall_score as average of three section scores.
    """

    @staticmethod
    def _call_llm(prompt: str) -> PageAnalysisResult:
        """
        Call Gemini API with structured output.
        Includes error handling for API failures.
        """
        try:
            genai.configure(api_key=GOOGLE_GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-2.5-flash-lite')

            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=PageAnalysisResult
                )
            )

            print(f"Gemini Response: {response.text}")
            result_data = json.loads(response.text)
            result = PageAnalysisResult(**result_data)

            logger.info(f"Gemini API analysis completed for {result.url}")
            return result

        except Exception as e:
            logger.error(f"Gemini API call failed: {str(e)}")
            raise
    
    @staticmethod
    def _clean_up_llm_response(raw: dict) -> dict:
        """
        Convert flattened LLM output into the structured PageAnalysisResult format.

        {
            url: str,
            overall_score: int,
            scan_date: str,
            ux: AnalysisSection,
            performance: AnalysisSection,
            seo: AnalysisSection
        }
        """

        def build_section(prefix: str):
            return {
                "score": raw[f"{prefix}_score"],
                "title": raw[f"{prefix}_title"],
                "impact_message": raw[f"{prefix}_impact_message"],
                "impact_score": raw[f"{prefix}_impact_score"],
                "business_benefits": raw[f"{prefix}_business_benefits"],
                "problems": raw[f"{prefix}_problems"],
            }
            
        print(f'raw: {raw}')

        formatted = {
            "url": raw["url"],
            "overall_score": raw.get("overall_score", ''),
            "scan_date": raw["scan_date"],
            "ux": build_section("ux"),
            "performance": build_section("performance"),
            "seo": build_section("seo"),
        }

        return formatted
