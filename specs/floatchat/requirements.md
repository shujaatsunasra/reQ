# Requirements Document: FloatChat

## Introduction

FloatChat is an AI-powered oceanographic data analytics platform that enables marine researchers to query and analyze ARGO float data through natural language conversations. The system combines distributed MCP servers, intelligent query optimization, multi-modal data processing, and interactive visualizations to make complex oceanographic data accessible and actionable.

## Glossary

- **ARGO_Float**: An autonomous profiling float that measures ocean temperature, salinity, and other parameters
- **Profile**: A single vertical measurement cycle from an ARGO float containing depth-indexed measurements
- **MCP_Server**: Model Context Protocol server providing specialized data processing capabilities
- **MCP_Bridge**: Security proxy that validates and routes requests to MCP servers
- **NL2Operator**: Natural language to semantic operator translator component
- **Query_Planner**: Cost-based query optimization component that generates execution plans
- **Semantic_Operator**: Abstract representation of data operations in a directed acyclic graph
- **QC_Flag**: Quality control flag indicating measurement reliability (1=good, 4=bad, 9=missing)
- **Data_Mode**: Profile processing status (R=real-time, A=adjusted, D=delayed-mode)
- **T-S_Diagram**: Temperature-Salinity scatter plot for water mass identification
- **Hovmöller_Diagram**: Depth-time contour plot showing temporal evolution
- **PostGIS**: PostgreSQL extension for geographic objects and spatial queries
- **HNSW**: Hierarchical Navigable Small World graph for approximate nearest neighbor search
- **ChromaDB**: Vector database for semantic search using embedding vectors
- **System**: The FloatChat platform (used in EARS patterns)
- **User**: Marine researcher or oceanographer using the platform
- **Explorer_Mode**: Simplified UI mode with guided interactions
- **Power_Mode**: Advanced UI mode with DAG visualization and cost metrics
- **Confidence_Score**: Numerical measure (0-1) of query interpretation certainty
- **Deadline**: Maximum acceptable query execution time in milliseconds
- **Cache_Hit**: Successful retrieval of results from cache without recomputation
- **Security_Stage**: One of three validation phases (pattern, neural, LLM)
- **Memory_System**: Component that stores and retrieves learned patterns for optimization

## Requirements

### Requirement 1: Natural Language Query Processing

**User Story:** As a marine researcher, I want to ask questions in natural language about oceanographic data, so that I can access insights without learning complex query languages.

#### Acceptance Criteria

1. WHEN a user submits a natural language query, THE NL2Operator SHALL parse it into semantic operators within 100ms
2. WHEN the query contains geographic entities (e.g., "Arabian Sea", "North Atlantic"), THE NL2Operator SHALL extract spatial boundaries with >90% accuracy
3. WHEN the query contains temporal expressions (e.g., "last month", "2023 summer"), THE NL2Operator SHALL resolve them to ISO 8601 timestamps
4. WHEN the query contains oceanographic parameters (e.g., "temperature", "salinity"), THE NL2Operator SHALL map them to database column names
5. WHEN the query is ambiguous, THE NL2Operator SHALL generate multiple interpretations with confidence scores
6. WHEN the NL2Operator confidence score is below 0.7, THE System SHALL request clarification from the user
7. THE NL2Operator SHALL support queries in English language
8. WHEN processing queries, THE NL2Operator SHALL utilize its memory system to improve accuracy over time

### Requirement 2: Query Planning and Optimization

**User Story:** As a system operator, I want queries to be optimized automatically, so that users receive fast responses regardless of query complexity.

#### Acceptance Criteria

1. WHEN the Query_Planner receives semantic operators, THE Query_Planner SHALL generate an execution plan within 50ms
2. WHEN multiple execution strategies exist, THE Query_Planner SHALL select the plan with lowest predicted cost
3. WHEN a query has a deadline constraint, THE Query_Planner SHALL prioritize plans that meet the deadline
4. WHEN historical execution data exists, THE Query_Planner SHALL use ML-predicted latencies for cost estimation
5. THE Query_Planner SHALL consider cache availability when generating plans
6. WHEN a plan exceeds predicted cost by >20%, THE Query_Planner SHALL update its cost model
7. THE Query_Planner SHALL support parallel execution of independent operators
8. WHEN the Query_Planner generates a plan, THE System SHALL store it in Query_Planner memory for future optimization

### Requirement 3: MCP Server Architecture

**User Story:** As a system architect, I want specialized MCP servers for different data operations, so that the system is maintainable and scalable.

#### Acceptance Criteria

1. THE System SHALL implement six specialized MCP servers: StructuredDataServer, MetadataProcessingServer, ProfileAnalysisServer, SemanticDataServer, CachingServer, VisualizationServer
2. WHEN an MCP_Server receives a request, THE MCP_Server SHALL validate the request schema before processing
3. WHEN an MCP_Server completes processing, THE MCP_Server SHALL return results in a standardized JSON format
4. WHEN an MCP_Server encounters an error, THE MCP_Server SHALL return a structured error response with error code and message
5. THE StructuredDataServer SHALL handle SQL queries against the PostgreSQL database
6. THE MetadataProcessingServer SHALL process file_index queries and metadata extraction
7. THE ProfileAnalysisServer SHALL compute derived oceanographic metrics (mixed layer depth, gradients, anomalies)
8. THE SemanticDataServer SHALL perform vector similarity searches using ChromaDB
9. THE CachingServer SHALL manage Redis-based result caching with TTL policies
10. THE VisualizationServer SHALL generate visualization specifications for frontend rendering
11. WHEN an MCP_Server processes a request, THE MCP_Server SHALL log execution metrics to its memory system

### Requirement 4: Security and Validation

**User Story:** As a security administrator, I want all MCP requests validated through multiple stages, so that the system is protected from malicious queries.

#### Acceptance Criteria

1. WHEN a request enters the MCP_Bridge, THE MCP_Bridge SHALL apply pattern detection validation within 2ms
2. WHEN pattern detection is inconclusive, THE MCP_Bridge SHALL apply neural analysis within 55ms
3. WHEN neural analysis is inconclusive, THE MCP_Bridge SHALL apply LLM arbitration within 500ms
4. WHEN a request fails any Security_Stage, THE MCP_Bridge SHALL reject the request and log the threat
5. THE MCP_Bridge SHALL achieve >95% threat detection rate
6. THE MCP_Bridge SHALL maintain <1% false positive rate
7. WHEN the neural model detects a threat, THE System SHALL use E5-based embeddings for classification
8. THE MCP_Bridge SHALL rate-limit requests to 100 requests per minute per user
9. WHEN a user exceeds rate limits, THE MCP_Bridge SHALL return a 429 status code with retry-after header

### Requirement 5: Database Schema and Indexing

**User Story:** As a database administrator, I want an optimized schema with proper indexes, so that queries execute efficiently at scale.

#### Acceptance Criteria

1. THE System SHALL implement a profiles table with columns: profile_id, float_id, cycle_number, timestamp, geom, data_mode, direction
2. THE System SHALL implement a profile_measurements table with columns: measurement_id, profile_id, level_index, depth, temperature, salinity, pressure, QC flags
3. THE System SHALL implement a file_index table with columns: float_id, data_center, file_path, time_range, lat_range, lon_range, depth_range, metadata
4. THE System SHALL create a GiST index on the geom column for spatial queries
5. THE System SHALL create a GIN index on JSONB metadata columns for flexible querying
6. THE System SHALL create B-tree indexes on timestamp, float_id, and profile_id columns
7. WHEN a spatial query is executed, THE System SHALL utilize the GiST index for <100ms response time
8. THE System SHALL use PostGIS extension for geographic operations
9. WHEN inserting new profiles, THE System SHALL validate QC_Flag values are in the set {1, 2, 3, 4, 8, 9}
10. WHEN inserting new profiles, THE System SHALL validate Data_Mode values are in the set {'R', 'A', 'D'}

### Requirement 6: Caching Strategy

**User Story:** As a performance engineer, I want intelligent caching of query results, so that repeated queries return instantly.

#### Acceptance Criteria

1. WHEN a query is executed, THE CachingServer SHALL check Redis cache before database access
2. WHEN a Cache_Hit occurs, THE System SHALL return cached results within 50ms
3. THE System SHALL achieve >70% cache hit rate for production workloads
4. WHEN caching results, THE CachingServer SHALL generate cache keys from normalized query representations
5. THE CachingServer SHALL set TTL values based on data freshness requirements (real-time: 5min, historical: 24hr)
6. WHEN cache memory exceeds 80% capacity, THE CachingServer SHALL evict entries using LRU policy
7. WHEN new data is ingested, THE CachingServer SHALL invalidate affected cache entries
8. THE CachingServer SHALL support cache warming for frequently accessed data

### Requirement 7: Iterative Query Refinement

**User Story:** As a marine researcher, I want the system to refine queries automatically when initial results are insufficient, so that I get comprehensive answers without manual iteration.

#### Acceptance Criteria

1. WHEN a query returns results with Confidence_Score below 0.8, THE System SHALL initiate refinement iteration
2. WHEN refining a query, THE System SHALL adjust parameters based on result quality metrics
3. THE System SHALL limit refinement iterations to maximum 3 attempts
4. WHEN refinement improves Confidence_Score by <0.1, THE System SHALL stop iteration
5. WHEN all refinement attempts are exhausted, THE System SHALL return best available results with confidence indication
6. THE System SHALL store successful refinement patterns in Refinement_Memory
7. WHEN a similar query is encountered, THE System SHALL apply learned refinement strategies proactively

### Requirement 8: User Interface Modes

**User Story:** As a user, I want to choose between simplified and advanced interfaces, so that I can match the UI complexity to my expertise level.

#### Acceptance Criteria

1. THE System SHALL provide Explorer_Mode with simplified, guided interactions
2. THE System SHALL provide Power_Mode with DAG visualization and cost metrics
3. WHEN a user switches modes, THE System SHALL preserve conversation history and context
4. WHEN in Explorer_Mode, THE System SHALL hide technical details (execution plans, cost metrics)
5. WHEN in Power_Mode, THE System SHALL display semantic operator DAG with execution costs
6. WHEN in Power_Mode, THE System SHALL allow manual query plan editing
7. THE System SHALL remember user's mode preference across sessions
8. WHEN in Explorer_Mode, THE System SHALL provide suggested follow-up questions

### Requirement 9: API Configuration

**User Story:** As a user, I want to configure my LLM API keys through the UI, so that I can use my preferred AI provider without backend configuration.

#### Acceptance Criteria

1. WHEN a user enters an API key, THE System SHALL validate it against the provider's API within 2 seconds
2. THE System SHALL support API keys for Gemini 2.0 Flash, GPT-4o, and Claude Sonnet 4.5
3. WHEN API key validation succeeds, THE System SHALL display animated success feedback
4. WHEN API key validation fails, THE System SHALL display error message with troubleshooting guidance
5. THE System SHALL store API keys encrypted in browser local storage
6. THE System SHALL NOT transmit API keys to backend servers
7. WHEN no API key is configured, THE System SHALL display inline configuration prompt
8. THE System SHALL allow users to switch between configured API providers

### Requirement 10: Chat Interface

**User Story:** As a user, I want a conversational interface similar to Gemini, so that querying data feels natural and intuitive.

#### Acceptance Criteria

1. WHEN a user sends a message, THE System SHALL display it in a right-aligned chat bubble
2. WHEN the System responds, THE System SHALL display the response in a left-aligned chat bubble
3. WHEN processing a query, THE System SHALL display an animated typing indicator
4. WHEN a response contains visualizations, THE System SHALL display inline preview thumbnails
5. WHEN a user clicks a visualization preview, THE System SHALL expand it to full size with smooth animation
6. THE System SHALL support markdown formatting in chat messages
7. THE System SHALL display timestamps for messages when hovering
8. WHEN a query fails, THE System SHALL display error messages in a distinct error bubble style
9. THE System SHALL auto-scroll to the latest message when new content appears
10. THE System SHALL support copying message content to clipboard

### Requirement 11: Animation System

**User Story:** As a user, I want smooth, purposeful animations throughout the interface, so that the application feels polished and responsive.

#### Acceptance Criteria

1. THE System SHALL implement micro-animations for hover, focus, and loading states with <100ms duration
2. THE System SHALL implement macro-animations for view transitions and visualization renders with <300ms duration
3. THE System SHALL implement singleton animations for onboarding and first-time experiences
4. WHEN a user hovers over interactive elements, THE System SHALL apply scale or color transitions
5. WHEN switching between UI modes, THE System SHALL animate the transition over 250ms
6. WHEN visualizations load, THE System SHALL animate their appearance with fade-in and scale effects
7. THE System SHALL respect user's prefers-reduced-motion setting by disabling non-essential animations
8. WHEN animations are disabled, THE System SHALL maintain functional transitions without motion effects
9. THE System SHALL use Framer Motion library for animation implementation
10. THE System SHALL maintain 60fps frame rate during all animations

### Requirement 12: Visualization Generation (Phase 1 MVP)

**User Story:** As a marine researcher, I want essential oceanographic visualizations generated automatically, so that I can understand spatial and temporal patterns in the data.

#### Acceptance Criteria

1. WHEN a query involves float trajectories, THE VisualizationServer SHALL generate an interactive map with float paths
2. WHEN a query involves depth-time data, THE VisualizationServer SHALL generate Hovmöller_Diagram contour plots
3. WHEN a query compares vertical profiles, THE VisualizationServer SHALL generate overlaid profile line charts
4. WHEN a query involves spatial distributions, THE VisualizationServer SHALL generate geospatial heat maps
5. WHEN a query involves time series, THE VisualizationServer SHALL generate line charts with confidence intervals
6. WHEN a query involves data quality, THE VisualizationServer SHALL generate QC dashboard with flag distributions
7. THE System SHALL render visualizations using Plotly.js, Recharts, or D3.js based on chart type
8. THE System SHALL render maps using Leaflet with OpenStreetMap tiles
9. WHEN generating visualizations, THE VisualizationServer SHALL complete within 2 seconds for datasets <10,000 points
10. THE System SHALL support exporting visualizations as PNG, SVG, or interactive HTML

### Requirement 13: Visualization Generation (Phase 2 Enhanced)

**User Story:** As a marine researcher, I want advanced oceanographic visualizations for detailed analysis, so that I can identify water masses, fronts, and ecosystem patterns.

#### Acceptance Criteria

1. WHEN a query involves water mass analysis, THE VisualizationServer SHALL generate T-S_Diagram scatter plots with density contours
2. WHEN a query involves BGC parameters, THE VisualizationServer SHALL generate correlation matrices with hierarchical clustering
3. WHEN a query involves mixed layer depth, THE VisualizationServer SHALL generate evolution plots with seasonal overlays
4. WHEN a query involves ocean fronts, THE VisualizationServer SHALL generate gradient magnitude maps with front detection overlays
5. WHEN a query involves water mass transit, THE VisualizationServer SHALL generate Lagrangian trajectory plots with age coloring
6. WHEN a query involves ecosystem indicators, THE VisualizationServer SHALL generate multi-parameter dashboards with threshold alerts
7. WHERE Phase 2 visualizations are enabled, THE System SHALL support all Phase 1 visualization types
8. THE System SHALL allow users to toggle between Phase 1 and Phase 2 visualization complexity

### Requirement 14: Visualization Generation (Phase 3 Advanced)

**User Story:** As a marine researcher, I want cutting-edge visualizations for publication-quality analysis, so that I can explore complex 3D patterns and real-time data streams.

#### Acceptance Criteria

1. WHEN a query involves multi-parameter analysis, THE VisualizationServer SHALL generate synchronized multi-panel dashboards
2. WHEN a query involves real-time data, THE VisualizationServer SHALL generate streaming visualizations with <1s update latency
3. WHEN a query involves 3D ocean structure, THE VisualizationServer SHALL generate volume renderings with isosurface extraction
4. WHEN a query involves mesoscale features, THE VisualizationServer SHALL generate eddy detection overlays with rotation indicators
5. WHEN a query involves frequency analysis, THE VisualizationServer SHALL generate spectral analysis plots with significance testing
6. WHERE Phase 3 visualizations are enabled, THE System SHALL support all Phase 1 and Phase 2 visualization types
7. THE System SHALL allow users to configure visualization phase level in settings

### Requirement 15: Performance Targets

**User Story:** As a user, I want fast query responses regardless of complexity, so that I can maintain analytical flow without waiting.

#### Acceptance Criteria

1. WHEN a simple query is executed (single table, <1000 rows), THE System SHALL respond within 500ms
2. WHEN a medium complexity query is executed (joins, aggregations, <10,000 rows), THE System SHALL respond within 2 seconds
3. WHEN a complex multi-modal query is executed (semantic search + SQL + analytics), THE System SHALL respond within 5 seconds
4. WHEN a dashboard is generated (multiple visualizations), THE System SHALL complete within 10 seconds
5. THE System SHALL support 100 concurrent users with <10% performance degradation
6. WHEN the system is under load, THE System SHALL maintain response times within 150% of baseline
7. THE System SHALL process 80% of queries within their target response time
8. WHEN a query exceeds its Deadline, THE System SHALL return partial results with timeout indication

### Requirement 16: Memory Systems

**User Story:** As a system operator, I want the system to learn from usage patterns, so that performance and accuracy improve over time.

#### Acceptance Criteria

1. THE System SHALL implement NL2Operator_Memory for storing query interpretation patterns
2. THE System SHALL implement Query_Planner_Memory for storing execution plan performance metrics
3. THE System SHALL implement Refinement_Memory for storing successful query refinement strategies
4. THE System SHALL implement MCP_Server_Memory for storing operation-specific optimization patterns
5. WHEN a query interpretation succeeds, THE NL2Operator SHALL store the pattern in NL2Operator_Memory
6. WHEN a query plan executes, THE Query_Planner SHALL store actual vs predicted costs in Query_Planner_Memory
7. WHEN a refinement improves results, THE System SHALL store the refinement strategy in Refinement_Memory
8. WHEN an MCP_Server optimizes an operation, THE MCP_Server SHALL store the optimization in MCP_Server_Memory
9. THE System SHALL use stored memory patterns to improve future query processing
10. THE System SHALL periodically prune memory entries with low utility scores

### Requirement 17: Filter-Aware Vector Indexing

**User Story:** As a performance engineer, I want semantic search to respect query filters efficiently, so that vector searches don't return irrelevant results.

#### Acceptance Criteria

1. WHEN building vector indexes, THE SemanticDataServer SHALL create condition-aware HNSW graphs
2. WHEN a semantic query includes filters (time, space, QC), THE SemanticDataServer SHALL use the appropriate filtered index
3. THE SemanticDataServer SHALL maintain separate HNSW graphs for common filter combinations
4. WHEN a filter combination has no dedicated index, THE SemanticDataServer SHALL fall back to post-filtering
5. THE System SHALL achieve <200ms semantic search latency for filtered queries with dedicated indexes
6. WHEN index memory exceeds limits, THE SemanticDataServer SHALL consolidate low-usage indexes
7. THE SemanticDataServer SHALL rebuild indexes incrementally as new data arrives

### Requirement 18: Credential Management

**User Story:** As a security-conscious user, I want all credentials managed securely without hardcoding, so that my API keys and database credentials are protected.

#### Acceptance Criteria

1. THE System SHALL NOT contain hardcoded API keys, database passwords, or secrets in source code
2. WHEN deploying the backend, THE System SHALL read credentials from environment variables
3. WHEN a user configures API keys, THE System SHALL store them encrypted in browser local storage
4. THE System SHALL use AES-256 encryption for stored credentials
5. WHEN transmitting credentials, THE System SHALL use TLS 1.3 or higher
6. THE System SHALL support credential rotation without application restart
7. WHEN credentials are invalid, THE System SHALL prompt for reconfiguration without exposing the invalid credential
8. THE System SHALL log credential access attempts for security auditing

### Requirement 19: Error Handling and Resilience

**User Story:** As a user, I want the system to handle errors gracefully, so that temporary failures don't disrupt my workflow.

#### Acceptance Criteria

1. WHEN an MCP_Server is unavailable, THE System SHALL retry the request up to 3 times with exponential backoff
2. WHEN all retries fail, THE System SHALL return a user-friendly error message with suggested actions
3. WHEN a database query times out, THE System SHALL cancel the query and suggest query simplification
4. WHEN the LLM API is unavailable, THE System SHALL fall back to cached interpretations if available
5. WHEN a visualization fails to render, THE System SHALL display the raw data in table format
6. THE System SHALL log all errors with stack traces to the ELK Stack for debugging
7. WHEN a critical component fails, THE System SHALL degrade gracefully by disabling dependent features
8. THE System SHALL display system health status in the UI footer

### Requirement 20: Monitoring and Observability

**User Story:** As a system operator, I want comprehensive monitoring and logging, so that I can diagnose issues and optimize performance.

#### Acceptance Criteria

1. THE System SHALL expose Prometheus metrics for query latency, cache hit rate, and error rates
2. THE System SHALL log all queries with execution time, plan, and result size to Elasticsearch
3. THE System SHALL create Grafana dashboards for real-time performance monitoring
4. WHEN query latency exceeds thresholds, THE System SHALL trigger alerts to operators
5. THE System SHALL track and report on the 95th percentile query latency
6. THE System SHALL log security events (blocked requests, rate limit violations) with severity levels
7. THE System SHALL provide distributed tracing for multi-component queries using OpenTelemetry
8. THE System SHALL retain logs for 90 days for compliance and debugging

### Requirement 21: Data Ingestion

**User Story:** As a data administrator, I want to ingest ARGO float data from standard sources, so that the platform stays current with the latest observations.

#### Acceptance Criteria

1. WHEN new ARGO NetCDF files are available, THE System SHALL download them from GDAC servers
2. WHEN parsing NetCDF files, THE System SHALL extract profiles, measurements, and metadata
3. WHEN inserting profiles, THE System SHALL validate data against ARGO quality control standards
4. WHEN duplicate profiles are detected, THE System SHALL update existing records rather than creating duplicates
5. THE System SHALL process at least 1000 profiles per minute during bulk ingestion
6. WHEN ingestion fails, THE System SHALL log the error and continue with remaining files
7. THE System SHALL update the file_index table with spatial and temporal bounds for each file
8. THE System SHALL invalidate affected cache entries after successful ingestion

### Requirement 22: Deployment and Scalability

**User Story:** As a DevOps engineer, I want the system containerized and orchestrated, so that it can scale horizontally and deploy reliably.

#### Acceptance Criteria

1. THE System SHALL provide Docker images for all components (frontend, backend, MCP servers)
2. THE System SHALL provide Kubernetes manifests for orchestration
3. WHEN deploying to Kubernetes, THE System SHALL support horizontal pod autoscaling based on CPU and memory
4. THE System SHALL use RabbitMQ for asynchronous task queuing between components
5. WHEN a component crashes, Kubernetes SHALL automatically restart it within 30 seconds
6. THE System SHALL support rolling updates with zero downtime
7. THE System SHALL provide health check endpoints for Kubernetes liveness and readiness probes
8. THE System SHALL support deployment to cloud providers (AWS, GCP, Azure) via Terraform

### Requirement 23: Testing and Quality Assurance

**User Story:** As a developer, I want comprehensive automated tests, so that I can refactor and extend the system with confidence.

#### Acceptance Criteria

1. THE System SHALL achieve >80% code coverage for backend components
2. THE System SHALL achieve >70% code coverage for frontend components
3. THE System SHALL include unit tests for all NL2Operator parsing logic
4. THE System SHALL include integration tests for MCP_Bridge security validation
5. THE System SHALL include end-to-end tests for complete query workflows
6. THE System SHALL include property-based tests for query optimization correctness
7. THE System SHALL include load tests validating 100 concurrent user performance target
8. THE System SHALL run all tests in CI/CD pipeline before deployment
9. WHEN tests fail, THE System SHALL block deployment and notify developers

### Requirement 24: Documentation

**User Story:** As a new developer or user, I want comprehensive documentation, so that I can understand and use the system effectively.

#### Acceptance Criteria

1. THE System SHALL provide API documentation for all MCP server endpoints using OpenAPI 3.0
2. THE System SHALL provide architecture diagrams showing component interactions
3. THE System SHALL provide user guides for both Explorer_Mode and Power_Mode
4. THE System SHALL provide example queries demonstrating key capabilities
5. THE System SHALL provide deployment guides for Docker and Kubernetes
6. THE System SHALL provide developer guides for extending MCP servers
7. THE System SHALL provide inline code documentation for all public APIs
8. THE System SHALL provide troubleshooting guides for common issues
