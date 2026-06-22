-- Snapshot metadata for service-managed VMs

CREATE TABLE vm_snapshots (
  vm_name VARCHAR(255) NOT NULL,
  snapshot_id VARCHAR(255) NOT NULL,
  metadata JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (vm_name, snapshot_id)
);

CREATE INDEX idx_vm_snapshots_vm_name_created_at ON vm_snapshots(vm_name, created_at DESC);

CREATE TRIGGER update_vm_snapshots_updated_at
BEFORE UPDATE ON vm_snapshots
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();
