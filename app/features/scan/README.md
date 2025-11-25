# Async Scan Feature - Celery & RabbitMQ Setup

This document explains how to run the async scanning system with Celery workers and RabbitMQ.

## 🚀 Quick Start (Development)

### Prerequisites
- RabbitMQ installed and running (Windows service)
- Python virtual environment activated
- Google Gemini API key configured in `.env`

### Start All Services

**Option 1: Quick Start Script (Recommended)**
```powershell
.\scripts\quickstart.ps1
# Select option 7 (Run ALL)
```

**Option 2: Manual Start**
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
