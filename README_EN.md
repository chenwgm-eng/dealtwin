# DealTwin — B2B Sales Digital Twin Engine

> AI-powered opportunity management built on SVS + Challenger Sale methodologies

DealTwin is an intelligent B2B sales opportunity management tool that combines the **SVS (Solution Value Selling)** process framework with **Challenger Sales** engagement skills. Powered by LLM-driven digital twin simulations, it helps salespeople make more precise decisions across the full opportunity lifecycle — from lead to close.

## Two Editions

| | Community Edition (this repo) | Business Edition |
|---|---|---|
| Target user | Individual salespeople | Sales teams / enterprises |
| AI capabilities | **Baseline AI** (core features) | **Full AI** (complete + advanced) |
| Customer relationship management | ❌ | ✅ |
| Authentication & RBAC | ❌ | ✅ |
| Team data isolation | ❌ | ✅ |
| Database | SQLite | SQLite / PostgreSQL / MySQL |
| License | AGPL-3.0 (open source) | Private commercial license |

---

## Community Edition Capabilities

The community edition provides full opportunity lifecycle management and **baseline AI** assistance for individual salespeople.

### Opportunity Management

- **Full opportunity lifecycle**: 5-stage SVS pipeline (Suspect → Identity → Define → Confirm → Closed) + OM10–OM70 milestone decisions
- **Stakeholder mapping**: Visualize relationship networks, decision chains, and influence paths
- **Stage deliverable tracking**: Per-stage deliverable checklists and completion tracking
- **Personal dashboard**: Opportunity overview and attention items

### Baseline AI Capabilities

- **Blind spot scanning**: Automatically identify gaps and risks in your opportunity
- **Action recommendations**: Generate next-best-action suggestions based on opportunity state
- **Challenger messaging**: 7-step commercial teaching script generation + social style tailoring
- **Meeting plans**: Structured visit preparation
- **Feedback parsing**: Automatically turn unstructured visit notes into structured data updates
- **Dashboard insights**: AI-generated sales insight summaries

---

## Business Edition Capabilities

The business edition extends the community edition with **full AI** and **advanced AI** capabilities.

### Full AI (enhanced baseline)

- **Deep blind spot scanning**: Multi-dimensional cross-analysis (organization / competition / timing / budget) to surface hidden risks
- **Intelligent action orchestration**: Personalized action strategies based on stakeholder social styles and buying roles
- **Complete Challenger**: 7-step scripts + Tailoring + Powerful Ask generation + verification factor analysis
- **Fermentation simulation**: LLM-driven multi-round closed-door sandbox that simulates internal stakeholder reactions and politics
- **Intelligent meeting plans**: Comprehensive plans combining stakeholder agendas + historical interactions + competitive posture

### Advanced AI (business-only)

- **Customer intelligence profiles**: Auto-fetch business registrations + industry dynamics + organizational structure, then generate panoramic customer portraits via AI
- **Organizational AI analysis**: Automatically parse customer reporting trees to identify key decision nodes and influence paths
- **Automatic learning pattern extraction**: Distill success and failure patterns from won/lost records to build a team sales knowledge base
- **Cross-opportunity strategy recommendations**: Recommend optimal strategies for new opportunities based on historical data and the learning pattern library
- **Team collaboration AI**: Analyze team opportunity distribution and progress to generate resource allocation and collaboration suggestions
- **Competitive intelligence AI**: Automatically monitor competitor dynamics and correlate them to relevant opportunities for risk alerts
- **Opportunity health AI scoring**: Multi-dimensional AI assessment of win probability and risk level

### Enterprise Features

- **Customer relationship management**: Hierarchical customer tree management, contacts, organizational graphs, automatic business registration fetching
- **JWT authentication**: Login / logout + token management
- **3-role RBAC**: admin (full access) / manager (team) / sales (individual)
- **Data isolation**: Automatic visibility filtering by role (admin: all / manager: team / sales: individual)
- **User management**: Create / disable users, role assignment, team membership

---

## Tech Stack

- **Backend**: Flask + SQLAlchemy + APScheduler + OpenAI SDK
- **Frontend**: Vue 3 + Vite + Vue Router + Vue I18n + AntV G6
- **Database**: SQLite (default) / PostgreSQL / MySQL (business edition)
- **LLM**: Any model compatible with the OpenAI API format

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- uv (Python package manager)

### Installation

```bash
# Clone the repository
git clone https://github.com/chenwgm-eng/dealtwin.git
cd dealtwin

# Install backend dependencies
cd backend
uv sync
cd ..

# Install frontend dependencies
cd frontend
npm install
cd ..

# Configure environment variables
cp .env.example .env
# Edit .env and fill in your LLM_API_KEY
```

### Running

```bash
# From the project root
npm run dev
```

This starts both the backend (Flask :5001) and the frontend (Vite :3000) simultaneously.

Open http://localhost:3000 in your browser to start using DealTwin.

### Production Build

```bash
cd frontend
npm run build
# Output is in frontend/dist/
```

---

## Project Structure

```
dealtwin/
├── backend/
│   ├── app/
│   │   ├── api/sales_twin/    # API routes (split by business domain)
│   │   ├── models/            # Data models
│   │   ├── services/          # Business services (LLM, simulation, detection)
│   │   ├── jobs/              # Background scheduled tasks
│   │   └── utils/             # Utilities
│   ├── scripts/               # Database migration scripts
│   ├── tests/                 # Tests
│   └── run.py                 # Entry point
├── frontend/
│   └── src/
│       ├── api/               # API client
│       ├── components/        # Vue components
│       ├── composables/       # Composable functions
│       ├── views/             # Page views
│       └── i18n/              # Internationalization
├── locales/                   # i18n language packs
├── docs/                      # Documentation
└── .env.example               # Environment variable template
```

---

## Extension Mechanism

DealTwin uses an **open-core** architecture. Community and commercial editions share the same codebase, separated via the `@edition` registry:

- The community edition ships `@edition` stubs (`set_edition_provider` / `has_customer_module` / `has_auth`)
- The business edition injects `BusinessEditionProvider` at startup to enable customer management, authentication, RBAC, and other extensions
- Data isolation is implemented via a `scope provider` (the community edition provider is `None`, so behavior is unchanged)

---

## License

The community edition is released under the [GNU AGPL-3.0](LICENSE) open-source license.

The business edition (DealTwin Business) is distributed under a private commercial license and is not open source.

---

## Acknowledgments

DealTwin is designed on top of the following sales methodologies:

- **SVS (Solution Value Selling)**: provides the opportunity progression framework
- **Challenger Sales**: provides the customer engagement skill framework

---

## Contact

Email: chenwgm@126.com
