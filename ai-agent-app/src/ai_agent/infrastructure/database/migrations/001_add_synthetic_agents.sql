-- Migration: Add synthetic agent system tables
-- Version: 001
-- Description: Create tables for transcript data, agent management, and evaluation results

-- Transcript metadata table
CREATE TABLE IF NOT EXISTS transcript_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(255) NOT NULL,
    source VARCHAR(50) NOT NULL,
    stakeholder_group VARCHAR(50) NOT NULL,
    interview_date TIMESTAMP,
    participants TEXT[],
    total_segments INTEGER DEFAULT 0,
    file_size_bytes INTEGER DEFAULT 0,
    processing_status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Transcript segments table
CREATE TABLE IF NOT EXISTS transcript_segments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transcript_id UUID NOT NULL REFERENCES transcript_metadata(id) ON DELETE CASCADE,
    speaker_name VARCHAR(255) NOT NULL,
    speaker_title VARCHAR(255),
    content TEXT NOT NULL,
    start_time FLOAT,
    end_time FLOAT,
    segment_index INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Topic tags table
CREATE TABLE IF NOT EXISTS topic_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    category VARCHAR(100),
    confidence_score FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Segment topic mappings
CREATE TABLE IF NOT EXISTS segment_topic_mappings (
    segment_id UUID NOT NULL REFERENCES transcript_segments(id) ON DELETE CASCADE,
    topic_id UUID NOT NULL REFERENCES topic_tags(id) ON DELETE CASCADE,
    relevance_score FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (segment_id, topic_id)
);

-- Governance models table
CREATE TABLE IF NOT EXISTS governance_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    model_type VARCHAR(100) NOT NULL,
    key_features TEXT[],
    proposed_by VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Evaluation results table
CREATE TABLE IF NOT EXISTS evaluation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id UUID NOT NULL REFERENCES governance_models(id) ON DELETE CASCADE,
    overall_score FLOAT NOT NULL,
    overall_assessment TEXT,
    evaluation_status VARCHAR(50) NOT NULL,
    key_risks TEXT[],
    key_benefits TEXT[],
    recommendations TEXT[],
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Factor scores table
CREATE TABLE IF NOT EXISTS factor_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evaluation_id UUID NOT NULL REFERENCES evaluation_results(id) ON DELETE CASCADE,
    factor_name VARCHAR(100) NOT NULL,
    score INTEGER NOT NULL CHECK (score >= 1 AND score <= 5),
    rationale TEXT NOT NULL,
    evidence_citations TEXT[],
    confidence_level VARCHAR(20) NOT NULL,
    persona_perspective VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agent sessions table
CREATE TABLE IF NOT EXISTS agent_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type VARCHAR(50) NOT NULL,
    session_id UUID NOT NULL,
    user_id VARCHAR(255),
    status VARCHAR(50) NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agent conversations table
CREATE TABLE IF NOT EXISTS agent_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES agent_sessions(session_id) ON DELETE CASCADE,
    agent_type VARCHAR(50) NOT NULL,
    query TEXT NOT NULL,
    response TEXT NOT NULL,
    evidence_count INTEGER DEFAULT 0,
    processing_time_ms INTEGER DEFAULT 0,
    confidence_level VARCHAR(20),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_transcript_segments_content ON transcript_segments USING gin(to_tsvector('english', content));
CREATE INDEX IF NOT EXISTS idx_transcript_segments_speaker ON transcript_segments(speaker_name);
CREATE INDEX IF NOT EXISTS idx_transcript_segments_stakeholder ON transcript_segments(metadata->>'stakeholder_group');
CREATE INDEX IF NOT EXISTS idx_transcript_metadata_source ON transcript_metadata(source);
CREATE INDEX IF NOT EXISTS idx_transcript_metadata_stakeholder_group ON transcript_metadata(stakeholder_group);
CREATE INDEX IF NOT EXISTS idx_transcript_metadata_processing_status ON transcript_metadata(processing_status);

CREATE INDEX IF NOT EXISTS idx_evaluation_results_model_id ON evaluation_results(model_id);
CREATE INDEX IF NOT EXISTS idx_evaluation_results_status ON evaluation_results(evaluation_status);
CREATE INDEX IF NOT EXISTS idx_evaluation_results_created_at ON evaluation_results(created_at);

CREATE INDEX IF NOT EXISTS idx_factor_scores_evaluation_id ON factor_scores(evaluation_id);
CREATE INDEX IF NOT EXISTS idx_factor_scores_factor_name ON factor_scores(factor_name);
CREATE INDEX IF NOT EXISTS idx_factor_scores_score ON factor_scores(score);

CREATE INDEX IF NOT EXISTS idx_agent_sessions_agent_type ON agent_sessions(agent_type);
CREATE INDEX IF NOT EXISTS idx_agent_sessions_session_id ON agent_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_sessions_status ON agent_sessions(status);

CREATE INDEX IF NOT EXISTS idx_agent_conversations_session_id ON agent_conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_conversations_agent_type ON agent_conversations(agent_type);
CREATE INDEX IF NOT EXISTS idx_agent_conversations_created_at ON agent_conversations(created_at);

-- Create views for common queries
CREATE OR REPLACE VIEW transcript_summary AS
SELECT
    tm.id,
    tm.filename,
    tm.source,
    tm.stakeholder_group,
    tm.total_segments,
    tm.processing_status,
    COUNT(ts.id) as actual_segments,
    AVG(LENGTH(ts.content)) as avg_segment_length
FROM transcript_metadata tm
LEFT JOIN transcript_segments ts ON tm.id = ts.transcript_id
GROUP BY tm.id, tm.filename, tm.source, tm.stakeholder_group, tm.total_segments, tm.processing_status;

CREATE OR REPLACE VIEW evaluation_summary AS
SELECT
    gm.name as model_name,
    gm.model_type,
    er.overall_score,
    er.evaluation_status,
    er.created_at as evaluation_date,
    COUNT(fs.id) as factor_count,
    AVG(fs.score) as avg_factor_score
FROM governance_models gm
JOIN evaluation_results er ON gm.id = er.model_id
LEFT JOIN factor_scores fs ON er.id = fs.evaluation_id
GROUP BY gm.id, gm.name, gm.model_type, er.overall_score, er.evaluation_status, er.created_at;

-- Insert default topic tags
INSERT INTO topic_tags (name, description, category, confidence_score) VALUES
('commercial sustainability', 'Commercial viability and sustainability aspects', 'business', 0.9),
('governance', 'Governance and regulatory aspects', 'policy', 0.9),
('cost considerations', 'Cost and financial considerations', 'financial', 0.9),
('interoperability', 'Interoperability and integration aspects', 'technical', 0.9),
('technical feasibility', 'Technical implementation feasibility', 'technical', 0.9)
ON CONFLICT (name) DO NOTHING;
