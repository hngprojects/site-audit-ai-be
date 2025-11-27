from datetime import datetime
from typing import Dict, List, Any
import json
import re


def convert_scan_results(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Converts scan results from current format to desired format.
    Only includes fields with actual data - no placeholders.

    Args:
        raw_data: The raw scan results data

    Returns:
        Converted scan results in the desired format
    """
    job_id = raw_data['data']['job_id']
    status = raw_data['data']['status']
    results = raw_data['data']['results']

    # Extract issues and count by severity
    all_issues = []
    severity_map = {}
    issue_counter = 0

    for page in results.get('selected_pages', []):
        page_issues = extract_page_issues(page)
        for issue in page_issues:
            issue_counter += 1
            issue['job_id'] = job_id
            all_issues.append(issue)

            # Count by severity
            severity = issue['severity']
            severity_map[severity] = severity_map.get(severity, 0) + 1

    # Calculate issue counts
    critical_issues = severity_map.get('critical', 0)
    warning_issues = severity_map.get('warning', 0)
    info_issues = severity_map.get('info', 0)
    total_issues = len(all_issues)

    # Get scan date from first page
    scanned_at = results.get('selected_pages', [{}])[0].get(
        'analysis_details', {}).get('scan_date')
    if scanned_at:
        scanned_at = datetime.strptime(
            scanned_at, '%Y-%m-%d %H:%M:%S').isoformat() + 'Z'
    else:
        scanned_at = datetime.utcnow().isoformat() + 'Z'

    converted_result = {
        'job_id': job_id,
        'status': status,
        'url': extract_base_url(results.get('selected_pages', [])[0]['url']),
        'overall_score': results.get('score_overall'),
        'score_breakdown': {
            'seo': results.get('score_seo'),
            'accessibility': results.get('score_accessibility'),
            'performance': results.get('score_performance'),
        },
        'total_issues': total_issues,
        'critical_issues': critical_issues,
        'warning_issues': warning_issues,
        'info_issues': info_issues,
        'scanned_at': scanned_at,
        'pages_analyzed': results.get('pages_analyzed'),
        'issues': all_issues,
        '_links': {
            'self': f"/api/v1/scan/{job_id}/results",
            'status': f"/api/v1/scan/{job_id}",
            'issues': f"/api/v1/scan/{job_id}/issues"
        }
    }

    # Only add business impact if there are issues
    if all_issues:
        converted_result['business_impact'] = extract_business_impact(raw_data)

    # Only add affected elements if there are issues
    if all_issues:
        converted_result['affected_elements'] = extract_affected_elements(
            all_issues)

    # Only add resources if there are issues
    if all_issues:
        converted_result['resources'] = generate_resources(all_issues)

    return converted_result


def extract_base_url(url: str) -> str:
    """
    Extract base URL (protocol + domain) from a full URL.
    Removes hash fragments and paths.

    Args:
        url: Full URL

    Returns:
        Base URL (e.g., https://example.com)
    """
    # Regex pattern: protocol + domain + optional port, remove everything after
    match = re.match(r'(https?://[^/]+)', url)
    return match.group(1) if match else url


def extract_page_issues(page: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract issues from a page's analysis details.
    Only maps issues that actually exist in the data.

    Args:
        page: Page analysis data

    Returns:
        List of extracted issues
    """
    issues = []
    page_url = page.get('url')
    analysis = page.get('analysis_details', {})

    def add_issue(title: str, category: str, severity: str, short_desc: str, count: int = 1):
        """Helper function to add an issue"""
        issues.append({
            'title': title,
            'category': category,
            'severity': severity,
            'page_url': page_url,
            'short_description': short_desc,
            'affected_elements_count': count,
        })

    # Process usability issues
    usability_problems = analysis.get('usability', {}).get('problems', [])
    for problem in usability_problems:
        title = problem.get('title', '').split(' - ')[0]
        short_desc = (
            (problem.get('title', '').split(' - ')
             [1] if ' - ' in problem.get('title', '') else '')
            or problem.get('description', '').split('.')[0]
        )
        severity = 'critical' if problem.get('icon') == 'alert' else 'warning'

        add_issue(title, 'Usability', severity, short_desc)

    # Process SEO issues
    seo_problems = analysis.get('seo', {}).get('problems', [])
    for problem in seo_problems:
        title = problem.get('title', '').split(' - ')[0]
        short_desc = (
            (problem.get('title', '').split(' - ')
             [1] if ' - ' in problem.get('title', '') else '')
            or problem.get('description', '').split('.')[0]
        )
        severity = 'critical' if problem.get('icon') == 'alert' else 'warning'

        add_issue(title, 'SEO', severity, short_desc)

    # Process Performance issues
    perf_problems = analysis.get('performance', {}).get('problems', [])
    for problem in perf_problems:
        title = problem.get('title', '').split(' - ')[0]
        short_desc = (
            (problem.get('title', '').split(' - ')
             [1] if ' - ' in problem.get('title', '') else '')
            or problem.get('description', '').split('.')[0]
        )
        severity = 'critical' if problem.get('icon') == 'alert' else 'warning'

        add_issue(title, 'Performance', severity, short_desc)

    return issues


def extract_business_impact(raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract business impact from the business_benefits in analysis_details.
    Maps negative impacts (risks) from the data.

    Args:
        raw_data: The raw scan results data

    Returns:
        List of business impacts
    """
    impacts = []
    impact_map = {}

    # Extract business benefits/impacts from each page's analysis
    for page in raw_data['data']['results'].get('selected_pages', []):
        analysis = page.get('analysis_details', {})

        # Check each analysis section for impact messages and benefits
        for section_key in ['usability', 'seo', 'performance']:
            section = analysis.get(section_key, {})

            if section.get('impact_message') and section.get('business_benefits'):
                impact_msg = section.get('impact_message')
                benefits = section.get('business_benefits', [])

                # Create a unique key for this impact
                impact_key = impact_msg[:50]  # Use first 50 chars as key

                if impact_key not in impact_map:
                    impact_map[impact_key] = {
                        'title': impact_msg,
                        'affected_areas': [section_key.upper()],
                        'potential_benefits_if_fixed': benefits,
                        'severity': 'high' if section.get('score', 0) < 40 else 'medium'
                    }
                else:
                    # Merge affected areas
                    if section_key.upper() not in impact_map[impact_key]['affected_areas']:
                        impact_map[impact_key]['affected_areas'].append(
                            section_key.upper())

    return list(impact_map.values())


def extract_affected_elements(issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract affected HTML elements.
    Only includes elements that are actually affected.

    Args:
        issues: List of issues

    Returns:
        List of affected elements
    """
    element_map = {}

    for issue in issues:
        title = issue.get('title', '')

        if 'Page Title' in title and 'title' not in element_map:
            element_map['title'] = {'element_type': 'title', 'count': 1}
        if 'Headings' in title and 'h1-h6' not in element_map:
            element_map['h1-h6'] = {'element_type': 'h1-h6', 'count': 1}
        if 'Meta Description' in title and 'meta-description' not in element_map:
            element_map['meta-description'] = {
                'element_type': 'meta-description', 'count': 1}
        if 'Canonical' in title and 'link-canonical' not in element_map:
            element_map['link-canonical'] = {
                'element_type': 'link-canonical', 'count': 1}
        if 'Content' in title and 'page-content' not in element_map:
            element_map['page-content'] = {
                'element_type': 'page-content', 'count': 1}
        if 'Alt Text' in title and 'img-alt-text' not in element_map:
            element_map['img-alt-text'] = {
                'element_type': 'img-alt-text', 'count': 1}

    return list(element_map.values())


def generate_resources(issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generate relevant resources based on issue categories.
    Only includes resources for categories that have issues.

    Args:
        issues: List of issues

    Returns:
        List of resources
    """
    resources = []
    categories = set(issue.get('category') for issue in issues)

    if 'SEO' in categories:
        resources.append({
            'title': 'SEO Best Practices',
            'url': 'https://developers.google.com/search/docs',
            'category': 'SEO'
        })

    if 'Accessibility' in categories:
        resources.append({
            'title': 'WCAG Accessibility Guidelines',
            'url': 'https://www.w3.org/WAI/WCAG21/quickref/',
            'category': 'Accessibility'
        })

    if 'Performance' in categories:
        resources.append({
            'title': 'Web Vitals & Performance',
            'url': 'https://web.dev/vitals/',
            'category': 'Performance'
        })

    if 'Usability' in categories:
        resources.append({
            'title': 'HTML Best Practices',
            'url': 'https://developer.mozilla.org/en-US/docs/Learn/HTML/Introduction_to_HTML',
            'category': 'General'
        })

    return resources
