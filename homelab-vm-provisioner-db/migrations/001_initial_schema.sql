-- Initial schema for async job queue

-- Jobs table: Core job tracking
CREATE TABLE jobs (
  id BIGSERIAL PRIMARY KEY,
  type VARCHAR(100) NOT NULL,
  status VARCHAR(50) NOT NULL DEFAULT 'queued',
  target_host_id VARCHAR(255) NOT NULL,
  target_vm_id VARCHAR(255),
  payload JSONB NOT NULL DEFAULT '{}',
  result JSONB,
  error TEXT,
  claimed_by VARCHAR(255),
  claimed_at TIMESTAMPTZ,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  attempts INTEGER NOT NULL DEFAULT 0,
  max_attempts INTEGER NOT NULL DEFAULT 3,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  
  -- Constraints
  CONSTRAINT jobs_status_check CHECK (
    status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')
  ),
  CONSTRAINT jobs_attempts_check CHECK (attempts >= 0),
  CONSTRAINT jobs_max_attempts_check CHECK (max_attempts > 0)
);

-- Job events table: Event log per job
CREATE TABLE job_events (
  id BIGSERIAL PRIMARY KEY,
  job_id BIGINT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  level VARCHAR(50) NOT NULL,
  message TEXT NOT NULL,
  metadata JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  
  -- Constraints
  CONSTRAINT job_events_level_check CHECK (
    level IN ('debug', 'info', 'warning', 'error')
  )
);

-- Resource locks table: Prevent concurrent operations on resources
CREATE TABLE resource_locks (
  lock_key VARCHAR(255) PRIMARY KEY,
  job_id BIGINT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  worker_id VARCHAR(255) NOT NULL,
  acquired_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL
);

-- Indexes for efficient queries
CREATE INDEX idx_jobs_status_created_at ON jobs(status, created_at);
CREATE INDEX idx_jobs_target_host_id_status ON jobs(target_host_id, status);
CREATE INDEX idx_jobs_target_vm_id ON jobs(target_vm_id) WHERE target_vm_id IS NOT NULL;
CREATE INDEX idx_jobs_claimed_by ON jobs(claimed_by) WHERE claimed_by IS NOT NULL;
CREATE INDEX idx_job_events_job_id_created_at ON job_events(job_id, created_at);
CREATE INDEX idx_resource_locks_expires_at ON resource_locks(expires_at);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at on jobs table
CREATE TRIGGER update_jobs_updated_at
BEFORE UPDATE ON jobs
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE jobs IS 'Async provisioning jobs with status tracking';
COMMENT ON TABLE job_events IS 'Event log per job for debugging and audit';
COMMENT ON TABLE resource_locks IS 'Per-resource locks to prevent concurrent operations';

COMMENT ON COLUMN jobs.type IS 'Job type (e.g., provision_vm, destroy_vm)';
COMMENT ON COLUMN jobs.status IS 'Current job status: queued, running, succeeded, failed, cancelled';
COMMENT ON COLUMN jobs.target_host_id IS 'Host where the job should run';
COMMENT ON COLUMN jobs.target_vm_id IS 'Target VM identifier (nullable for host-level jobs)';
COMMENT ON COLUMN jobs.payload IS 'Job-specific input parameters';
COMMENT ON COLUMN jobs.result IS 'Job result data (set on success)';
COMMENT ON COLUMN jobs.error IS 'Error message (set on failure)';
COMMENT ON COLUMN jobs.claimed_by IS 'Worker ID that claimed this job';
COMMENT ON COLUMN jobs.claimed_at IS 'When the job was claimed';
COMMENT ON COLUMN jobs.started_at IS 'When the job started executing';
COMMENT ON COLUMN jobs.finished_at IS 'When the job completed (success or failure)';
COMMENT ON COLUMN jobs.attempts IS 'Number of execution attempts';
COMMENT ON COLUMN jobs.max_attempts IS 'Maximum allowed attempts before giving up';
