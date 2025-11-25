# Async Scan Feature - Celery & RabbitMQ Setup

This document explains how to run the async scanning system with Celery workers and RabbitMQ.

## 📖 General Flow

The scan feature performs comprehensive website audits through a multi-phase pipeline:

### High-Level Flow

```
User Request → Create Job → Queue Task → Background Processing → Store Results
```

### Detailed Step-by-Step

1. **User Initiates Scan** (`POST /scan/start-async`)
   - User submits URL
   - FastAPI validates input and creates `ScanJob` record in database
   - Job gets unique UUID and initial status: `queued`
   - Returns job ID immediately to user

2. **Task Orchestration** (`run_scan_pipeline`)
   - Job queued to RabbitMQ `scan.orchestration` queue
   - Celery worker picks up orchestration task
   - Sets up pipeline chain: discovery → selection → (scraping, extraction, analysis) → aggregation
   - Updates job status throughout execution

3. **Phase 1: Page Discovery** (`discover_pages`)
   - Status: `discovering` (15% progress)
   - Selenium Chrome headless browser visits the target URL
   - Crawls website to find all internal pages (max depth: 3 levels)
   - Handles dynamic content, stale elements, and JavaScript-heavy sites
   - Stores discovered URLs in `scan_pages` table
   - Updates `pages_discovered` count

4. **Phase 2: Page Selection** (`select_pages`)
   - Status: `selecting` (35% progress)
   - Sends discovered page list to Google Gemini 1.5 Flash LLM
   - AI analyzes URLs and selects most important pages for audit
   - Selection criteria: homepage, key pages, diverse content types
   - Limits selection to top N pages (default: 15) for efficiency
   - Updates `pages_selected` count and marks selected pages in database

5. **Phase 3: Page Scraping** (`scrape_page`) - *In Progress*
   - Status: `scraping` (50% progress)
   - Visits each selected page and extracts full HTML content
   - Handles authentication, cookies, and dynamic rendering
   - Stores raw HTML for analysis
   - **TODO**: Team integration pending

6. **Phase 4: Data Extraction** (`extract_data`) - *In Progress*
   - Status: `extracting` (60% progress)
   - Parses HTML to extract structured data
   - Identifies page elements: headings, images, forms, links, meta tags
   - Extracts accessibility attributes, semantic structure
   - **TODO**: Team integration pending

7. **Phase 5: Content Analysis** (`analyze_page`) - *In Progress*
   - Status: `analyzing` (70% progress)
   - Runs scan-type-specific checks (accessibility/SEO/performance)
   - Detects issues: missing alt text, broken links, slow resources
   - Generates recommendations and severity scores
   - **TODO**: Team integration pending

8. **Phase 6: Result Aggregation** (`aggregate_results`)
   - Status: `aggregating` (90% progress)
   - Collects all page-level scores and issues
   - Calculates overall site score (0-100)
   - Generates category breakdowns (accessibility, SEO, performance)
   - Updates `score_overall`, `score_breakdown` in `ScanJob`
   - Sets final status: `completed` (100% progress)

9. **User Retrieves Results** (`GET /scan/{job_id}/results`)
   - User polls status endpoint until `completed`
   - Fetches comprehensive scan report with:
     - Overall site score
     - Pages scanned with individual scores
     - Issues found with severity levels
     - Recommendations for improvement
     - Detailed metrics and charts

### Progress Tracking

The status endpoint (`GET /scan/{job_id}/status`) provides real-time updates:

| Status | Progress | Description |
|--------|----------|-------------|
| `queued` | 0% | Job created, waiting for worker |
| `discovering` | 15% | Finding pages on site |
| `selecting` | 35% | AI choosing important pages |
| `scraping` | 50% | Downloading page content |
| `analyzing` | 70% | Running audit checks |
| `aggregating` | 90% | Calculating final scores |
| `completed` | 100% | Results ready |
| `failed` | - | Error occurred (see error_message) |

### Error Handling

- **Discovery fails**: Too many pages, site blocks crawlers → Returns partial results
- **LLM fails**: Timeout, API error → Falls back to heuristic selection
- **Scraping fails**: 404, network error → Skips page, continues with others
- **Analysis fails**: Invalid HTML, parsing error → Marks page as errored
- **Any task times out**: After 1 hour, task is killed and job marked `failed`

### Data Flow

```
┌──────────┐
│  Client  │
└────┬─────┘
     │ POST /scan/start-async
     ▼
┌──────────────┐
│   FastAPI    │ Creates ScanJob (queued)
└────┬─────────┘
     │ Queue run_scan_pipeline
     ▼
┌──────────────┐
│  RabbitMQ    │ Routes to scan.orchestration
└────┬─────────┘
     │
     ▼
┌──────────────┐
│Celery Worker │ Executes pipeline chain
└────┬─────────┘
     │
     ├─→ discover_pages (Selenium) → pages_discovered
     ├─→ select_pages (Gemini AI) → pages_selected
     ├─→ scrape_page (per page) → HTML content
     ├─→ extract_data (per page) → Structured data
     ├─→ analyze_page (per page) → Issues + scores
     └─→ aggregate_results → Final score
            │
            ▼
     ┌──────────────┐
     │ PostgreSQL   │ Stores results
     └────┬─────────┘
          │
          ▼
     ┌──────────┐
     │  Client  │ GET /scan/{job_id}/results
     └──────────┘
```

---

## 🚀 Quick Start (Development)

### Prerequisites
- RabbitMQ installed and running (Windows service)
- Python virtual environment activated
- Google Gemini API key configured in `.env`

### Start All Services
Manual Start**
```powershell
# Terminal 1: Check RabbitMQ is running
Get-Service -Name RabbitMQ
# If not running: Start-Service -Name RabbitMQ

# Terminal 2: Start Celery Worker
celery -A app.platform.celery_app worker --loglevel=info --pool=solo -Q scan.discovery,scan.selection,scan.scraping,scan.extraction,scan.analysis,scan.aggregation,scan.orchestration,celery

# Terminal 3: Start FastAPI Server
uvicorn app.main:app --reload --port 8000
```

### Test the Async Endpoint

**1. Start a scan:**
```bash
curl -X POST http://localhost:8000/api/v1/scan/start-async \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "scan_type": "accessibility", "user_id": 1}'
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "job_id": "019abcca-8d1b-7763-b47a-cb7a06d71923",
    "status": "queued",
    "message": "Scan queued successfully. Poll GET /scan/{job_id}/status for progress."
  }
}
```

**2. Check progress:**
```bash
curl http://localhost:8000/api/v1/scan/{job_id}/status
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "job_id": "019abcca-8d1b-7763-b47a-cb7a06d71923",
    "status": "discovering",
    "progress_percent": 15,
    "current_step": "Finding pages on site",
    "pages_discovered": 42,
    "pages_selected": null,
    "pages_scanned": null
  }
}
```

**3. Get results (when completed):**
```bash
curl http://localhost:8000/api/v1/scan/{job_id}/results
```

### Monitoring

- **API Documentation**: http://localhost:8000/docs
- **RabbitMQ Management UI**: http://localhost:15672 (guest/guest)
- **Celery Worker Logs**: Check the terminal where worker is running

---

## 🏗️ Architecture

```
┌─────────────┐
│  FastAPI    │  POST /scan/start-async
│   Server    │  (Creates job, queues task)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  RabbitMQ   │  Message Broker
│   Queues    │  (Routes tasks to workers)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Celery    │  Background Workers
│   Workers   │  (Execute scan tasks)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ PostgreSQL  │  Store results
│  Database   │
└─────────────┘
```

## 📋 Task Pipeline

The scan is broken into phases executed by Celery workers:

1. **`run_scan_pipeline`** (Orchestrator)
   - Queue: `scan.orchestration`
   - Coordinates entire scan workflow

2. **`discover_pages`** (Phase 1)
   - Queue: `scan.discovery`
   - Finds all pages on the website using Selenium
   - Updates: `pages_discovered`

3. **`select_pages`** (Phase 2)
   - Queue: `scan.selection`
   - Uses Gemini AI to select important pages
   - Updates: `pages_selected`

4. **`scrape_page`** (Phase 3) - *Placeholder*
   - Queue: `scan.scraping`
   - Scrapes HTML from selected pages
   - **TODO**: Integrate with scraping service

5. **`extract_data`** (Phase 4) - *Placeholder*
   - Queue: `scan.extraction`
   - Extracts structured data from HTML
   - **TODO**: Integrate with extraction service

6. **`analyze_page`** (Phase 5) - *Placeholder*
   - Queue: `scan.analysis`
   - Analyzes page for issues
   - **TODO**: Integrate with analysis service

7. **`aggregate_results`** (Phase 6)
   - Queue: `scan.aggregation`
   - Calculates final scores
   - Updates: `score_overall`, `status=completed`

---

## 🚀 Production Deployment

### Option 1: Managed Services (Easiest)

Use managed RabbitMQ services like **CloudAMQP**:

```env
# .env (Production)
CELERY_BROKER_URL=amqps://user:pass@rabbit.cloudamqp.com/vhost
CELERY_RESULT_BACKEND=rpc://
```

**Deploy Celery Workers:**
- Deploy as separate containers/services
- Scale workers independently based on load
- Use process managers like systemd or supervisord

### Option 2: Self-Hosted

**1. Install RabbitMQ on Server:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install rabbitmq-server -y
sudo systemctl enable rabbitmq-server
sudo systemctl start rabbitmq-server

# Enable management UI
sudo rabbitmq-plugins enable rabbitmq_management

# Create production user
sudo rabbitmqctl add_user prod_user secure_password
sudo rabbitmqctl set_user_tags prod_user administrator
sudo rabbitmqctl set_permissions -p / prod_user ".*" ".*" ".*"
```

**2. Run Celery as Systemd Service:**

Create `/etc/systemd/system/celery-worker.service`:
```ini
[Unit]
Description=Celery Worker for Site Audit AI
After=network.target rabbitmq-server.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/var/www/site-audit-ai-be
Environment="PATH=/var/www/site-audit-ai-be/.venv/bin"
ExecStart=/var/www/site-audit-ai-be/.venv/bin/celery -A app.platform.celery_app worker \
    --loglevel=info \
    --concurrency=4 \
    -Q scan.discovery,scan.selection,scan.scraping,scan.extraction,scan.analysis,scan.aggregation,scan.orchestration,celery
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable celery-worker
sudo systemctl start celery-worker
sudo systemctl status celery-worker
```

**3. Configure Production Environment:**
```env
ENVIRONMENT=production
DEBUG=False
CELERY_BROKER_URL=amqp://prod_user:secure_password@localhost:5672//
CELERY_RESULT_BACKEND=rpc://
DATABASE_URL=postgresql+asyncpg://user:pass@db-host:5432/siteaudit
GOOGLE_GEMINI_API_KEY=your-production-key
```

### Scaling Workers

Run specialized workers for different task types:

```bash
# Worker 1: Discovery (CPU intensive)
celery -A app.platform.celery_app worker -Q scan.discovery --concurrency=2

# Worker 2: Selection & Analysis (I/O + API calls)
celery -A app.platform.celery_app worker -Q scan.selection,scan.analysis --concurrency=4

# Worker 3: Scraping (Network intensive)
celery -A app.platform.celery_app worker -Q scan.scraping --concurrency=8
```

---

## 🔧 Configuration

### Environment Variables

```env
# Message Broker
CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//

# Result Backend (optional)
CELERY_RESULT_BACKEND=rpc://  # or redis://localhost:6379/0

# Task Settings
CELERY_TASK_SERIALIZER=json
CELERY_RESULT_SERIALIZER=json
CELERY_ACCEPT_CONTENT=json
CELERY_TASK_TRACK_STARTED=True
CELERY_TASK_TIME_LIMIT=3600  # 1 hour max per task

# LLM API
GOOGLE_GEMINI_API_KEY=your-gemini-api-key
```

### Celery Queues

| Queue | Purpose | Concurrency |
|-------|---------|-------------|
| `scan.orchestration` | Task coordination | 1-2 |
| `scan.discovery` | Page discovery (Selenium) | 2-4 |
| `scan.selection` | LLM page selection | 4-8 |
| `scan.scraping` | HTML scraping | 8-16 |
| `scan.extraction` | Data extraction | 4-8 |
| `scan.analysis` | Content analysis | 4-8 |
| `scan.aggregation` | Score calculation | 2-4 |
| `celery` | Default queue | 4 |

---

## 🐛 Troubleshooting


### Tasks Not Executing
```bash
# Check worker logs for errors
# Look for task registration messages on startup

# Verify task is queued in RabbitMQ UI
# http://localhost:15672/#/queues

# Check database for job status
# Status should progress: queued → discovering → selecting → ... → completed
```

### Slow Performance
```bash
# Increase worker concurrency
celery -A app.platform.celery_app worker --concurrency=8

# Monitor with Flower
celery -A app.platform.celery_app flower
# Visit http://localhost:5555
```

---

## 🎯 Next Steps

1. ✅ Page discovery and selection are working
2. 🚧 **TODO**: Integrate scraping service @Eros4321
3. 🚧 **TODO**: Integrate extraction service  @Newkoncept
4. 🚧 **TODO**: Integrate analysis service @Toluwaa-o
5. ✅ Result aggregation is ready

Once the placeholder tasks are implemented, the full pipeline will execute end-to-end automatically!
