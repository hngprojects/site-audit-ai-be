from datetime import datetime
from typing import Dict, List, Any

def get_category_title(key: str) -> str:
    """Get friendly category title."""
    title_mapping = {
        "seo": "Visibility",
        "usability": "Not Mobile-Friendly",
        "performance": "Slow Loading Speed"
    }
    return title_mapping.get(key, key)

def get_severity_from_score(score: int) -> str:
    """Determine severity based on score."""
    if score >= 80:
        return "good"
    elif score >= 60:
        return "warning"
    else:
        return "critical"

def get_short_description(key: str, score: int) -> str:
    """Generate short description based on category and score."""
    # Determine severity level based on score
    if score >= 80:
        severity_text = "excellent"
        action = "well optimized"
    elif score >= 60:
        severity_text = "good"
        action = "performing adequately"
    elif score >= 40:
        severity_text = "concerning"
        action = "needs improvement"
    else:
        severity_text = "critical"
        action = "needs immediate attention"
    
    # Generic descriptions based on severity
    descriptions = {
        "seo": f"Your search visibility is {severity_text} and {action}. Current score: {score}/100.",
        "usability": f"Mobile experience is {severity_text} and {action}. Current score: {score}/100.",
        "performance": f"Your site's loading speed is {severity_text} and {action}. Current score: {score}/100."
    }
    return descriptions.get(key, f"This area is {severity_text} and {action}. Current score: {score}/100.")

def generate_summary_message(score: int) -> str:
    """Generate summary message dynamically based on score ranges."""
    if score == 100:
        return "Your website is performing at its absolute best with a score of 100/100."
    elif score >= 90:
        return f"Your website is performing excellently with a score of {score}/100. There's room to reach perfection."
    elif score >= 80:
        return f"Your website is performing very well with a score of {score}/100. It can be improved further with minor optimizations."
    elif score >= 70:
        return f"Your website has a solid score of {score}/100. It can be improved by addressing issues in a few key areas."
    elif score >= 60:
        return f"Your website is performing adequately with a score of {score}/100. It can be significantly improved by addressing several issues."
    elif score >= 50:
        return f"Your website needs attention. With a score of {score}/100, it can be improved through several key enhancements."
    elif score >= 40:
        return f"Your website requires immediate attention. With a score of {score}/100, it can be substantially improved by addressing critical issues."
    elif score >= 30:
        return f"Your website has serious issues that need urgent attention. Score: {score}/100. It can be transformed through major improvements."
    else:
        return f"Your website score is {score}/100. It can be greatly improved with a comprehensive overhaul."

def parse_audit_report(data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform audit report from detailed structure to simplified category-based structure."""
    job_id = data["job_id"]
    results = data["results"]
    
    score_overall = results["score_overall"]
    score_seo = results.get("score_seo", 0)
    score_accessibility = results.get("score_accessibility", 0)
    score_performance = results.get("score_performance", 0)
    
    # Build categories with provided scores
    categories = [
        {
            "key": "seo",
            "title": get_category_title("seo"),
            "severity": get_severity_from_score(score_seo),
            "score": score_seo,
            "score_max": 100,
            "short_description": get_short_description("seo", score_seo)
        },
        {
            "key": "usability",
            "title": get_category_title("usability"),
            "severity": get_severity_from_score(score_accessibility),
            "score": score_accessibility,
            "score_max": 100,
            "short_description": get_short_description("usability", score_accessibility)
        },
        {
            "key": "performance",
            "title": get_category_title("performance"),
            "severity": get_severity_from_score(score_performance),
            "score": score_performance,
            "score_max": 100,
            "short_description": get_short_description("performance", score_performance)
        }
    ]
    
    # Build final output
    return {
        "job_id": job_id,
        "website_score": score_overall,
        "scan_date": datetime.now().strftime("%Y-%m-%d"),
        "summary_message": generate_summary_message(score_overall),
        "categories": categories
    }