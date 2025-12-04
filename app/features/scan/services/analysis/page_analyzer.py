import os
import logging
from typing import Dict, Any
from copy import deepcopy
from datetime import datetime
from pydantic import BaseModel, Field
from app.features.scan.schemas.page_analyzer import PageAnalysisResult
from openai import OpenAI
import json

from app.platform.config import settings

logger = logging.getLogger(__name__)


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

            result = PageAnalyzerService._merge_llm_with_formula(
                raw.model_dump(), prepared_data)

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
    def _calculate_formula_scores(prepared_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate formula-based scores using a configurable scoring map.
        Easier to maintain and extend.
        """
        acc_issues = prepared_data['accessibility_issues']
        seo_issues = prepared_data['seo_issues']

        score_map = {
            "accessibility": [
                {"value": len(acc_issues['images_missing_alt']), "weight": 0.4, "total": max(
                    prepared_data['images_count'], 1)},
                {"value": len(acc_issues['inputs_missing_label']), "weight": 0.15, "total": max(
                    len(acc_issues['inputs_missing_label']) + 1, 1)},
                {"value": len(acc_issues['buttons_missing_label']), "weight": 0.15, "total": max(
                    len(acc_issues['buttons_missing_label']) + 1, 1)},
                {"value": len(acc_issues['links_missing_label']), "weight": 0.15, "total": max(
                    len(acc_issues['links_missing_label']) + 1, 1)},
                {"value": len(acc_issues['empty_headings']), "weight": 0.15, "total": max(
                    len(acc_issues['empty_headings']), 1)},
            ],
            "performance": [
                {"value": prepared_data['images_count'],
                    "weight": 0.5, "total": 100},
                {"value": prepared_data['headings_count'],
                    "weight": 0.5, "total": 100},
                {"value": prepared_data['word_count'],
                    "weight": 1/5000, "total": 100},
            ],
            "seo": [
                {"value": seo_issues.get(
                    'total_issues', 0) * 2, "weight": 1, "total": 100},
                {"value": 0 if seo_issues.get(
                    'has_title') else 5, "weight": 1, "total": 100},
                {"value": 0 if seo_issues.get(
                    'has_description') else 5, "weight": 1, "total": 100},
                {"value": 0 if seo_issues.get(
                    'canonical_url') else 2, "weight": 1, "total": 100},
            ]
        }

        formula_scores = {}

        for section, rules in score_map.items():
            if section == "accessibility":
                weighted_pct = sum(
                    rule['weight'] * (rule['value'] / rule['total']) for rule in rules)
                score = max(0, 100 * (1 - weighted_pct))
            else:
                score = max(0, 100 - sum(rule['value'] for rule in rules))
            formula_scores[f"{section}_score_formula"] = round(score)

        return formula_scores

    @staticmethod
    def _merge_llm_with_formula(llm_response: dict, prepared_data: dict) -> dict:
        """
        Merge Gemini LLM response with formula-based scores to get final averaged scores.

        Args:
            llm_response (dict): Response from Gemini LLM
            prepared_data (dict): Prepared page data to calculate formula scores

        Returns:
            dict: Updated LLM response with averaged scores
        """

        merged_response = llm_response.copy()

        formula_scores = PageAnalyzerService._calculate_formula_scores(
            prepared_data)

        for section in ["accessibility", "performance", "seo"]:
            llm_score = merged_response[section + "_score"]
            formula_score = formula_scores[f"{section}_score_formula"]

            merged_response[section + "_score"] = round(
                (llm_score + formula_score) / 2)

        merged_response["overall_score"] = round(
            (merged_response["accessibility_score"] + merged_response["seo_score"] + merged_response["performance_score"]) / 3)

        return merged_response

    @staticmethod
    def _build_analysis_prompt(prepared_data: Dict[str, Any]) -> str:
        """Build comprehensive analysis prompt from prepared data."""
        return f"""
    You are an expert web auditor analyzing page performance across accessibility, Performance, and SEO.
    Format your response ONLY as valid JSON matching the specified schema.

    Analyze this page data:

    URL: {prepared_data['url']}

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

    For each section (accessibility, performance, SEO), provide:
    1. <section>_score: a number from 0-100
    2. <section>_issues: list of specific issues with:
        - title: short problem name
        - description: short, one-line sentence describing the issue
        - severity: low, medium, or high
        - score_impact: Positive Integer between 0-100 quantifying how this issue affects the total score
        - business_impact: short, one-line sentence explaining the impact
        - recommendation: short, one-line sentence with recommended action

    Use the accessibility_issues, text_content metrics, and SEO metadata to inform accessibility and SEO scores. Make scores realistic and actionable. Include real problems found. Ensure all text fields are concise and on a single line.
    """

    @staticmethod
    def _call_llm(prompt: str) -> PageAnalysisResult:
        """
        Call OpenRouter API with structured output.
        Includes error handling for API failures.
        """
        try:
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.OPENROUTER_API_KEY
            )

            # Add JSON schema instruction to the prompt
            schema_prompt = f"""{prompt}

You MUST respond with ONLY valid JSON matching this exact structure:
{{
  "url": "string",
  "scan_date": "string (YYYY-MM-DD HH:MM:SS)",
  
  "accessibility_score": number (0-100),
  "accessibility_issues": [{{"title": "string", "severity": "low|medium|high", "score_impact": number (0-100), "description": "string", "business_impact": "string", "recommendation": "string"}}, ...],
  
  "performance_score": number (0-100),
  "performance_issues": [{{"title": "string", "severity": "low|medium|high", "score_impact": number (0-100), "description": "string", "business_impact": "string", "recommendation": "string"}}, ...],

  "seo_score": number (0-100),
  "seo_issues": [{{"title": "string", "severity": "low|medium|high", "score_impact": number (0-100), "description": "string", "business_impact": "string", "recommendation": "string"}}, ...],
}}

Do not include any text before or after the JSON. Only output valid JSON."""

            completion = client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "https://sitemate-ai.com",
                    "X-Title": "SiteMate AI",
                },
                model="z-ai/glm-4.5-air:free",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a web auditing expert. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": schema_prompt
                    }
                ],
                temperature=0.7
            )

            response_text = completion.choices[0].message.content or ""
            print(f"OpenRouter Response: {response_text}")

            # Try to parse JSON - handle malformed responses
            try:
                result_data = json.loads(response_text)
            except json.JSONDecodeError as json_err:
                logger.error(f"JSON parse error: {json_err}")
                cleaned_text = response_text.strip()
                # Try to extract valid JSON by cleaning the response
                cleaned_text = response_text.strip()
                # Remove markdown code blocks if present
                if cleaned_text.startswith('```'):
                    cleaned_text = cleaned_text.split(
                        '\n', 1)[1] if '\n' in cleaned_text else cleaned_text
                    if cleaned_text.endswith('```'):
                        cleaned_text = cleaned_text.rsplit(
                            '\n', 1)[0] if '\n' in cleaned_text else cleaned_text
                    cleaned_text = cleaned_text.replace(
                        '```json', '').replace('```', '').strip()

                # If it starts with { and ends with }, try to find the last valid }
                if cleaned_text.startswith('{'):
                    last_brace = cleaned_text.rfind('}')
                    if last_brace > 0:
                        cleaned_text = cleaned_text[:last_brace + 1]
                        result_data = json.loads(cleaned_text)
                    else:
                        raise
                else:
                    raise

            result = PageAnalysisResult(**result_data)

            logger.info(f"OpenRouter API analysis completed for {result.url}")
            return result

        except Exception as e:
            logger.error(f"OpenRouter API call failed: {str(e)}")
            raise

    @staticmethod
    def flatten_issues(result: dict) -> list:
        """
        Convert accessibility/performance/seo issues from a raw dict
        into a unified list of IssueUnified-compatible dicts.
        """

        unified = []

        category_map = {
            "accessibility_issues": "accessibility",
            "performance_issues": "performance",
            "seo_issues": "seo",
        }

        for field_name, category in category_map.items():

            issues = result.get(field_name, [])
            # Ensure it's a list (LLMs sometimes return dict or None)
            if not isinstance(issues, list):
                continue

            for issue in issues:
                if not isinstance(issue, dict):
                    continue

                unified.append(
                    {
                        "page_url": result.get("url"),
                        "title": issue.get("title"),
                        "category": category,
                        "severity": issue.get("severity"),
                        "score_impact": issue.get("score_impact"),
                        "description": issue.get("description"),
                        "business_impact": issue.get("business_impact"),
                        "recommendation": issue.get("recommendation")
                    }
                )

        return unified
