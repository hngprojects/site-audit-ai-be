"""Email service for sending scan reports to users."""
import os
from jinja2 import Environment, FileSystemLoader

from app.platform.services.email import send_email

# Set up Jinja2 environment for sites templates
current_dir = os.path.dirname(os.path.abspath(__file__))
sites_template_dir = os.path.join(current_dir, "../template")
auth_template_dir = os.path.join(current_dir, "../../auth/template")

# Fallback paths if running from different location
if not os.path.exists(sites_template_dir):
    sites_template_dir = os.path.join(os.getcwd(), "app/features/sites/template")
if not os.path.exists(auth_template_dir):
    auth_template_dir = os.path.join(os.getcwd(), "app/features/auth/template")

# Use multiple template directories so scan_report.html can extend base_email.html from auth
env = Environment(loader=FileSystemLoader([sites_template_dir, auth_template_dir]))


def send_scan_report_email(to_email: str, first_name: str, site_name: str, scan_results: dict):
    """Send periodic scan report email with results summary"""
    template = env.get_template("scan_report.html")
    html_content = template.render(
        first_name=first_name,
        site_name=site_name,
        score_overall=scan_results.get("score_overall", 0),
        score_seo=scan_results.get("score_seo", 0),
        score_accessibility=scan_results.get("score_accessibility", 0),
        score_performance=scan_results.get("score_performance", 0),
        score_design=scan_results.get("score_design", 0),
        critical_issues=scan_results.get("critical_issues_count", 0),
        warnings=scan_results.get("warning_issues_count", 0),
        total_issues=scan_results.get("total_issues", 0),
        job_id=scan_results.get("job_id"),
        dashboard_url=f"https://sitelytics.com/scan/{scan_results.get('job_id')}/results"
    )
    send_email(to_email, f"Scan Report for {site_name} - Sitelytics", html_content)
