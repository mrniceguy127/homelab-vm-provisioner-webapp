-- Domain state for users, network groups, VM definitions, and runtime state

CREATE TABLE users (
  id VARCHAR(255) PRIMARY KEY,
  username VARCHAR(255) NOT NULL,
  role VARCHAR(50) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT users_role_check CHECK (role IN ('admin', 'user'))
);

CREATE TABLE network_groups (
  id VARCHAR(255) PRIMARY KEY,
  owner_user_id VARCHAR(255) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  libvirt_network_name VARCHAR(255),
  bridge_name VARCHAR(255),
  subnet_cidr VARCHAR(64),
  gateway_ip VARCHAR(64),
  dhcp_start VARCHAR(64),
  dhcp_end VARCHAR(64),
  profile VARCHAR(50) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT network_groups_profile_check CHECK (profile IN ('private', 'nat', 'isolated_nat', 'bridged')),
  CONSTRAINT network_groups_owner_name_unique UNIQUE (owner_user_id, name)
);

CREATE TABLE vm_definitions (
  id BIGSERIAL PRIMARY KEY,
  vm_name VARCHAR(255) NOT NULL UNIQUE,
  owner_user_id VARCHAR(255),
  network_group_id VARCHAR(255),
  target_host_id VARCHAR(255) NOT NULL,
  config JSONB NOT NULL,
  ssh_public_key TEXT,
  setup_script TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT vm_definitions_owner_user_fk FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE SET NULL,
  CONSTRAINT vm_definitions_network_group_fk FOREIGN KEY (network_group_id) REFERENCES network_groups(id) ON DELETE SET NULL
);

CREATE TABLE vm_runtime_state (
  vm_name VARCHAR(255) PRIMARY KEY REFERENCES vm_definitions(vm_name) ON DELETE CASCADE,
  state JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_network_groups_owner_user_id ON network_groups(owner_user_id);
CREATE INDEX idx_vm_definitions_owner_user_id ON vm_definitions(owner_user_id);
CREATE INDEX idx_vm_definitions_network_group_id ON vm_definitions(network_group_id);
CREATE INDEX idx_vm_definitions_target_host_id ON vm_definitions(target_host_id);

CREATE TRIGGER update_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_network_groups_updated_at
BEFORE UPDATE ON network_groups
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_vm_definitions_updated_at
BEFORE UPDATE ON vm_definitions
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_vm_runtime_state_updated_at
BEFORE UPDATE ON vm_runtime_state
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();
