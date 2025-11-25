"""
Scan Schemas

Request and response models for the scan API endpoints.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, HttpUrl


# ============================================================================
# Main Orchestration Schemas
# ============================================================================

class ScanStartRequest(BaseModel):
    """Request to start a complete scan."""
    url: HttpUrl
    top_n: int = 15
    user_id: Optional[str] = None  # For authenticated users
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com",
                "top_n": 15
            }
        }


class ScanStartResponse(BaseModel):
    """Response after starting a scan."""
    job_id: str
    status: str
    message: str


class ScanStatusResponse(BaseModel):
    """Response for scan status check."""
    job_id: str
    status: str
    current_phase: str
    progress: Dict[str, str]


class ScanResultsResponse(BaseModel):
    """Response with final scan results."""
    job_id: str
    status: str
    results: Dict[str, Any]


# ============================================================================
# Phase 1: Discovery Schemas
# ============================================================================

class DiscoveryRequest(BaseModel):
    """Request for page discovery phase."""
    url: HttpUrl
    job_id: Optional[str] = None  # Links to ScanJob if part of workflow
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com",
                "job_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class DiscoveryResponse(BaseModel):
    """Response from page discovery phase."""
    pages: List[str]
    count: int
    job_id: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "pages": [
                    "https://example.com",
                    "https://example.com/about",
                    "https://example.com/contact"
                ],
                "count": 3,
                "job_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


# ============================================================================
# Phase 2: Selection Schemas
# ============================================================================

class SelectionRequest(BaseModel):
    """Request for page selection phase."""
    pages: List[str]
    top_n: int = 15
    job_id: Optional[str] = None
    referer: Optional[str] = None
    site_title: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "pages": ["https://example.com", "https://example.com/about"],
                "top_n": 15,
                "job_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class SelectionResponse(BaseModel):
    """Response from page selection phase."""
    important_pages: List[str]
    count: int
    job_id: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "important_pages": ["https://example.com", "https://example.com/about"],
                "count": 2,
                "job_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


# ============================================================================
# Phase 3: Scraping Schemas
# ============================================================================

class ScrapingRequest(BaseModel):
    """Request for page scraping phase."""
    pages: List[str]
    job_id: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "pages": ["https://example.com"],
                "job_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class ScrapingResponse(BaseModel):
    """Response from page scraping phase."""
    scraped_pages: List[Dict[str, Any]]
    count: int
    job_id: Optional[str] = None
    message: Optional[str] = None


# ============================================================================
# Phase 4: Analysis Schemas
# ============================================================================

class AnalysisRequest(BaseModel):
    """Request for page analysis phase."""
    page_ids: List[str]  # ScanPage IDs to analyze
    job_id: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "page_ids": ["page-id-1", "page-id-2"],
                "job_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class AnalysisResponse(BaseModel):
    """Response from page analysis phase."""
    issues_found: int
    pages_analyzed: int
    job_id: Optional[str] = None
    message: Optional[str] = None


# ============================================================================
# Page Management Schemas
# ============================================================================

class PageInfo(BaseModel):
    """Information about a discovered/selected page."""
    id: str
    page_url: str
    is_selected_by_llm: bool
    is_manually_selected: bool
    is_manually_deselected: bool
    is_selected: bool  # Computed final selection status
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "page-id-123",
                "page_url": "https://example.com/about",
                "is_selected_by_llm": True,
                "is_manually_selected": False,
                "is_manually_deselected": False,
                "is_selected": True
            }
        }


class GetPagesRequest(BaseModel):
    """Request to get all discovered pages for a job."""
    job_id: str
    filter: Optional[str] = None  # 'all', 'selected', 'not_selected', 'llm_selected'


class GetPagesResponse(BaseModel):
    """Response with all pages for a job."""
    job_id: str
    pages: List[PageInfo]
    total_discovered: int
    total_selected: int
    total_llm_selected: int
    total_manually_added: int


class TogglePageSelectionRequest(BaseModel):
    """Request to manually select/deselect a page."""
    page_id: str
    action: str  # 'select' or 'deselect'
    
    class Config:
        json_schema_extra = {
            "example": {
                "page_id": "page-id-123",
                "action": "select"
            }
        }


class TogglePageSelectionResponse(BaseModel):
    """Response after toggling page selection."""
    page_id: str
    page_url: str
    is_selected: bool
    message: str
