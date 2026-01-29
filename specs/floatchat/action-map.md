# Implementation Plan: FloatChat

## Overview

This implementation plan breaks down the FloatChat system into discrete, incremental tasks. The approach follows a bottom-up strategy: build core infrastructure first (database, MCP servers), then add intelligence layers (NL2Operator, Query Planner), then security (MCP Bridge), and finally the user interface. Each task builds on previous work, with checkpoints to ensure stability before proceeding.

## Tasks

- [x] 1. Set up project structure and core infrastructure
  - Create monorepo structure with backend (Python/FastAPI) and frontend (Next.js/TypeScript) directories
  - Set up Supabase project (PostgreSQL + PostGIS + Realtime included)
  - Set up Docker Compose for local development (Redis, ChromaDB, RabbitMQ only - Supabase handles database)
  - Configure environment variable management (.env files, no hardcoded secrets, Supabase connection strings)
  - Set up Python virtual environment with FastAPI, supabase-py, redis, chromadb dependencies
  - Set up Next.js 14+ project with App Router, TypeScript, Zustand, Framer Motion, Plotly.js, Recharts, D3.js, Leaflet
  - Configure linters (pylint, black, eslint, prettier) and pre-commit hooks
  - _Requirements: 18.1, 18.2, 22.1_

- [x] 2. Implement database schema and migrations
  - [x] 2.1 Create Supabase database schema
    - Create profiles table with PostGIS geometry column in Supabase dashboard or via SQL migration
    - Create profile_measurements table with QC flag constraints
    - Create file_index table with JSONB metadata column
    - Add CHECK constraints for data_mode and QC flags
    - Enable PostGIS extension in Supabase if not already enabled
    - _Requirements: 5.1, 5.2, 5.3, 5.9, 5.10_
  
  - [x] 2.2 Create database indexes
    - Create GiST index on profiles.geom for spatial queries in Supabase
    - Create GIN index on file_index.metadata for JSONB queries
    - Create B-tree indexes on timestamp, float_id, profile_id columns
    - Create composite indexes for common query patterns
    - _Requirements: 5.4, 5.5, 5.6_
  
  - [ ]* 2.3 Write property test for QC flag validation
    - **Property 23: QC flag validation**
    - **Validates: Requirements 5.9**
  
  - [ ]* 2.4 Write property test for data mode validation
    - **Property 24: Data mode validation**
    - **Validates: Requirements 5.10**
  
  - [ ]* 2.5 Write unit tests for database schema
    - Test table creation and constraints
    - Test index existence and usage
    - Test spatial query functionality with PostGIS
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

- [x] 3. Implement StructuredDataServer (MCP Server)
  - [x] 3.1 Create MCP server base class
    - Define request/response schemas using Pydantic
    - Implement request validation decorator
    - Implement standardized error response format
    - Add execution metrics logging to memory system
    - _Requirements: 3.2, 3.3, 3.4, 3.11_
  
  - [x] 3.2 Implement query_profiles operation
    - Build parameterized SQL query with spatial, temporal, and attribute filters
    - Use PostGIS ST_Contains for bounding box queries
    - Implement pagination with limit/offset
    - Return results in standardized JSON format
    - _Requirements: 3.5_
  
  - [x] 3.3 Implement query_measurements operation
    - Build SQL query joining profiles and measurements tables
    - Filter by profile IDs, parameters, depth range, QC threshold
    - Return measurements with QC flags
    - _Requirements: 3.5_
  
  - [ ]* 3.4 Write property test for request schema validation
    - **Property 18: Request schema validation**
    - **Validates: Requirements 3.2**
  
  - [ ]* 3.5 Write property test for response format consistency
    - **Property 19: Response format consistency**
    - **Validates: Requirements 3.3**
  
  - [ ]* 3.6 Write property test for spatial query performance
    - **Property 22: Spatial query performance**
    - **Validates: Requirements 5.7**
  
  - [ ]* 3.7 Write unit tests for StructuredDataServer
    - Test query_profiles with various filter combinations
    - Test query_measurements with different parameters
    - Test error handling for invalid inputs
    - _Requirements: 3.5_

- [x] 4. Implement CachingServer (MCP Server)
  - [x] 4.1 Implement Redis connection and cache operations
    - Create Redis client with connection pooling
    - Implement get_cached operation with TTL retrieval
    - Implement set_cached operation with TTL and tags
    - Implement invalidate_by_tag operation
    - _Requirements: 3.9, 6.1, 6.2, 6.7_
  
  - [x] 4.2 Implement cache key generation
    - Create normalized cache key from operation and params (sort keys, hash)
    - Ensure equivalent queries generate identical keys
    - _Requirements: 6.4_
  
  - [x] 4.3 Implement TTL policy logic
    - Infer TTL based on data freshness (real-time: 5min, historical: 24hr)
    - Support custom TTL overrides
    - _Requirements: 6.5_
  
  - [x] 4.4 Implement LRU eviction
    - Monitor cache memory usage
    - Evict least recently used entries when capacity >80%
    - _Requirements: 6.6_
  
  - [ ]* 4.5 Write property test for cache-first behavior
    - **Property 25: Cache-first behavior**
    - **Validates: Requirements 6.1**
  
  - [ ]* 4.6 Write property test for cache hit performance
    - **Property 26: Cache hit performance**
    - **Validates: Requirements 6.2**
  
  - [ ]* 4.7 Write property test for cache key normalization
    - **Property 27: Cache key normalization**
    - **Validates: Requirements 6.4**
  
  - [ ]* 4.8 Write property test for TTL policy correctness
    - **Property 28: TTL policy correctness**
    - **Validates: Requirements 6.5**
  
  - [ ]* 4.9 Write unit tests for CachingServer
    - Test cache hit and miss scenarios
    - Test TTL expiration
    - Test tag-based invalidation
    - _Requirements: 6.1, 6.2, 6.4, 6.5, 6.6, 6.7_

- [x] 5. Checkpoint - Ensure database and caching tests pass
  - Ensure all tests pass, ask the user if questions arise.


- [x] 6. Implement SemanticDataServer (MCP Server)
  - [x] 6.1 Set up ChromaDB collections
    - Create profile_embeddings collection with HNSW configuration
    - Create filter-aware collections (global, recent_6mo, high_qc, regional)
    - Configure E5-large-v2 embedding model
    - _Requirements: 3.8, 17.1, 17.3_
  
  - [x] 6.2 Implement semantic_search operation
    - Generate query embedding using E5 model
    - Select appropriate HNSW index based on filters
    - Perform vector similarity search with topK
    - Implement post-filtering fallback for uncommon filter combinations
    - _Requirements: 3.8, 17.2, 17.4_
  
  - [x] 6.3 Implement incremental index updates
    - Add new profile embeddings to relevant indexes
    - Update indexes without full rebuild
    - _Requirements: 17.7_
  
  - [ ]* 6.4 Write property test for filter-aware index selection
    - **Property 48: Filter-aware index selection**
    - **Validates: Requirements 17.2**
  
  - [ ]* 6.5 Write property test for post-filtering fallback
    - **Property 49: Post-filtering fallback**
    - **Validates: Requirements 17.4**
  
  - [ ]* 6.6 Write property test for filtered search performance
    - **Property 50: Filtered search performance**
    - **Validates: Requirements 17.5**
  
  - [ ]* 6.7 Write unit tests for SemanticDataServer
    - Test semantic search with various filters
    - Test index selection logic
    - Test incremental updates
    - _Requirements: 3.8, 17.2, 17.4, 17.7_

- [ ] 7. Implement ProfileAnalysisServer (MCP Server)
  - [x] 7.1 Implement compute_mixed_layer_depth operation
    - Fetch profile measurements from database
    - Implement temperature-based MLD calculation
    - Implement density-based MLD calculation using gsw library
    - Compute confidence scores based on data quality
    - _Requirements: 3.7_
  
  - [x] 7.2 Implement compute_gradients operation
    - Fetch profile measurements
    - Implement finite difference gradient calculation
    - Implement spline-based gradient calculation
    - Return gradients at each depth level
    - _Requirements: 3.7_
  
  - [ ]* 7.3 Write unit tests for ProfileAnalysisServer
    - Test MLD calculation with known profiles
    - Test gradient calculation with synthetic data
    - Test edge cases (insufficient data, missing QC flags)
    - _Requirements: 3.7_

- [x] 8. Implement MetadataProcessingServer (MCP Server)
  - [x] 8.1 Implement file_index query operations
    - Query file_index table by float_id, data_center, time/spatial ranges
    - Extract metadata from JSONB column
    - Return file paths and bounds
    - _Requirements: 3.6_
  
  - [ ]* 8.2 Write unit tests for MetadataProcessingServer
    - Test file_index queries with various filters
    - Test JSONB metadata extraction
    - _Requirements: 3.6_

- [x] 9. Implement VisualizationServer (MCP Server)
  - [x] 9.1 Implement trajectory map generation
    - Group data by float_id
    - Generate Leaflet map specification with trajectories
    - Compute center and zoom level from data bounds
    - Assign colors to floats
    - _Requirements: 3.10, 12.1, 12.8_
  
  - [x] 9.2 Implement Hovmöller diagram generation
    - Pivot data to create depth-time grid
    - Generate Plotly contour plot specification
    - Configure color scale and axes
    - _Requirements: 3.10, 12.2_
  
  - [x] 9.3 Implement vertical profile comparison generation
    - Generate Plotly line chart with overlaid profiles
    - Configure axes (depth inverted on y-axis)
    - Add legend and hover information
    - _Requirements: 3.10, 12.3_
  
  - [x] 9.4 Implement geospatial heatmap generation
    - Generate Plotly or Leaflet heatmap specification
    - Configure color scale based on parameter
    - _Requirements: 3.10, 12.4_
  
  - [x] 9.5 Implement time series generation
    - Generate Recharts line chart specification
    - Add confidence intervals if available
    - _Requirements: 3.10, 12.5_
  
  - [x] 9.6 Implement QC dashboard generation
    - Generate Recharts dashboard with QC flag distributions
    - Show pie charts and bar charts for QC statistics
    - _Requirements: 3.10, 12.6_
  
  - [ ]* 9.7 Write property test for visualization type selection
    - **Property 37: Visualization type selection**
    - **Validates: Requirements 12.1, 12.2, 12.3**
  
  - [ ]* 9.8 Write property test for visualization library selection
    - **Property 38: Visualization library selection**
    - **Validates: Requirements 12.7**
  
  - [ ]* 9.9 Write property test for visualization generation performance
    - **Property 39: Visualization generation performance**
    - **Validates: Requirements 12.9**
  
  - [ ]* 9.10 Write unit tests for VisualizationServer
    - Test each visualization type with sample data
    - Test edge cases (empty data, single point)
    - Verify output conforms to library specifications
    - _Requirements: 3.10, 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_

- [x] 10. Checkpoint - Ensure all MCP servers are functional
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Implement NL2Operator component
  - [x] 11.1 Set up spaCy NLP pipeline
    - Load spaCy English model (en_core_web_lg)
    - Configure NER for geographic entities, dates, parameters
    - Set up dependency parser
    - _Requirements: 1.1_
  
  - [x] 11.2 Implement entity extraction
    - Extract geographic entities and map to bounding boxes
    - Extract temporal expressions and resolve to ISO 8601 timestamps
    - Extract oceanographic parameters and map to database columns
    - Compute confidence scores for each extraction
    - _Requirements: 1.2, 1.3, 1.4_
  
  - [x] 11.3 Implement semantic operator generation
    - Convert extracted entities to semantic operators (filter, aggregate, join, etc.)
    - Build operator DAG with dependencies
    - Compute overall confidence score
    - _Requirements: 1.1_
  
  - [x] 11.4 Implement ambiguity handling
    - Generate multiple interpretations for ambiguous queries
    - Assign confidence scores to each interpretation
    - Request clarification when confidence <0.7
    - _Requirements: 1.5, 1.6_
  
  - [x] 11.5 Implement NL2Operator memory integration
    - Store successful interpretations in NL2Operator_Memory
    - Query memory for similar past queries
    - Use stored patterns to improve accuracy
    - _Requirements: 1.8, 16.5_
  
  - [ ]* 11.6 Write property test for parsing performance
    - **Property 1: NL2Operator parsing performance**
    - **Validates: Requirements 1.1**
  
  - [ ]* 11.7 Write property test for geographic entity extraction
    - **Property 2: Geographic entity extraction accuracy**
    - **Validates: Requirements 1.2**
  
  - [ ]* 11.8 Write property test for temporal expression resolution
    - **Property 3: Temporal expression resolution**
    - **Validates: Requirements 1.3**
  
  - [ ]* 11.9 Write property test for parameter mapping
    - **Property 4: Parameter mapping correctness**
    - **Validates: Requirements 1.4**
  
  - [ ]* 11.10 Write property test for ambiguity handling
    - **Property 5: Ambiguity handling**
    - **Validates: Requirements 1.5**
  
  - [ ]* 11.11 Write property test for low confidence clarification
    - **Property 6: Low confidence clarification**
    - **Validates: Requirements 1.6**
  
  - [ ]* 11.12 Write unit tests for NL2Operator
    - Test specific queries (Arabian Sea, North Atlantic, etc.)
    - Test temporal expressions (last month, 2023 summer, etc.)
    - Test parameter variations (temperature, salinity, etc.)
    - Test error handling for invalid queries
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

- [x] 12. Implement Query Planner component
  - [x] 12.1 Implement cost estimation
    - Define base costs for each operator type
    - Adjust costs based on data volume estimates
    - Adjust costs based on cache availability
    - Query Query_Planner_Memory for historical costs
    - _Requirements: 2.1, 2.4, 2.5_
  
  - [x] 12.2 Implement execution plan generation
    - Build dependency graph from operator DAG
    - Identify independent operators for parallelization
    - Assign operators to appropriate MCP servers
    - Generate execution steps with timeouts
    - _Requirements: 2.1, 2.7_
  
  - [x] 12.3 Implement plan selection
    - Generate multiple candidate plans
    - Select plan with lowest predicted cost
    - Respect deadline constraints if specified
    - _Requirements: 2.2, 2.3_
  
  - [x] 12.4 Implement cost model learning
    - Store actual vs predicted costs in Query_Planner_Memory
    - Update cost model when prediction error >20%
    - _Requirements: 2.6, 16.6_
  
  - [ ]* 12.5 Write property test for planning performance
    - **Property 7: Query planning performance**
    - **Validates: Requirements 2.1**
  
  - [ ]* 12.6 Write property test for cost-based plan selection
    - **Property 8: Cost-based plan selection**
    - **Validates: Requirements 2.2**
  
  - [ ]* 12.7 Write property test for deadline-aware planning
    - **Property 9: Deadline-aware planning**
    - **Validates: Requirements 2.3**
  
  - [ ]* 12.8 Write property test for cache-aware planning
    - **Property 10: Cache-aware planning**
    - **Validates: Requirements 2.5**
  
  - [ ]* 12.9 Write property test for cost model learning
    - **Property 11: Cost model learning**
    - **Validates: Requirements 2.6**
  
  - [ ]* 12.10 Write property test for parallel execution identification
    - **Property 12: Parallel execution identification**
    - **Validates: Requirements 2.7**
  
  - [ ]* 12.11 Write unit tests for Query Planner
    - Test plan generation for various operator DAGs
    - Test cost estimation with different scenarios
    - Test deadline constraint handling
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

- [x] 13. Checkpoint - Ensure query processing pipeline works
  - Ensure all tests pass, ask the user if questions arise.


- [x] 14. Implement MCP Bridge security layer
  - [x] 14.1 Implement pattern detection stage
    - Define regex patterns for SQL injection, path traversal, XSS, code execution
    - Implement pattern matching with <2ms latency
    - Return validation result with confidence
    - _Requirements: 4.1_
  
  - [x] 14.2 Implement neural analysis stage
    - Load E5-large-v2 model for embeddings
    - Train binary classifier on MCP-AttackBench dataset
    - Generate embeddings and classify requests
    - Return validation result with confidence (trigger if pattern detection inconclusive)
    - _Requirements: 4.2, 4.7_
  
  - [x] 14.3 Implement LLM arbitration stage
    - Configure Gemini 2.0 Flash API client
    - Generate security analysis prompt
    - Parse LLM response for malicious/benign classification
    - Return validation result (trigger if neural analysis inconclusive)
    - _Requirements: 4.3_
  
  - [x] 14.4 Implement three-stage validation pipeline
    - Orchestrate pattern → neural → LLM stages
    - Short-circuit on conclusive results
    - Log rejected requests with threat details
    - _Requirements: 4.4_
  
  - [x] 14.5 Implement rate limiting
    - Track requests per user per minute using Redis
    - Reject requests exceeding 100/min with 429 status
    - Include retry-after header in response
    - _Requirements: 4.8, 4.9_
  
  - [ ]* 14.6 Write property test for security validation performance
    - **Property 13: Security validation performance**
    - **Validates: Requirements 4.1, 4.2, 4.3**
  
  - [ ]* 14.7 Write property test for malicious request rejection
    - **Property 14: Malicious request rejection**
    - **Validates: Requirements 4.4**
  
  - [ ]* 14.8 Write property test for threat detection rate
    - **Property 15: Threat detection rate**
    - **Validates: Requirements 4.5**
  
  - [ ]* 14.9 Write property test for false positive rate
    - **Property 16: False positive rate**
    - **Validates: Requirements 4.6**
  
  - [ ]* 14.10 Write property test for rate limiting enforcement
    - **Property 17: Rate limiting enforcement**
    - **Validates: Requirements 4.8**
  
  - [ ]* 14.11 Write unit tests for MCP Bridge
    - Test each validation stage independently
    - Test three-stage pipeline with various request types
    - Test rate limiting with concurrent requests
    - Test error logging
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.8, 4.9_

- [x] 15. Implement Iterative Refinement component
  - [x] 15.1 Implement confidence evaluation
    - Compute confidence based on result count, data quality, spatial/temporal coverage
    - Return confidence score 0-1
    - _Requirements: 7.1_
  
  - [x] 15.2 Implement adjustment generation
    - Analyze result deficiencies (too few results, low quality, lack of diversity)
    - Generate parameter adjustments (expand bounds, tighten QC, change sampling)
    - Query Refinement_Memory for learned strategies
    - _Requirements: 7.2, 7.7_
  
  - [x] 15.3 Implement refinement loop
    - Trigger refinement when confidence <0.8
    - Apply adjustments and re-execute query
    - Limit to 3 iterations maximum
    - Stop early if improvement <0.1
    - Store successful refinements in Refinement_Memory
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_
  
  - [ ]* 15.4 Write property test for automatic refinement triggering
    - **Property 31: Automatic refinement triggering**
    - **Validates: Requirements 7.1**
  
  - [ ]* 15.5 Write property test for parameter adjustment
    - **Property 32: Parameter adjustment**
    - **Validates: Requirements 7.2**
  
  - [ ]* 15.6 Write property test for maximum iteration limit
    - **Property 33: Maximum iteration limit**
    - **Validates: Requirements 7.3**
  
  - [ ]* 15.7 Write property test for early stopping
    - **Property 34: Early stopping on minimal improvement**
    - **Validates: Requirements 7.4**
  
  - [ ]* 15.8 Write property test for refinement memory storage
    - **Property 35: Refinement memory storage**
    - **Validates: Requirements 7.6**
  
  - [ ]* 15.9 Write property test for proactive refinement application
    - **Property 36: Proactive refinement application**
    - **Validates: Requirements 7.7**
  
  - [ ]* 15.10 Write unit tests for Iterative Refinement
    - Test confidence evaluation with various result sets
    - Test adjustment generation for different deficiencies
    - Test refinement loop with mock queries
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_

- [x] 16. Implement Memory Systems
  - [x] 16.1 Create memory system base class
    - Define MemoryEntry schema with pattern, utility score, access count
    - Implement storage (SQLite or Redis)
    - Implement retrieval by similarity
    - Implement pruning by utility score
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.10_
  
  - [x] 16.2 Implement NL2Operator_Memory
    - Store query text, entities, operators, confidence
    - Query by text similarity
    - _Requirements: 16.1, 16.5_
  
  - [x] 16.3 Implement Query_Planner_Memory
    - Store operator DAG, predicted cost, actual cost, cache hits, rows processed
    - Query by DAG similarity
    - _Requirements: 16.2, 16.6_
  
  - [x] 16.4 Implement Refinement_Memory
    - Store original query, adjustments, confidence improvement
    - Query by query similarity
    - _Requirements: 16.3, 16.6_
  
  - [x] 16.5 Implement MCP_Server_Memory
    - Store operation, params, execution time, result size
    - Query by operation and params
    - _Requirements: 16.4, 16.8_
  
  - [ ]* 16.6 Write property test for NL2Operator memory storage
    - **Property 45: NL2Operator memory storage**
    - **Validates: Requirements 16.5**
  
  - [ ]* 16.7 Write property test for Query Planner memory storage
    - **Property 46: Query Planner memory storage**
    - **Validates: Requirements 16.6**
  
  - [ ]* 16.8 Write property test for memory pruning
    - **Property 47: Memory pruning**
    - **Validates: Requirements 16.10**
  
  - [ ]* 16.9 Write unit tests for Memory Systems
    - Test storage and retrieval for each memory type
    - Test similarity queries
    - Test pruning logic
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6, 16.8, 16.10_

- [x] 17. Implement FastAPI gateway and orchestration
  - [x] 17.1 Create FastAPI application
    - Set up FastAPI app with CORS middleware
    - Configure authentication middleware (JWT or API key)
    - Configure rate limiting middleware
    - _Requirements: 18.2_
  
  - [x] 17.2 Implement /api/query endpoint
    - Accept query, mode, context in request body
    - Orchestrate NL2Operator → Query Planner → Iterative Refiner → MCP Bridge → MCP Servers
    - Aggregate results from multiple MCP servers
    - Return response with data, visualizations, confidence, execution time
    - _Requirements: 1.1, 2.1, 7.1_
  
  - [x] 17.3 Implement error handling and retry logic
    - Wrap MCP server calls with retry logic (3 attempts, exponential backoff)
    - Implement circuit breaker for external dependencies
    - Return user-friendly error messages
    - Log errors to ELK Stack
    - _Requirements: 19.1, 19.2, 19.7_
  
  - [x] 17.4 Implement /api/validate-key endpoint
    - Accept API key and provider in request body
    - Validate key against provider API within 2 seconds
    - Return validation result with animated feedback
    - _Requirements: 9.1_
  
  - [ ]* 17.5 Write property test for simple query performance
    - **Property 40: Simple query performance**
    - **Validates: Requirements 15.1**
  
  - [ ]* 17.6 Write property test for medium query performance
    - **Property 41: Medium query performance**
    - **Validates: Requirements 15.2**
  
  - [ ]* 17.7 Write property test for complex query performance
    - **Property 42: Complex query performance**
    - **Validates: Requirements 15.3**
  
  - [ ]* 17.8 Write property test for timeout handling
    - **Property 44: Timeout handling**
    - **Validates: Requirements 15.8**
  
  - [ ]* 17.9 Write property test for retry with exponential backoff
    - **Property 55: Retry with exponential backoff**
    - **Validates: Requirements 19.1**
  
  - [ ]* 17.10 Write integration tests for end-to-end query flow
    - Test complete flow from NL query to visualization
    - Test caching integration
    - Test refinement integration
    - Test error handling
    - _Requirements: 1.1, 2.1, 6.1, 7.1, 19.1_

- [x] 18. Checkpoint - Ensure backend is fully functional
  - Ensure all tests pass, ask the user if questions arise.


- [x] 19. Implement frontend state management with Zustand
  - [x] 19.1 Create Zustand store for app state
    - Define AppState interface (apiKeys, selectedProvider, mode, messages, visualizations, preferences)
    - Implement actions for updating state
    - Persist API keys to encrypted local storage
    - _Requirements: 9.5, 18.4_
  
  - [x] 19.2 Implement API key management
    - Create actions for setting/getting API keys
    - Implement AES-256 encryption for local storage
    - Implement provider switching logic
    - _Requirements: 9.2, 9.5, 18.4_
  
  - [x] 19.3 Implement conversation state management
    - Create actions for adding messages
    - Track processing state
    - Store visualizations with messages
    - _Requirements: 10.1, 10.2_
  
  - [ ]* 19.4 Write property test for credential encryption
    - **Property 53: Credential encryption**
    - **Validates: Requirements 18.4**
  
  - [ ]* 19.5 Write unit tests for Zustand store
    - Test state updates
    - Test API key encryption/decryption
    - Test message management
    - _Requirements: 9.2, 9.5, 18.4_

- [x] 20. Implement API configuration UI component
  - [x] 20.1 Create API key input component
    - Build form with inputs for Gemini, GPT-4o, Claude API keys
    - Implement inline validation with animated feedback
    - Show success/error states with Framer Motion animations
    - _Requirements: 9.1, 9.3, 9.4_
  
  - [x] 20.2 Implement API key validation
    - Call /api/validate-key endpoint
    - Display validation result within 2 seconds
    - Show troubleshooting guidance on failure
    - _Requirements: 9.1, 9.4_
  
  - [x] 20.3 Implement provider selection
    - Create dropdown for selecting active provider
    - Update Zustand store on selection
    - _Requirements: 9.8_
  
  - [ ]* 20.4 Write property test for API key validation timing
    - **Property 54: API key validation timing**
    - **Validates: Requirements 9.1**
  
  - [ ]* 20.5 Write unit tests for API configuration component
    - Test form submission
    - Test validation feedback
    - Test provider switching
    - _Requirements: 9.1, 9.3, 9.4, 9.8_

- [x] 21. Implement chat interface UI component
  - [x] 21.1 Create message bubble components
    - Build user message bubble (right-aligned)
    - Build assistant message bubble (left-aligned)
    - Support markdown formatting
    - Add timestamp on hover
    - _Requirements: 10.1, 10.2, 10.6, 10.7_
  
  - [x] 21.2 Implement typing indicator
    - Create animated typing indicator component
    - Show during query processing
    - _Requirements: 10.3_
  
  - [x] 21.3 Implement visualization previews
    - Display inline thumbnail previews in messages
    - Implement click to expand with smooth animation
    - _Requirements: 10.4, 10.5_
  
  - [x] 21.4 Implement message input
    - Create text input with send button
    - Handle Enter key submission
    - Clear input after sending
    - _Requirements: 10.1_
  
  - [x] 21.5 Implement auto-scroll
    - Scroll to latest message when new content appears
    - Smooth scroll animation
    - _Requirements: 10.9_
  
  - [ ]* 21.6 Write unit tests for chat interface
    - Test message rendering
    - Test input submission
    - Test auto-scroll behavior
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.9_

- [x] 22. Implement animation system with Framer Motion
  - [x] 22.1 Implement micro-animations
    - Create hover animations for interactive elements (<100ms)
    - Create focus animations for inputs
    - Create loading animations for buttons
    - _Requirements: 11.1, 11.4_
  
  - [x] 22.2 Implement macro-animations
    - Create view transition animations (<300ms)
    - Create visualization render animations (fade-in, scale)
    - _Requirements: 11.2, 11.5, 11.6_
  
  - [x] 22.3 Implement singleton animations
    - Create onboarding animation sequence
    - Create first-time experience animations
    - _Requirements: 11.3_
  
  - [x] 22.4 Implement accessibility support
    - Respect prefers-reduced-motion setting
    - Disable non-essential animations when requested
    - Maintain functional transitions without motion
    - _Requirements: 11.7, 11.8_
  
  - [ ]* 22.5 Write unit tests for animation system
    - Test animation timing
    - Test reduced-motion support
    - Test frame rate performance
    - _Requirements: 11.1, 11.2, 11.3, 11.7, 11.8, 11.10_

- [x] 23. Implement UI mode switching (Explorer/Power)
  - [x] 23.1 Create mode toggle component
    - Build toggle switch for Explorer/Power modes
    - Animate mode transitions
    - Persist mode preference to Zustand store
    - _Requirements: 8.1, 8.2, 8.3, 8.7_
  
  - [x] 23.2 Implement Explorer mode UI
    - Hide technical details (execution plans, cost metrics)
    - Show simplified, guided interactions
    - Display suggested follow-up questions
    - _Requirements: 8.1, 8.4, 8.8_
  
  - [x] 23.3 Implement Power mode UI
    - Display semantic operator DAG visualization
    - Show execution costs and metrics
    - Allow manual query plan editing
    - _Requirements: 8.2, 8.5, 8.6_
  
  - [ ]* 23.4 Write unit tests for mode switching
    - Test mode toggle
    - Test UI differences between modes
    - Test preference persistence
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8_

- [x] 24. Implement visualization rendering components
  - [x] 24.1 Create Leaflet map component
    - Render trajectory maps with float paths
    - Add markers and popups
    - Support zoom and pan
    - _Requirements: 12.1, 12.8_
  
  - [x] 24.2 Create Plotly chart component
    - Render Hovmöller diagrams (contour plots)
    - Render vertical profile comparisons (line charts)
    - Render heatmaps
    - Support interactive hover and zoom
    - _Requirements: 12.2, 12.3, 12.4, 12.7_
  
  - [x] 24.3 Create Recharts dashboard component
    - Render time series charts
    - Render QC dashboards
    - Support responsive layouts
    - _Requirements: 12.5, 12.6, 12.7_
  
  - [x] 24.4 Implement visualization export
    - Export as PNG using html2canvas
    - Export as SVG using native browser APIs
    - Export as interactive HTML
    - _Requirements: 12.10_
  
  - [ ]* 24.5 Write unit tests for visualization components
    - Test rendering with sample data
    - Test export functionality
    - Test responsive behavior
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.8, 12.10_

- [x] 25. Implement data ingestion pipeline
  - [x] 25.1 Create ARGO NetCDF parser
    - Download NetCDF files from GDAC servers
    - Parse profiles, measurements, and metadata using netCDF4 library
    - Validate data against ARGO quality control standards
    - _Requirements: 21.1, 21.2, 21.3_
  
  - [x] 25.2 Implement bulk ingestion
    - Process multiple files in parallel
    - Handle duplicate profiles (update instead of insert)
    - Achieve 1000 profiles/minute throughput
    - _Requirements: 21.4, 21.5_
  
  - [x] 25.3 Implement error handling for ingestion
    - Log errors and continue with remaining files
    - Skip invalid profiles
    - _Requirements: 21.6_
  
  - [x] 25.4 Implement file_index updates
    - Update file_index table with spatial/temporal bounds
    - Store metadata in JSONB column
    - _Requirements: 21.7_
  
  - [x] 25.5 Implement cache invalidation on ingestion
    - Identify affected cache entries by spatial/temporal overlap
    - Invalidate cache entries via CachingServer
    - _Requirements: 21.8_
  
  - [ ]* 25.6 Write property test for duplicate profile handling
    - **Property 57: Duplicate profile handling**
    - **Validates: Requirements 21.4**
  
  - [ ]* 25.7 Write property test for ingestion throughput
    - **Property 58: Ingestion throughput**
    - **Validates: Requirements 21.5**
  
  - [ ]* 25.8 Write property test for cache invalidation on ingestion
    - **Property 59: Cache invalidation on ingestion**
    - **Validates: Requirements 21.8**
  
  - [ ]* 25.9 Write unit tests for data ingestion
    - Test NetCDF parsing with sample files
    - Test duplicate handling
    - Test error handling
    - Test cache invalidation
    - _Requirements: 21.1, 21.2, 21.3, 21.4, 21.5, 21.6, 21.7, 21.8_

- [x] 26. Checkpoint - Ensure frontend and ingestion work
  - Ensure all tests pass, ask the user if questions arise.

- [x] 27. Implement monitoring and observability
  - [x] 27.1 Set up Prometheus metrics
    - Expose /metrics endpoint in FastAPI
    - Track query latency (histogram)
    - Track cache hit rate (gauge)
    - Track error rates (counter)
    - _Requirements: 20.1, 20.5_
  
  - [x] 27.2 Set up ELK Stack logging
    - Configure Logstash to collect logs from all components
    - Index logs in Elasticsearch
    - Create Kibana dashboards for log analysis
    - _Requirements: 20.2_
  
  - [x] 27.3 Create Grafana dashboards
    - Create dashboard for query performance metrics
    - Create dashboard for cache performance
    - Create dashboard for security events
    - _Requirements: 20.3_
  
  - [x] 27.4 Implement alerting
    - Configure alerts for query latency >95th percentile threshold
    - Configure alerts for error rate spikes
    - Configure alerts for security violations
    - _Requirements: 20.4_
  
  - [x] 27.5 Implement distributed tracing
    - Integrate OpenTelemetry for tracing
    - Trace requests across NL2Operator → Query Planner → MCP Bridge → MCP Servers
    - _Requirements: 20.7_
  
  - [ ]* 27.6 Write unit tests for monitoring
    - Test metrics exposure
    - Test log formatting
    - Test trace propagation
    - _Requirements: 20.1, 20.2, 20.7_

- [x] 28. Implement deployment configuration
  - [x] 28.1 Create Docker images
    - Create Dockerfile for FastAPI backend
    - Create Dockerfile for React frontend (nginx)
    - Create Dockerfiles for each MCP server
    - _Requirements: 22.1_
  
  - [x] 28.2 Create Kubernetes manifests
    - Create Deployments for all components
    - Create Services for internal communication
    - Create Ingress for external access
    - Configure HorizontalPodAutoscaler for scaling
    - _Requirements: 22.2, 22.3_
  
  - [x] 28.3 Configure health checks
    - Implement /health endpoint in FastAPI
    - Configure Kubernetes liveness and readiness probes
    - _Requirements: 22.7_
  
  - [x] 28.4 Configure RabbitMQ for async tasks
    - Set up RabbitMQ queues for data ingestion
    - Implement worker processes for consuming tasks
    - _Requirements: 22.4_
  
  - [ ]* 28.5 Write unit tests for deployment configuration
    - Test health check endpoints
    - Test Docker image builds
    - Validate Kubernetes manifests
    - _Requirements: 22.1, 22.2, 22.7_

- [x] 29. Implement CI/CD pipeline
  - [x] 29.1 Create GitHub Actions workflow
    - Run linters (pylint, black, eslint, prettier)
    - Run unit tests with coverage reporting
    - Run property-based tests (100 iterations each)
    - Run integration tests
    - Build Docker images
    - Run security scans (Snyk, Trivy)
    - Deploy to staging on success
    - _Requirements: 23.8, 23.9_
  
  - [ ]* 29.2 Write unit tests for CI/CD
    - Test workflow configuration
    - Test deployment scripts
    - _Requirements: 23.8_

- [x] 30. Create documentation
  - [x] 30.1 Create API documentation
    - Generate OpenAPI 3.0 spec from FastAPI
    - Document all MCP server endpoints
    - Include request/response examples
    - _Requirements: 24.1_
  
  - [x] 30.2 Create architecture documentation
    - Create architecture diagrams (Mermaid)
    - Document component interactions
    - Document data flow
    - _Requirements: 24.2_
  
  - [x] 30.3 Create user guides
    - Write guide for Explorer mode
    - Write guide for Power mode
    - Include example queries
    - _Requirements: 24.3, 24.4_
  
  - [x] 30.4 Create deployment guides
    - Write Docker deployment guide
    - Write Kubernetes deployment guide
    - Include configuration examples
    - _Requirements: 24.5_
  
  - [x] 30.5 Create developer guides
    - Write guide for extending MCP servers
    - Write guide for adding new visualization types
    - Include code examples
    - _Requirements: 24.6_

- [x] 31. Final integration and testing
  - [x] 31.1 Run end-to-end integration tests
    - Test complete workflows with real data
    - Test all visualization types
    - Test error scenarios
    - _Requirements: 23.5_
  
  - [x] 31.2 Run load tests
    - Simulate 100 concurrent users with Locust
    - Verify performance targets met
    - Verify cache hit rate >70%
    - _Requirements: 23.7_
  
  - [x] 31.3 Verify code coverage
    - Backend: >80% coverage
    - Frontend: >70% coverage
    - _Requirements: 23.1, 23.2_
  
  - [ ]* 31.4 Write property test for dashboard generation performance
    - **Property 43: Dashboard generation performance**
    - **Validates: Requirements 15.4**

- [x] 32. Final checkpoint - System ready for deployment
  - Ensure all tests pass, verify documentation is complete, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional property-based and unit tests that can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at major milestones
- Property tests validate universal correctness properties with 100+ iterations
- Unit tests validate specific examples and edge cases
- Integration tests validate complete workflows across components
