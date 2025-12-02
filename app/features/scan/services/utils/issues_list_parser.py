from typing import Dict, Any
from app.features.scan.services.utils.scan_result_parser import get_short_description


def parse_detailed_audit_report(data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform detailed audit report into category-specific report with all categories."""
    job_id = data["job_id"]
    score_overall = data["score_overall"]
    summary = data["summary"]
    scanned_at = data["scanned_at"]
    issues = data["issues"]

    category_titles = {
        "seo": "Visibility",
        "usability": "Not Mobile-Friendly",
        "performance": "Slow Loading Speed"
    }

    category_sections = {
        "seo": "Search Engine Optimization",
        "performance": "Performance",
        "usability": "Mobile Experience",
    }

    categories = []

    for category_key in ["seo", "performance", "usability"]:
        category_issues = [
            issue for issue in issues if issue["category"] == category_key]

        problems = []
        impacts = [f"Improved {category_key} performance"]
        recommendations = []

        seen_titles = set()
        seen_impact = set()
        seen_recommendations = set()

        for issue in category_issues:
            if issue["title"] not in seen_titles:
                problems.append({
                    "title": issue["title"],
                    "description": issue["description"]
                })

                seen_titles.add(issue["title"])

            if issue['business_impact'] not in seen_impact:
                impacts.append(issue['business_impact'])

                seen_impact.add(issue['business_impact'])

            if issue['recommendation'] not in seen_recommendations:
                recommendations.append(issue['recommendation'])

                seen_recommendations.add(issue['recommendation'])

        category_score = data[f'score_{category_key}']

        category_obj = {
            "key": category_key,
            "title": category_titles.get(category_key, category_key),
            "description": get_short_description(category_key, category_score),
            "section_title": category_sections.get(category_key, category_key.capitalize()),
            "score": category_score,
            "score_max": 100,
            "business_impact": impacts,
            "problems": problems,
            "suggestion": recommendations
        }

        categories.append(category_obj)

    return {
        "job_id": job_id,
        "website_score": score_overall,
        "scan_date": scanned_at,
        "summary_message": summary,
        "categories": categories
    }
