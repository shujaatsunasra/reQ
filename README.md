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
OCEANOGRAPHY PLATFORM - 5 BEST QUERY VARIATIONS
================================================

VARIATION 1: SIMPLE & DIRECT QUERIES
-------------------------------------
Purpose: Test basic retrieval and simple parameter requests
Expected: Fast, straightforward responses with single data type

1. "Show me temperature profiles in the Arabian Sea from last month"
2. "What's the current salinity in the North Atlantic?"
3. "Display all active floats near 10°N 50°E"
4. "Get surface temperature in the Pacific for today"
5. "Show me oxygen levels at 500m depth in the Southern Ocean"


VARIATION 2: COMPLEX MULTI-PARAMETER QUERIES
---------------------------------------------
Purpose: Test system's ability to handle multiple constraints and correlations
Expected: Integration of multiple data sources, complex filtering

1. "Find all floats near the equator with salinity anomalies above 36 PSU and temperature exceeding 28°C in the last 3 months"
2. "Compare temperature gradients between Indian Ocean and Pacific at 100m, 500m, and 1000m depths over the last year"
3. "Show me the trajectory of float 1900975 over the last year with temperature and salinity profiles at each location"
4. "Display areas where SST is above 27°C, mixed layer depth is below 50m, and chlorophyll concentration exceeds 0.5 mg/m³"
5. "Get correlation between sea surface height anomalies and subsurface temperature in mesoscale eddies in the Kuroshio Extension region"


VARIATION 3: TEMPORAL ANALYSIS QUERIES
---------------------------------------
Purpose: Test time-series handling, trend analysis, and historical comparisons
Expected: Temporal data processing, statistical analysis

1. "Show me temperature trends in the Mediterranean over the past 10 years at monthly intervals"
2. "Compare salinity in the Bay of Bengal during monsoon season vs dry season for 2020-2025"
3. "Display seasonal variations in mixed layer depth in the North Atlantic from 2015 to present"
4. "Track how float 2901345 moved through different water masses over its entire deployment period"
5. "Show me temperature anomalies during the 2023-2024 El Niño event compared to the 1997-1998 event"


VARIATION 4: SPATIAL COMPARISON QUERIES
----------------------------------------
Purpose: Test geographic analysis, regional comparisons, cross-basin studies
Expected: Spatial data processing, comparative visualization

1. "Compare thermocline depth between western Pacific warm pool and eastern Pacific cold tongue"
2. "Show me salinity differences along a transect from 60°N to 60°S at 30°W in the Atlantic"
3. "Display oxygen minimum zone characteristics in the Arabian Sea vs the Eastern Tropical Pacific"
4. "Compare upwelling intensity off Peru vs off Namibia during austral summer"
5. "Show me how mixed layer depth varies from equator to poles in all three major ocean basins"


VARIATION 5: ANOMALY & THRESHOLD DETECTION QUERIES
---------------------------------------------------
Purpose: Test filtering, anomaly detection, and conditional logic
Expected: Smart filtering, outlier identification, alert capabilities

1. "Find all floats reporting temperature anomalies greater than 3°C from climatology in the last month"
2. "Show me locations where salinity dropped below 30 PSU within 24 hours"
3. "Display all regions experiencing marine heatwaves (SST > 90th percentile for 5+ consecutive days)"
4. "Find floats with sensor malfunctions: pressure readings >2100 dbar or salinity >42 PSU or temperature <-3°C"
5. "Alert me to any areas where dissolved oxygen fell below 2 ml/L in coastal waters during the last week"


VARIATION 6: AMBIGUOUS/UNDERSPECIFIED QUERIES
----------------------------------------------
Purpose: Test system's ability to handle unclear requests and ask for clarification
Expected: Intelligent interpretation or clarification requests

1. "Show me the ocean data"
   (Too vague - which ocean? which parameter? which time period?)

2. "What's happening in the water?"
   (Unclear - which location? which phenomenon? which measurement?)

3. "Find the float"
   (Missing identifier - which specific float?)

4. "Show me anomalies"
   (Underspecified - which parameter? which threshold? where? when?)

5. "Get me yesterday's data"
   (Incomplete - which data type? which location? which depth?)


VARIATION 7: IRRELEVANT/OFF-TOPIC QUERIES
------------------------------------------
Purpose: Test system's ability to recognize and handle non-oceanographic queries
Expected: Polite rejection or redirection to relevant topics

1. "What's the weather forecast for New York tomorrow?"
   (Meteorology, not oceanography)

2. "Show me the best restaurants near the beach"
   (Completely unrelated to ocean data)

3. "How do I fix my boat engine?"
   (Marine engineering, not ocean science)

4. "What time does the aquarium open?"
   (Tourism question, not data query)

5. "Can you help me with my chemistry homework on titration?"
   (General chemistry, not ocean chemistry)


VARIATION 8: MALFORMED/TECHNICAL ERROR QUERIES
-----------------------------------------------
Purpose: Test error handling and input validation
Expected: Graceful error messages, suggestions for correction

1. "Show me temperature at coordinates 95°N 200°W"
   (Invalid coordinates - latitude >90°, longitude >180°)

2. "Get data from float ABCXYZ99999"
   (Invalid float ID format)

3. "Display salinity at -5000m depth"
   (Invalid depth - negative or beyond ocean floor)

4. "Show me temperature on February 30th, 2024"
   (Invalid date)

5. "Find floats with salinity = NULL AND temperature > NaN"
   (Technical jargon that should be interpreted correctly)


VARIATION 9: EDGE CASE QUERIES
-------------------------------
Purpose: Test boundary conditions and extreme scenarios
Expected: Proper handling of limits and special cases

1. "Show me all data from every float in the entire global ocean for the past 20 years"
   (Potentially huge dataset - should warn or paginate)

2. "Get temperature at exactly 0°N 0°E (null island)"
   (Unusual but valid location in the Atlantic)

3. "Display measurements from the deepest point in the Mariana Trench"
   (Extreme depth ~11,000m - may have limited data)

4. "Show me ice thickness in the Sahara Desert"
   (Geographically impossible - no ocean there)

5. "Find floats that have been active for more than 15 years"
   (Edge case - very few floats last that long)


VARIATION 10: NATURAL LANGUAGE VARIATIONS
------------------------------------------
Purpose: Test NLP capabilities with different phrasings of similar requests
Expected: Consistent results despite different wording

Same intent, different expressions:

1a. "Show me temperature profiles in the Arabian Sea from last month"
1b. "I need last month's temperature data for the Arabian Sea with depth profiles"
1c. "Can you display how temperature changes with depth in the Arabian Sea over the past 30 days?"
1d. "Arabian Sea temp profiles - last month please"
1e. "Temperature vs depth for Arabian Sea, previous month"

2a. "What's the salinity in the North Atlantic?"
2b. "Tell me the salt concentration in the northern Atlantic Ocean"
2c. "How salty is the water in the North Atlantic right now?"
2d. "North Atlantic salinity levels?"
2e. "Check salinity measurements for North Atlantic region"

3a. "Find all floats near the equator with anomalies above 36 PSU"
3b. "Show me equatorial floats where salinity exceeds 36 PSU"
3c. "Which floats at the equator have high salinity (>36 PSU)?"
3d. "Equatorial region - floats with salinity anomalies over 36 PSU"
3e. "Get me floats around 0° latitude reporting salinity above 36 PSU"

4a. "Compare temperature gradients between Indian Ocean and Pacific"
4b. "Show me how temperature changes differ in Indian vs Pacific Ocean"
4c. "Temperature gradient comparison: Indian Ocean versus Pacific"
4d. "What are the temperature gradient differences between Pacific and Indian Oceans?"
4e. "Contrast thermal gradients in Indian and Pacific basins"

5a. "Show me the trajectory of float 1900975 over the last year"
5b. "Track float 1900975's path for the past 12 months"
5c. "Where has float 1900975 been in the last year?"
5d. "Display 1-year movement history for float 1900975"
5e. "Float 1900975 - show me where it's traveled since last year"


BONUS VARIATION 11: CONTEXT-DEPENDENT QUERIES
----------------------------------------------
Purpose: Test system's ability to maintain context in conversation
Expected: Reference resolution, session memory

Conversation sequence:

User: "Show me temperature in the Pacific Ocean"
System: [Shows Pacific temperature data]

Then:
1. "Now show me salinity there"
   (Should refer to Pacific Ocean from previous query)

2. "What about at 500m depth?"
   (Should apply to Pacific + salinity context)

3. "Compare this to last year"
   (Should reference all previous constraints)

4. "Which floats are in this region?"
   (Should identify "this region" as Pacific)

5. "Show me their trajectories"
   (Should reference the floats just identified)


SUMMARY: TESTING STRATEGY
==========================

Distribute your 1000 queries as follows:

- Simple Direct Queries: 200 (20%)
- Complex Multi-Parameter: 200 (20%)
- Temporal Analysis: 150 (15%)
- Spatial Comparison: 150 (15%)
- Anomaly Detection: 100 (10%)
- Ambiguous/Underspecified: 50 (5%)
- Irrelevant/Off-topic: 50 (5%)
- Malformed/Error Cases: 50 (5%)
- Edge Cases: 30 (3%)
- Natural Language Variations: 20 (2%)

This distribution ensures comprehensive testing of:
✓ Core functionality
✓ Complex analytical capabilities
✓ Error handling
✓ Edge case robustness
✓ NLP understanding
✓ Context awareness
✓ User experience with unclear inputs

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
