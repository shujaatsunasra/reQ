# FloatChat - AI-Powered Oceanographic Data Analytics Platform

<div align="center">

![FloatChat Logo](docs/images/logo.png)

**Transform natural language queries into powerful oceanographic insights**

[![TypeScript](https://img.shields.io/badge/TypeScript-5.3-blue.svg)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-teal.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14+-black.svg)](https://nextjs.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## 🌊 Overview

FloatChat is an advanced conversational AI system designed for ARGO oceanographic float data discovery, analysis, and visualization. It combines multi-modal data processing, intelligent query planning, and interactive visualizations to make ocean data accessible through natural language.

### Key Features

- **🗣️ Natural Language Interface**: Ask questions in plain English about oceanographic data
- **🧠 Intelligent Query Planning**: ML-optimized execution with deadline awareness
- **⚡ Powered by Groq**: Lightning-fast LLM inference with Llama 3.3 70B
- **🔒 Three-Stage Security**: Pattern detection → Neural analysis → LLM arbitration
- **📊 Rich Visualizations**: Trajectory maps, Hovmöller diagrams, T-S plots, and more
- **⚡ Real-Time Performance**: <2s response for 80% of queries
- **🎨 Gemini-Inspired UI**: Fluid animations, dual-mode interface (Explorer/Power)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend Layer                          │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │  React UI   │  │ Framer Motion│  │  Plotly/Leaflet/D3    │  │
│  │Explorer/Power│  │  Animations  │  │    Visualizations     │  │
│  └─────────────┘  └──────────────┘  └───────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                       API Gateway Layer                          │
│           FastAPI + Auth Middleware + Rate Limiter               │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                   Query Processing Pipeline                      │
│  ┌────────────┐  ┌─────────────┐  ┌──────────────────────────┐ │
│  │ NL2Operator│→ │Query Planner│→ │  Iterative Refinement    │ │
│  │ NER+Parsing│  │Cost Optimizer│  │  Confidence-Based        │ │
│  └────────────┘  └─────────────┘  └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                      Security Layer                              │
│  MCP Bridge: Pattern(<2ms) → Neural(55ms) → LLM(500ms)          │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                     MCP Server Layer                             │
│  ┌──────────┐ ┌──────────┐ ┌─────────┐ ┌────────┐ ┌──────────┐ │
│  │Structured│ │ Metadata │ │ Profile │ │Semantic│ │  Cache   │ │
│  │Data      │ │Processing│ │Analysis │ │ Data   │ │  Server  │ │
│  └──────────┘ └──────────┘ └─────────┘ └────────┘ └──────────┘ │
│                    ┌────────────────┐                           │
│                    │ Visualization  │                           │
│                    │    Server      │                           │
│                    └────────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                       Data Layer                                 │
│  ┌─────────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │PostgreSQL+PostGIS│  │   ChromaDB   │  │      Redis       │   │
│  │   (Supabase)    │  │    HNSW      │  │     Cache        │   │
│  └─────────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Node.js 20+
- Python 3.11+
- Docker & Docker Compose (optional - for full infrastructure)
- pnpm 8+

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/floatchat.git
cd floatchat

# Install Node.js dependencies
pnpm install

# Create Python virtual environment
python -m venv .venv

# Activate virtual environment (Windows)
.\.venv\Scripts\Activate.ps1

# Or on Unix/macOS
source .venv/bin/activate

# Install Python dependencies
pip install -r apps/api/requirements.txt

# Install spaCy language model
python -m pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.7.1/en_core_web_lg-3.7.1-py3-none-any.whl

# Copy environment configuration
cp .env.example .env
```

### Running Development Servers

```bash
# Start the FastAPI backend (in terminal 1)
pnpm dev:api

# Start the Next.js frontend (in terminal 2)
pnpm dev:web
```

Access the application:
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Optional: Start Infrastructure Services

If you have Docker installed, you can start the full infrastructure:

```bash
# Start Redis, ChromaDB, RabbitMQ via Docker Compose
pnpm docker:up

# Stop services
pnpm docker:down
```

### Configuration

1. Open [http://localhost:3000](http://localhost:3000)
2. Click "Setup" in the header to configure your Groq API key
3. Get your free API key from [console.groq.com/keys](https://console.groq.com/keys)
4. Select your preferred model (Llama 3.3 70B recommended)
5. Configure your Supabase connection in `.env`
6. Start querying oceanographic data!

## 📁 Project Structure

```
floatchat/
├── apps/
│   ├── web/                    # Next.js frontend
│   │   ├── app/               # App router pages
│   │   ├── components/        # React components
│   │   ├── hooks/             # Custom hooks
│   │   ├── lib/               # Utilities
│   │   └── store/             # Zustand state
│   └── api/                    # FastAPI backend
│       ├── core/              # Core configuration
│       ├── mcp/               # MCP servers
│       ├── nl2op/             # NL2Operator
│       ├── planner/           # Query Planner
│       ├── security/          # MCP Bridge security
│       ├── memory/            # Memory systems
│       └── routers/           # API endpoints
├── packages/
│   ├── types/                  # Shared TypeScript types
│   ├── config/                 # Shared configuration
│   └── ui/                     # Shared UI components
├── docker/                     # Docker configurations
├── k8s/                        # Kubernetes manifests
├── docs/                       # Documentation
└── specs/                      # Specifications
```

## 🔧 Development

### Running Tests

```bash
# Run all tests
pnpm test

# Run backend tests
cd apps/api && pytest

# Run frontend tests
cd apps/web && pnpm test
```

### Linting & Formatting

```bash
# Lint all code
pnpm lint

# Format code
pnpm format
```

### Building for Production

```bash
# Build all apps
pnpm build

# Build Docker images
docker-compose -f docker-compose.prod.yml build
```

## 📊 Finilized Queries

```


```

## 🛡️ Security

FloatChat implements a three-stage security pipeline:

1. **Pattern Detection (<2ms)**: Regex-based detection of SQL injection, XSS, path traversal
2. **Neural Analysis (55ms)**: E5-based embeddings with 96.01% accuracy on adversarial prompts
3. **LLM Arbitration (500ms)**: GPT-4o-mini for complex edge cases

## 📈 Performance Targets

| Metric | Target |
|--------|--------|
| Simple queries | <500ms |
| Medium complexity | <2s |
| Complex multi-modal | <5s |
| Cache hit rate | >70% |
| NL parsing accuracy | >90% |

## 📚 Documentation

- [API Documentation](docs/api.md)
- [Architecture Guide](docs/architecture.md)
- [User Guide - Explorer Mode](docs/user-guide-explorer.md)
- [User Guide - Power Mode](docs/user-guide-power.md)
- [Deployment Guide](docs/deployment.md)
- [Developer Guide](docs/developer.md)

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- ARGO Program for oceanographic float data
- Supabase for database infrastructure
- The open-source community


---

<div align="center">
Built with ❤️ for ocean science
</div>
