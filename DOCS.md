# FireReach – Technical Documentation

## Overview

FireReach is a production-ready autonomous outreach system. It takes an Ideal Customer Profile (ICP), a target company, and a recipient email — and runs a fully agentic pipeline that:

1. **Harvests live company signals** via Tavily and Apify
2. **Analyzes the account** with a grounded LLM brief
3. **Generates a hyper-personalized outreach email** referencing real signals
4. **Sends the email automatically** via SendGrid

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     React Frontend                       │
│   InputForm → StatusTimeline → SignalsPanel → EmailPanel │
└────────────────────┬────────────────────────────────────┘
                     │ POST /api/v1/run-agent
┌────────────────────▼────────────────────────────────────┐
│                  FastAPI Backend                          │
│                                                          │
│  routes/agent_routes.py                                  │
│       │                                                  │
│  services/agent_service.py  ←→  services/session_store  │
│       │                                                  │
│  agent/graph.py  (LangGraph)                             │
│   ┌───┴───────────────────────────────────────────┐      │
│   │  node_input_validation                        │      │
│   │       ↓                                       │      │
│   │  node_signal_harvesting ← tool_signal_harvester│     │
│   │       ↓                                       │      │
│   │  node_research_analysis ← tool_research_analyst│     │
│   │       ↓                                       │      │
│   │  node_email_generation_and_send               │      │
│   │         └← tool_outreach_automated_sender     │      │
│   └───────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────┘
```

---

## Agent Flow

### Node 1: Input Validation
- Validates email format, company name, ICP length
- Logs validation failures with field names
- Routes to `FAILED` on any error

### Node 2: Signal Harvesting
- Calls `tool_signal_harvester`
- Fires 4 Tavily search queries about the company
- Runs Apify Google Search Scraper for structured results
- Passes all raw snippets to a deterministic Groq LLM call (temp=0.0)
- LLM extracts only grounded signals — explicitly instructed not to invent
- Returns `SignalHarvesterOutput` with typed `GrowthSignal` objects

### Node 3: Research Analysis
- Calls `tool_research_analyst`
- Requires at least 1 signal (guardrail — will not hallucinate a brief)
- Calls Groq (llama-3.3-70b-versatile, temp=0.2)
- Produces a 2-paragraph account brief + pain points + urgency reason

### Node 4: Email Generation + Send
- Calls `tool_outreach_automated_sender`
- Generates email via Groq (temp=0.4 for natural variation)
- Runs signal reference guardrail: verifies ≥2 signals mentioned in email body
- If guardrail fails, regenerates once with stricter prompt
- Sends via SendGrid, logs message ID

---

## Tool Schemas

### tool_signal_harvester
```python
Input:  SignalHarvesterInput(company: str, icp: str)
Output: SignalHarvesterOutput(
    company: str,
    signals: list[GrowthSignal],
    raw_snippets: list[str],
    error: Optional[str]
)

GrowthSignal(
    signal_type:  str   # funding | hiring | leadership | tech_stack | social | growth
    description:  str
    source:       str   # URL or tool name
    grounded:     bool  # always True from this tool
)
```

### tool_research_analyst
```python
Input:  ResearchAnalystInput(company: str, icp: str, signals: list[GrowthSignal])
Output: ResearchAnalystOutput(
    account_brief:  str
    pain_points:    list[str]
    urgency_reason: str
    error:          Optional[str]
)
```

### tool_outreach_automated_sender
```python
Input:  OutreachSenderInput(
    company: str,
    recipient_email: str,
    icp: str,
    account_brief: str,
    signals: list[GrowthSignal]
)
Output: OutreachSenderOutput(
    subject:    str
    body:       str
    sent:       bool
    message_id: Optional[str]
    error:      Optional[str]
)
```

---

## State Model

```python
class AgentState(BaseModel):
    session_id:     str
    icp:            str          # Ideal Customer Profile
    company:        str          # Target company name
    email:          str          # Recipient email

    signals:        dict         # Serialized signals from harvester
    research_brief: str          # Account brief from research analyst
    email_subject:  str          # Generated email subject
    email_body:     str          # Generated email body

    status:         AgentStatus  # initialized|validating|harvesting|researching|generating|sending|complete|failed
    error:          Optional[str]
    chat_history:   list[dict]   # {"role": str, "content": str}
```

---

## How Signals Are Grounded

FireReach uses a **three-layer grounding strategy**:

1. **Source traceability**: Every signal carries a `source` field (URL or tool name). Signals are only accepted if they came directly from Tavily or Apify output.

2. **LLM extraction guardrail**: The signal extraction prompt explicitly instructs the model: *"DO NOT invent any signal not present in the snippets"*. Temperature is set to 0.0 for determinism.

3. **Email reference check**: Before sending, a second LLM call (temp=0.0) verifies that the generated email body explicitly references ≥2 of the harvested signals. If it doesn't, the email is regenerated.

---

## Logging Strategy

Each session produces one JSONL log file at `logs/{session_id}.jsonl`.

Every line is a structured JSON entry:
```json
{
  "timestamp": "2025-01-01T12:00:00Z",
  "level":     "INFO",
  "session_id": "abc-123",
  "event":     "tool_call",
  "tool":      "tool_signal_harvester",
  "inputs":    {...}
}
```

Logged events:
- `tool_call` — tool name + inputs
- `tool_result` — tool name + outputs + success flag
- `llm_output` — node name + truncated output
- `validation_failure` — field + reason
- `email_sent` — recipient + message_id + success
- `node_started` / `node_completed` — graph execution tracking
- `error` events — all exceptions

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | `/api/v1/run-agent` | Run full pipeline |
| GET    | `/api/v1/session/{id}` | Get session state |
| GET    | `/api/v1/logs/{id}` | Get session logs |
| GET    | `/api/v1/health` | Health check |
| GET    | `/docs` | Swagger UI |

---

## Environment Variables

```env
GROQ_API_KEY=           # Groq API key (required)
SENDGRID_API_KEY=       # SendGrid API key for email sending
SENDGRID_FROM_EMAIL=    # From address (must be verified in SendGrid)
SENDGRID_FROM_NAME=     # Display name
TAVILY_API_KEY=         # Tavily API key for web search
APIFY_TOKEN=            # Apify API token for structured scraping
LOG_DIR=logs            # Directory for session log files
ENV=development         # Environment name
```

---

## Setup Instructions

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:3000
```

---

## Test Scenario

**ICP**: "We sell high-end cybersecurity training to Series B startups"
**Company**: "Wiz" (or any recently funded startup)
**Email**: `cto@target.com`

Expected behavior:
1. Tavily searches fire: funding, hiring, leadership, tech news queries
2. Signals like "raised Series B", "hiring 50 engineers", "expanded to EU" are extracted
3. Brief explains: why Wiz matters, their likely security gaps from fast growth
4. Email opens with a specific growth signal, connects it to security risk, mentions the training offering
5. Email is sent (or logged if SendGrid not configured)

---

## How Each API Is Used

| Service  | Usage |
|----------|-------|
| **Groq** | LLM inference for signal extraction (temp=0.0), account briefs (temp=0.2), and email generation (temp=0.4). Model: llama-3.3-70b-versatile |
| **Tavily** | Web search — fires 4 targeted queries per company. Returns structured results with URLs and content snippets |
| **Apify** | Google Search Scraper actor — fires one broad query, returns up to 10 organic results with snippets and URLs |
| **SendGrid** | Transactional email delivery. Sends both plain text and HTML versions. Returns message ID for logging |

---

## Project Structure

```
firereach/
├── backend/
│   ├── main.py               # FastAPI app entry point
│   ├── requirements.txt
│   ├── .env.example
│   ├── agent/
│   │   └── graph.py          # LangGraph workflow
│   ├── tools/
│   │   ├── signal_harvester.py
│   │   ├── research_analyst.py
│   │   └── outreach_sender.py
│   ├── services/
│   │   ├── agent_service.py  # Orchestration layer
│   │   └── session_store.py  # In-memory session store
│   ├── routes/
│   │   └── agent_routes.py   # FastAPI endpoints
│   ├── schemas/
│   │   └── models.py         # All Pydantic models
│   ├── prompts/
│   │   └── templates.py      # All prompt templates
│   ├── utils/
│   │   ├── config.py         # Settings (pydantic-settings)
│   │   └── logger.py         # Structured JSONL logger
│   └── logs/                 # Per-session log files
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── main.jsx
    │   ├── components/
    │   │   ├── InputForm.jsx
    │   │   ├── StatusTimeline.jsx
    │   │   ├── SignalsPanel.jsx
    │   │   ├── OutputPanels.jsx
    │   │   ├── ChatHistory.jsx
    │   │   └── LoadingSkeleton.jsx
    │   ├── hooks/
    │   │   └── useFireReach.js
    │   ├── utils/
    │   │   └── api.js
    │   └── styles/
    │       └── globals.css
    ├── index.html
    ├── vite.config.js
    ├── tailwind.config.js
    └── package.json
```
