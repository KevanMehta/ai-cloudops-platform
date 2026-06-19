# AI CloudOps Platform

**Monitor cloud costs, detect anomalies, and get AI-powered operational recommendations — all in one dashboard.**

A production-style full-stack application that helps engineering teams monitor AWS cloud spend, detect billing anomalies, analyze Terraform infrastructure, monitor Kubernetes workloads, and generate actionable optimization recommendations.

---

## Features

- **Dashboard** — Monthly spend, projections, anomaly counts, cost trends, service breakdown, top recommendations
- **Cost Anomaly Detection** — Statistical spike detection with severity classification and explanations
- **AI CloudOps Agent** — LangGraph-style 5-step workflow with optional OpenAI integration and local rule-based fallback
- **Terraform Analyzer** — Parses IaC for overprovisioning, public storage, missing tags, and missing autoscaling
- **Kubernetes Monitor** — Pod health, CPU/memory usage, restart counts, and fix recommendations
- **Recommendations Engine** — Actionable items with severity, savings estimates, and step-by-step actions
- **Observability** — Prometheus `/metrics` endpoint and structured JSON logging
- **Demo Data** — 90 days of AWS billing data, 7 intentional anomalies, 8 K8s workloads, 3 Terraform samples

---

## Architecture

```mermaid
flowchart TB
    subgraph Client
        FE[React + Vite Frontend<br/>:3000]
    end

    subgraph Backend
        API[FastAPI API<br/>:8000]
        AGENT[LangGraph-style Agent]
        ANOM[Anomaly Detection]
        REC[Recommendations Engine]
        TF[Terraform Analyzer]
        K8S[K8s Monitor]
    end

    subgraph Data
        PG[(PostgreSQL)]
        RD[(Redis Cache)]
    end

    subgraph Optional
        OAI[OpenAI API]
    end

    FE -->|REST| API
    API --> AGENT
    API --> ANOM
    API --> REC
    API --> TF
    API --> K8S
    AGENT --> ANOM
    AGENT --> REC
    AGENT --> TF
    AGENT --> K8S
    AGENT -.->|optional| OAI
    API --> PG
    API --> RD
    ANOM --> PG
    REC --> PG
    TF --> PG
    K8S --> PG
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Recharts |
| Backend | FastAPI, Python 3.12, Pydantic, SQLAlchemy |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| AI | LangGraph-style workflow, optional OpenAI, rule-based fallback |
| Infra | Docker, Docker Compose |
| Observability | Prometheus metrics, structured JSON logs |
| Testing | Pytest (backend), Vitest (frontend) |
| CI/CD | GitHub Actions |

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- (Optional) OpenAI API key for richer agent summaries

### Run with one command

```bash
git clone <repo-url>
cd ai-cloudops-platform
cp .env.example .env
docker compose up --build
```

After startup (typically 60–90 seconds):

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |
| Prometheus Metrics | http://localhost:8000/metrics |

Demo data is seeded automatically on first startup.

### Optional: Enable OpenAI

Add your key to `.env`:

```env
OPENAI_API_KEY=sk-your-key-here
```

Restart the backend container. The agent will use GPT-4o-mini for executive summaries; without a key, a deterministic rule-based summary is used.

---

## Screenshots

Capture screenshots after starting the app:

1. **Dashboard** — `http://localhost:3000/dashboard`
2. **Anomalies** — `http://localhost:3000/anomalies`
3. **AI Agent Report** — Run agent at `http://localhost:3000/agent`
4. **Terraform Analyzer** — `http://localhost:3000/terraform`
5. **Kubernetes Health** — `http://localhost:3000/kubernetes`

Save screenshots to `docs/screenshots/` for your portfolio.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check (DB + Redis status) |
| GET | `/metrics` | Prometheus metrics |
| GET | `/api/dashboard` | Dashboard summary data |
| GET | `/api/costs?days=90` | Cloud billing records |
| GET | `/api/anomalies` | Detected cost anomalies |
| GET | `/api/recommendations` | Optimization recommendations |
| GET | `/api/kubernetes` | Kubernetes workload health |
| POST | `/api/agent/run` | Run AI CloudOps agent workflow |
| POST | `/api/terraform/analyze` | Analyze Terraform sample files |

---

## Agent Workflow

The AI CloudOps Agent executes a 5-step LangGraph-style pipeline:

1. **Analyze cost data** — Aggregate monthly spend, projections, top services
2. **Detect anomalies** — Run statistical anomaly detection on billing data
3. **Inspect infrastructure** — Analyze Terraform samples and Kubernetes workloads
4. **Generate recommendations** — Produce actionable optimization items
5. **Executive summary** — OpenAI-enriched or rule-based final report

```mermaid
flowchart LR
    A[Analyze Costs] --> B[Detect Anomalies]
    B --> C[Inspect Infra]
    C --> D[Generate Recs]
    D --> E[Executive Summary]
```

---

## Sample Recommendations

| Title | Severity | Est. Savings |
|-------|----------|--------------|
| Reduce overprovisioned EC2 instances | High | ~$6,900/mo |
| Add autoscaling to web tier | Medium | $1,200/mo |
| Restrict public S3 bucket access | High | — |
| Investigate EC2 cost spike | High | Variable |
| Move idle Kubernetes workloads | Medium | ~$150/workload |
| Add budget alerts | Medium | $800/mo |

---

## Project Structure

```
ai-cloudops-platform/
├── docker-compose.yml
├── .env.example
├── README.md
├── .github/workflows/ci.yml
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── agent/workflow.py
│   │   ├── routers/api.py
│   │   └── seed/
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── api/
│   │   └── test/
│   ├── Dockerfile
│   └── package.json
└── infra-samples/
    ├── ec2.tf
    ├── s3.tf
    └── eks.tf
```

---

## Testing

### Backend

```bash
cd backend
pip install -r requirements.txt
pytest -v
```

### Frontend

```bash
cd frontend
npm install
npm test -- --run
```

### CI

GitHub Actions runs both test suites on push/PR to `main`.

---

## Local Development (without Docker)

**Backend:**

```bash
cd backend
pip install -r requirements.txt
export DATABASE_URL=postgresql://cloudops:cloudops_secret@localhost:5432/cloudops
export REDIS_URL=redis://localhost:6379/0
python -m app.seed.init_db
uvicorn app.main:app --reload --port 8000
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

---

## Future Improvements

- Real AWS Cost Explorer and CloudWatch integration via IAM roles
- Multi-cloud support (GCP, Azure)
- Slack/PagerDuty alert notifications
- Historical agent run comparison and trend analysis
- RBAC and SSO authentication
- Kubernetes live metrics via Prometheus adapter
- Terraform plan diff analysis in CI/CD pipelines

---

## Resume Bullet Points

- Built a full-stack **AI CloudOps Platform** with React, FastAPI, PostgreSQL, and Redis serving 7 dashboard views and 9 REST endpoints
- Implemented **statistical cost anomaly detection** across 90 days of multi-service AWS billing data with severity classification
- Designed a **LangGraph-style agent workflow** with optional OpenAI integration and deterministic local fallback
- Created **Terraform IaC analyzer** detecting overprovisioning, public storage, missing tags, and autoscaling gaps
- Containerized with **Docker Compose** for one-command local deployment with automatic database seeding and CI/CD via GitHub Actions

---

## License

MIT
