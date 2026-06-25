-- Migration 007: Add RabbitMQ job queue integration fields
-- Adds fields for RabbitMQ message tracking, heartbeat, and cleanup context

-- Add queue_message_id for RabbitMQ message correlation
ALTER TABLE jobs ADD COLUMN queue_message_id VARCHAR(255);

-- Add last_heartbeat_at for worker health tracking
ALTER TABLE jobs ADD COLUMN last_heartbeat_at TIMESTAMPTZ;

-- Add cleanup_context for storing cleanup metadata
ALTER TABLE jobs ADD COLUMN cleanup_context JSONB;

-- Add publish_failed status to existing constraint
ALTER TABLE jobs DROP CONSTRAINT jobs_status_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_status_check CHECK (
  status IN (
    'queued',
    'published',
    'running',
    'succeeded',
    'failed',
    'cancelled',
    'cleanup_required',
    'retryable_failed',
    'publish_failed'
  )
);

-- Add index for queue message ID lookups
CREATE INDEX idx_jobs_queue_message_id ON jobs(queue_message_id) WHERE queue_message_id IS NOT NULL;

-- Add index for heartbeat monitoring
CREATE INDEX idx_jobs_last_heartbeat ON jobs(last_heartbeat_at) WHERE last_heartbeat_at IS NOT NULL;

-- Comments
COMMENT ON COLUMN jobs.queue_message_id IS 'RabbitMQ message ID for correlation';
COMMENT ON COLUMN jobs.last_heartbeat_at IS 'Timestamp of last worker heartbeat';
COMMENT ON COLUMN jobs.cleanup_context IS 'Metadata for cleanup operations (e.g., resource IDs to clean)';
