"""
Site management service for handling both authenticated portfolio sites and global scan cache.

This service demonstrates the unified Site model approach where:
- Auth users can manage a portfolio of sites (is_portfolio_site=True)
- All scans (auth + unauth) create/update Site records for caching
- Unauth scans create "unclaimed" sites (user_id=NULL)
- Device sessions can later "claim" sites when user registers
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.features.sites.models.site import Site, SiteStatus


class SiteService:
    """Handles site creation, caching, and portfolio management."""
    
    @staticmethod
    def get_or_create_site(
        db: Session,
        root_url: str,
        user_id: Optional[str] = None,
        add_to_portfolio: bool = False
    ) -> tuple[Site, bool]:
        """
        Get existing site or create new one.
        
        Logic:
        1. Check if site exists globally (regardless of owner)
        2. If exists and user wants to add to portfolio, link it to user
        3. If doesn't exist, create new site record
        
        Args:
            root_url: The site URL to scan
            user_id: Auth user ID (None for anonymous scans)
            add_to_portfolio: If True, mark as portfolio site for auth user
            
        Returns:
            (Site, created: bool)
        """
        # Normalize URL
        normalized_url = root_url.lower().rstrip('/')
        
        if user_id and add_to_portfolio:
            # Auth user adding to portfolio - check if they already have it
            user_portfolio_site = db.query(Site).filter(
                Site.user_id == user_id,
                Site.root_url == normalized_url
            ).first()
            
            if user_portfolio_site:
                # User already has this site in portfolio
                return user_portfolio_site, False
            else:
                # Create new portfolio entry for this user
                portfolio_site = Site(
                    user_id=user_id,
                    root_url=normalized_url,
                    is_portfolio_site=True,
                    total_scans=0,
                    status=SiteStatus.active
                )
                db.add(portfolio_site)
                db.commit()
                return portfolio_site, True
        
        else:
            # Anonymous scan OR auth scan without portfolio
            # Check if cache entry exists (user_id is NULL)
            cache_entry = db.query(Site).filter(
                Site.root_url == normalized_url,
                Site.user_id == None
            ).first()
            
            if cache_entry:
                # Use existing cache entry
                return cache_entry, False
            else:
                # Create new cache entry
                new_cache_entry = Site(
                    user_id=None,
                    root_url=normalized_url,
                    is_portfolio_site=False,
                    total_scans=0,
                    status=SiteStatus.active
                )
                db.add(new_cache_entry)
                db.commit()
                return new_cache_entry, True
    
    @staticmethod
    def check_recent_scan(
        db: Session,
        root_url: str,
        max_age_hours: int = 24
    ) -> Optional[dict]:
        """
        Check if site has been scanned recently (for cache optimization).
        
        This checks the GLOBAL site record (regardless of owner) to see if
        ANY user has scanned this site recently. If yes, we can potentially
        serve cached results instead of running a new scan.
        
        Args:
            root_url: The site URL
            max_age_hours: Consider scans older than this as stale
            
        Returns:
            Dict with site_id and last_scanned_at if recent scan exists, else None
        """
        normalized_url = root_url.lower().rstrip('/')
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        site = db.query(Site).filter(
            Site.root_url == normalized_url,
            Site.last_scanned_at >= cutoff_time
        ).first()
        
        if site:
            return {
                "site_id": site.id,
                "last_scanned_at": site.last_scanned_at,
                "total_scans": site.total_scans
            }
        
        return None
    
    @staticmethod
    def update_scan_stats(
        db: Session,
        site_id: str,
        increment_count: bool = True
    ):
        """
        Update site scan statistics after a scan completes.
        
        This updates the global site record so future scans can check
        when this site was last scanned (for cache optimization).
        """
        site = db.query(Site).filter(Site.id == site_id).first()
        if site:
            if increment_count:
                site.total_scans += 1
            site.last_scanned_at = datetime.utcnow()
            db.commit()
    
    @staticmethod
    def get_user_portfolio_sites(
        db: Session,
        user_id: str,
        status: Optional[SiteStatus] = None
    ) -> list[Site]:
        """
        Get sites in user's portfolio (for dashboard/management).
        
        Only returns sites where:
        - user_id matches
        - is_portfolio_site = True (user actively managing)
        """
        query = db.query(Site).filter(
            Site.user_id == user_id,
            Site.is_portfolio_site == True
        )
        
        if status:
            query = query.filter(Site.status == status)
        
        return query.order_by(Site.last_scanned_at.desc()).all()
    
    @staticmethod
    def claim_device_scans(
        db: Session,
        device_id: str,
        user_id: str
    ):
        """
        When a device session user registers, link their scan history to their account.
        
        This finds all scan_jobs for the device and:
        1. Links them to the new user_id
        2. Optionally adds scanned sites to user's portfolio
        """
        from app.features.scan.models.scan_job import ScanJob
        
        # Find all scans by this device
        device_scans = db.query(ScanJob).filter(
            ScanJob.device_id == device_id
        ).all()
        
        # Link scans to user
        for scan in device_scans:
            scan.user_id = user_id
            
            # Optionally add to portfolio
            if scan.site_id:
                site = db.query(Site).filter(Site.id == scan.site_id).first()
                if site and not site.user_id:
                    # Unclaimed site - claim it
                    site.user_id = user_id
                    site.is_portfolio_site = True
        
        db.commit()


# Example Usage
# =============

def example_unauth_scan(db: Session, url: str, device_id: str):
    """
    Anonymous user scans a site.
    
    Flow:
    1. Check if site was scanned recently (cache optimization)
    2. If recent, serve cached results
    3. If not, run new scan and update site record
    """
    # Check cache
    recent_scan = SiteService.check_recent_scan(db, url, max_age_hours=24)
    if recent_scan:
        print(f"Cache hit! Site last scanned {recent_scan['last_scanned_at']}")
        # Serve cached results from scan_jobs table
        # return cached_results
    
    # No cache - run new scan
    site, created = SiteService.get_or_create_site(
        db,
        root_url=url,
        user_id=None,  # Anonymous
        add_to_portfolio=False
    )
    
    # Create ScanJob linked to site
    from app.features.scan.models.scan_job import ScanJob
    scan_job = ScanJob(
        device_id=device_id,
        site_id=site.id,
        root_url=url,
        status="queued"
    )
    db.add(scan_job)
    db.commit()
    
    # ... run scan ...
    
    # Update site stats
    SiteService.update_scan_stats(db, site.id)


def example_auth_scan_with_portfolio(db: Session, url: str, user_id: str):
    """
    Authenticated user scans a site and adds it to their portfolio.
    
    Flow:
    1. Check if site exists globally
    2. Add to user's portfolio
    3. Run scan
    """
    # Get or create site AND add to portfolio
    site, created = SiteService.get_or_create_site(
        db,
        root_url=url,
        user_id=user_id,
        add_to_portfolio=True  # Mark as portfolio site
    )
    
    # Create ScanJob
    from app.features.scan.models.scan_job import ScanJob
    scan_job = ScanJob(
        user_id=user_id,
        site_id=site.id,
        root_url=url,
        status="queued"
    )
    db.add(scan_job)
    db.commit()
    
    # ... run scan ...
    
    # Update site stats
    SiteService.update_scan_stats(db, site.id)


def example_get_user_dashboard(db: Session, user_id: str):
    """
    Get user's portfolio sites for dashboard.
    """
    portfolio_sites = SiteService.get_user_portfolio_sites(
        db,
        user_id=user_id,
        status=SiteStatus.active
    )
    
    return [
        {
            "id": site.id,
            "url": site.root_url,
            "name": site.display_name or site.root_url,
            "total_scans": site.total_scans,
            "last_scanned": site.last_scanned_at
        }
        for site in portfolio_sites
    ]
