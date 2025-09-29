-- Migration: Add synthetic agent system tables
-- Version: 001
-- Description: Create tables for transcript data, agent management, and evaluation results

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

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

-- Transcript segments table with vector embedding
CREATE TABLE IF NOT EXISTS transcript_segments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transcript_id UUID NOT NULL REFERENCES transcript_metadata(id) ON DELETE CASCADE,
    speaker_name VARCHAR(255) NOT NULL,
    speaker_title VARCHAR(255),
    content TEXT NOT NULL,
    embedding vector(384), -- all-MiniLM-L6-v2 dimension
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

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_transcript_segments_content ON transcript_segments USING gin(to_tsvector('english', content));
CREATE INDEX IF NOT EXISTS idx_transcript_segments_speaker ON transcript_segments(speaker_name);
CREATE INDEX IF NOT EXISTS idx_transcript_segments_stakeholder ON transcript_segments(metadata->>'stakeholder_group');
CREATE INDEX IF NOT EXISTS idx_transcript_metadata_source ON transcript_metadata(source);
CREATE INDEX IF NOT EXISTS idx_transcript_metadata_stakeholder_group ON transcript_metadata(stakeholder_group);
CREATE INDEX IF NOT EXISTS idx_transcript_metadata_processing_status ON transcript_metadata(processing_status);

-- Vector similarity index for fast semantic search
CREATE INDEX IF NOT EXISTS idx_transcript_segments_embedding ON transcript_segments
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Insert default topic tags
INSERT INTO topic_tags (name, description, category, confidence_score) VALUES
('commercial sustainability', 'Commercial viability and sustainability aspects', 'business', 0.9),
('governance', 'Governance and regulatory aspects', 'policy', 0.9),
('cost considerations', 'Cost and financial considerations', 'financial', 0.9),
('interoperability', 'Interoperability and integration aspects', 'technical', 0.9),
('technical feasibility', 'Technical implementation feasibility', 'technical', 0.9)
ON CONFLICT (name) DO NOTHING;
