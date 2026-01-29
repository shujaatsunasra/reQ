-- FloatChat Database Schema
-- ARGO Oceanographic Data Analytics Platform
-- Migration 001: Initial Schema

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================
-- PROFILES TABLE
-- Core table for ARGO float profile data
-- ============================================
CREATE TABLE IF NOT EXISTS profiles (
    profile_id TEXT PRIMARY KEY,
    float_id TEXT NOT NULL,
    cycle_number INTEGER NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    geom GEOMETRY(Point, 4326) GENERATED ALWAYS AS (
        ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
    ) STORED,
    data_mode CHAR(1) NOT NULL CHECK (data_mode IN ('R', 'A', 'D')),
    direction CHAR(1) CHECK (direction IN ('A', 'D')),
    institution TEXT,
    project_name TEXT,
    platform_type TEXT,
    wmo_id TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_float_cycle UNIQUE (float_id, cycle_number)
);

-- Add comments
COMMENT ON TABLE profiles IS 'ARGO float vertical profile records';
COMMENT ON COLUMN profiles.profile_id IS 'Unique profile identifier (typically float_id_cycle)';
COMMENT ON COLUMN profiles.float_id IS 'ARGO float identifier';
COMMENT ON COLUMN profiles.cycle_number IS 'Cycle number of the measurement';
COMMENT ON COLUMN profiles.data_mode IS 'R=Real-time, A=Adjusted, D=Delayed-mode';
COMMENT ON COLUMN profiles.direction IS 'A=Ascending, D=Descending';

-- ============================================
-- PROFILE MEASUREMENTS TABLE
-- Depth-indexed measurements for each profile
-- ============================================
CREATE TABLE IF NOT EXISTS profile_measurements (
    measurement_id BIGSERIAL PRIMARY KEY,
    profile_id TEXT NOT NULL REFERENCES profiles(profile_id) ON DELETE CASCADE,
    level_index INTEGER NOT NULL,
    depth DOUBLE PRECISION NOT NULL,
    pressure DOUBLE PRECISION,
    temperature DOUBLE PRECISION,
    salinity DOUBLE PRECISION,
    oxygen DOUBLE PRECISION,
    chlorophyll DOUBLE PRECISION,
    
    -- Quality Control flags (ARGO standard: 1=good, 2=probably good, 3=probably bad, 4=bad, 8=interpolated, 9=missing)
    pres_qc CHAR(1) DEFAULT '0' CHECK (pres_qc IN ('0', '1', '2', '3', '4', '8', '9')),
    temp_qc CHAR(1) DEFAULT '0' CHECK (temp_qc IN ('0', '1', '2', '3', '4', '8', '9')),
    psal_qc CHAR(1) DEFAULT '0' CHECK (psal_qc IN ('0', '1', '2', '3', '4', '8', '9')),
    doxy_qc CHAR(1) DEFAULT '0' CHECK (doxy_qc IN ('0', '1', '2', '3', '4', '8', '9')),
    chla_qc CHAR(1) DEFAULT '0' CHECK (chla_qc IN ('0', '1', '2', '3', '4', '8', '9')),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_profile_level UNIQUE (profile_id, level_index)
);

COMMENT ON TABLE profile_measurements IS 'Depth-indexed measurements for each ARGO profile';
COMMENT ON COLUMN profile_measurements.level_index IS 'Vertical level index (0 = surface)';
COMMENT ON COLUMN profile_measurements.depth IS 'Depth in meters (positive downward)';
COMMENT ON COLUMN profile_measurements.pres_qc IS 'Pressure QC flag (ARGO standard)';

-- ============================================
-- FILE INDEX TABLE
-- Index of NetCDF files for data ingestion
-- ============================================
CREATE TABLE IF NOT EXISTS file_index (
    file_id SERIAL PRIMARY KEY,
    float_id TEXT NOT NULL,
    data_center TEXT,
    file_path TEXT NOT NULL UNIQUE,
    file_type TEXT CHECK (file_type IN ('core', 'bgc', 'synthetic', 'meta', 'tech', 'traj')),
    
    -- Time range
    time_start TIMESTAMPTZ,
    time_end TIMESTAMPTZ,
    
    -- Spatial bounds
    lat_min DOUBLE PRECISION,
    lat_max DOUBLE PRECISION,
    lon_min DOUBLE PRECISION,
    lon_max DOUBLE PRECISION,
    
    -- Depth range
    depth_min DOUBLE PRECISION,
    depth_max DOUBLE PRECISION,
    
    -- File metadata
    file_size_bytes BIGINT,
    num_profiles INTEGER,
    variables JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    
    -- Processing status
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'error')),
    last_processed_at TIMESTAMPTZ,
    error_message TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE file_index IS 'Index of ARGO NetCDF files for data ingestion';

-- ============================================
-- QUERY HISTORY TABLE
-- Track user queries for analytics and memory
-- ============================================
CREATE TABLE IF NOT EXISTS query_history (
    query_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT,
    user_id TEXT,
    
    -- Query details
    raw_query TEXT NOT NULL,
    parsed_intent JSONB,
    operators JSONB,
    
    -- Execution details
    execution_plan JSONB,
    execution_time_ms DOUBLE PRECISION,
    rows_returned INTEGER,
    cache_hit BOOLEAN DEFAULT FALSE,
    
    -- Results
    success BOOLEAN DEFAULT TRUE,
    confidence_score DOUBLE PRECISION,
    refinement_count INTEGER DEFAULT 0,
    error_message TEXT,
    
    -- Feedback
    user_rating INTEGER CHECK (user_rating >= 1 AND user_rating <= 5),
    user_feedback TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE query_history IS 'History of natural language queries for learning and analytics';

-- ============================================
-- MEMORY TABLES
-- For NL2Operator, Planner, MCP, and Refinement memory systems
-- ============================================

-- NL2Operator Memory: Stores parsing patterns
CREATE TABLE IF NOT EXISTS nl2op_memory (
    pattern_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_text TEXT NOT NULL,
    pattern_hash TEXT UNIQUE NOT NULL,
    entities JSONB NOT NULL,
    operators JSONB NOT NULL,
    success_count INTEGER DEFAULT 1,
    failure_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Planner Memory: Stores successful query plans
CREATE TABLE IF NOT EXISTS planner_memory (
    plan_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_signature TEXT NOT NULL,
    query_hash TEXT UNIQUE NOT NULL,
    execution_plan JSONB NOT NULL,
    avg_execution_time_ms DOUBLE PRECISION,
    success_rate DOUBLE PRECISION DEFAULT 1.0,
    use_count INTEGER DEFAULT 1,
    last_used_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- MCP Server Memory: Stores server-specific patterns
CREATE TABLE IF NOT EXISTS mcp_memory (
    memory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    server_type TEXT NOT NULL CHECK (server_type IN ('structured', 'metadata', 'profile', 'semantic', 'cache', 'visualization')),
    operation TEXT NOT NULL,
    parameters_hash TEXT NOT NULL,
    result_pattern JSONB,
    performance_metrics JSONB,
    success_count INTEGER DEFAULT 1,
    last_used_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_mcp_pattern UNIQUE (server_type, operation, parameters_hash)
);

-- Refinement Memory: Stores refinement strategies
CREATE TABLE IF NOT EXISTS refinement_memory (
    refinement_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    initial_query_pattern TEXT NOT NULL,
    refinement_strategy JSONB NOT NULL,
    confidence_improvement DOUBLE PRECISION,
    success_rate DOUBLE PRECISION DEFAULT 1.0,
    use_count INTEGER DEFAULT 1,
    last_used_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- INDEXES
-- Optimized for common query patterns
-- ============================================

-- Profiles indexes
CREATE INDEX IF NOT EXISTS idx_profiles_float_id ON profiles(float_id);
CREATE INDEX IF NOT EXISTS idx_profiles_timestamp ON profiles(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_profiles_geom ON profiles USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_profiles_data_mode ON profiles(data_mode);
CREATE INDEX IF NOT EXISTS idx_profiles_metadata ON profiles USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_profiles_float_timestamp ON profiles(float_id, timestamp DESC);

-- Profile measurements indexes
CREATE INDEX IF NOT EXISTS idx_measurements_profile_id ON profile_measurements(profile_id);
CREATE INDEX IF NOT EXISTS idx_measurements_depth ON profile_measurements(depth);
CREATE INDEX IF NOT EXISTS idx_measurements_profile_depth ON profile_measurements(profile_id, depth);

-- File index indexes
CREATE INDEX IF NOT EXISTS idx_file_index_float_id ON file_index(float_id);
CREATE INDEX IF NOT EXISTS idx_file_index_status ON file_index(status);
CREATE INDEX IF NOT EXISTS idx_file_index_time_range ON file_index(time_start, time_end);

-- Query history indexes
CREATE INDEX IF NOT EXISTS idx_query_history_session ON query_history(session_id);
CREATE INDEX IF NOT EXISTS idx_query_history_created ON query_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_query_history_success ON query_history(success);

-- Memory table indexes
CREATE INDEX IF NOT EXISTS idx_nl2op_memory_hash ON nl2op_memory(pattern_hash);
CREATE INDEX IF NOT EXISTS idx_planner_memory_hash ON planner_memory(query_hash);
CREATE INDEX IF NOT EXISTS idx_mcp_memory_server ON mcp_memory(server_type, operation);

-- ============================================
-- FUNCTIONS
-- Helper functions for common operations
-- ============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to tables with updated_at
CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_file_index_updated_at
    BEFORE UPDATE ON file_index
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to find profiles within a bounding box
CREATE OR REPLACE FUNCTION find_profiles_in_bbox(
    min_lon DOUBLE PRECISION,
    min_lat DOUBLE PRECISION,
    max_lon DOUBLE PRECISION,
    max_lat DOUBLE PRECISION,
    start_time TIMESTAMPTZ DEFAULT NULL,
    end_time TIMESTAMPTZ DEFAULT NULL
)
RETURNS SETOF profiles AS $$
BEGIN
    RETURN QUERY
    SELECT *
    FROM profiles
    WHERE ST_Within(
        geom,
        ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
    )
    AND (start_time IS NULL OR timestamp >= start_time)
    AND (end_time IS NULL OR timestamp <= end_time)
    ORDER BY timestamp DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to get profile with measurements
CREATE OR REPLACE FUNCTION get_profile_with_measurements(p_profile_id TEXT)
RETURNS TABLE (
    out_profile_id TEXT,
    out_float_id TEXT,
    out_cycle_number INTEGER,
    out_timestamp TIMESTAMPTZ,
    out_latitude DOUBLE PRECISION,
    out_longitude DOUBLE PRECISION,
    out_data_mode CHAR(1),
    out_level_index INTEGER,
    out_depth DOUBLE PRECISION,
    out_temperature DOUBLE PRECISION,
    out_salinity DOUBLE PRECISION,
    out_pressure DOUBLE PRECISION
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.profile_id,
        p.float_id,
        p.cycle_number,
        p.timestamp,
        p.latitude,
        p.longitude,
        p.data_mode,
        m.level_index,
        m.depth,
        m.temperature,
        m.salinity,
        m.pressure
    FROM profiles p
    LEFT JOIN profile_measurements m ON p.profile_id = m.profile_id
    WHERE p.profile_id = p_profile_id
    ORDER BY m.level_index;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- ROW LEVEL SECURITY (RLS)
-- Enable for multi-tenant scenarios
-- ============================================

-- Enable RLS on tables (disabled by default for development)
-- ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE profile_measurements ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE query_history ENABLE ROW LEVEL SECURITY;

-- ============================================
-- SAMPLE DATA (Optional - for testing)
-- ============================================
-- Uncomment to insert sample data

-- INSERT INTO profiles (profile_id, float_id, cycle_number, timestamp, latitude, longitude, data_mode)
-- VALUES 
--     ('4901556_001', '4901556', 1, '2024-01-15 10:30:00+00', 15.5, 68.2, 'R'),
--     ('4901556_002', '4901556', 2, '2024-01-25 14:45:00+00', 15.6, 68.3, 'R'),
--     ('4901557_001', '4901557', 1, '2024-01-20 08:15:00+00', 12.3, 72.1, 'A');
