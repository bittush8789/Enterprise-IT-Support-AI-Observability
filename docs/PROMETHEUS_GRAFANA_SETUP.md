# 📊 Prometheus & Grafana Observability Setup Guide

This document provides a comprehensive guide for setting up **Prometheus** (time-series metrics collection) and **Grafana** (metrics visualization dashboards) using **Docker** and **Docker Compose** to monitor the **Enterprise IT Support Agentic RAG Copilot**.

---

## 🎯 Architecture Overview

```text
┌───────────────────────────────────────┐
│     FastAPI Application               │
│     (Port 8080 - /metrics)            │
└──────────────────┬────────────────────┘
                   │ Scrapes every 5s
                   ▼
┌───────────────────────────────────────┐
│     Prometheus Time-Series DB         │
│     (Port 9090 - Container)           │
└──────────────────┬────────────────────┘
                   │ Datasource Query
                   ▼
┌───────────────────────────────────────┐
│     Grafana Dashboards                │
│     (Port 3000 - Container)           │
└───────────────────────────────────────┘
```

* **Langfuse** handles LLM-level observability (tokens, prompt costs, node decision steps).
* **Prometheus & Grafana** handle system-level APM (HTTP request rates, latency percentiles p95/p99, error rates, server resources).

---

## 📁 Directory Structure

The setup files are located in the `monitoring/` directory:

```text
Enterprise-IT-Support-Agentic-RAG-Evaluation-Harness/
├── monitoring/
│   ├── docker-compose.yml       # Container orchestration for Prometheus & Grafana
│   └── prometheus.yml          # Scrape target configuration
└── docs/
    └── PROMETHEUS_GRAFANA_SETUP.md # This guide
```

---

## ⚙️ Configuration Files

### 1. `monitoring/prometheus.yml`

```yaml
global:
  scrape_interval: 5s       # Metrics collection interval
  evaluation_interval: 5s

scrape_configs:
  - job_name: 'it-support-fastapi'
    metrics_path: '/metrics'
    static_configs:
      # Use host.docker.internal to scrape FastAPI running on the host OS
      - targets: ['host.docker.internal:8080']
        labels:
          environment: 'development'
          service: 'it-support-copilot'
```

### 2. `monitoring/docker-compose.yml`

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:v2.51.0
    container_name: it_support_prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
      - '--web.enable-lifecycle'
    extra_hosts:
      - "host.docker.internal:host-gateway"

  grafana:
    image: grafana/grafana:10.4.1
    container_name: it_support_grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
    depends_on:
      - prometheus

volumes:
  prometheus_data:
  grafana_data:
```

---

## 🔌 FastAPI Code Integration (Optional Activation)

When you are ready to expose `/metrics` from the FastAPI application, follow these steps:

### Step 1: Install Dependency
```bash
pip install prometheus-fastapi-instrumentator==7.0.2
```

### Step 2: Instrument FastAPI in `app/main.py`
```python
from prometheus_fastapi_instrumentator import Instrumentator

# Directly after creating the FastAPI app:
app = FastAPI(title=settings.app_name, version="1.0.0")

# Expose Prometheus /metrics endpoint
Instrumentator().instrument(app).expose(app, endpoint="/metrics")
```

Once added, visiting `http://localhost:8080/metrics` will output OpenMetrics-formatted metrics.

---

## 🚀 Execution & Verification

### 1. Start the Containers
Run Docker Compose in the `monitoring/` directory:
```powershell
cd monitoring
docker compose up -d
```

Check running containers:
```powershell
docker compose ps
```

### 2. Verify Prometheus
* Open `http://localhost:9090` in your browser.
* Navigate to **Status ➔ Targets**.
* Ensure the `it-support-fastapi` target is in state **UP** (Green).

### 3. Setup Grafana Dashboard
1. Open `http://localhost:3000`.
2. Login with:
   * **Username:** `admin`
   * **Password:** `admin` (change on first login if prompted).
3. **Add Data Source:**
   * Go to **Connections ➔ Data Sources ➔ Add data source**.
   * Choose **Prometheus**.
   * Set Prometheus server URL to: `http://prometheus:9090`
   * Click **Save & Test**.
4. **Import Community FastAPI Dashboard:**
   * Go to **Dashboards ➔ New ➔ Import**.
   * Enter Dashboard ID: `16110` (or `14264`).
   * Click **Load**, select your Prometheus data source, and click **Import**.

---

## 📊 Key KPIs Monitored

| Metric | Prometheus PromQL Query | Description |
|---|---|---|
| **Request Rate (RPS)** | `rate(http_requests_total[1m])` | Total inbound requests per second |
| **P95 Latency** | `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))` | 95th percentile API response time |
| **Error Rate (5xx)** | `sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100` | Percentage of failed 5xx server errors |
| **Chat Endpoint Throughput** | `sum(rate(http_requests_total{handler="/api/chat"}[1m]))` | Real-time agent query volume |

---

## 🛑 Stopping & Teardown

To stop the monitoring stack:
```powershell
cd monitoring
docker compose down
```

To stop and remove all persisted metric volumes:
```powershell
docker compose down -v
```

