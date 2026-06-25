# Homelab VM Provisioner - Job Queue

RabbitMQ-based job queue infrastructure for async VM provisioning.

## Overview

This subproject manages RabbitMQ setup, configuration, and lifecycle for the VM provisioner backend. It handles:

- RabbitMQ installation (Docker and non-Docker modes)
- RabbitMQ service lifecycle (start/stop)
- Vhost, exchange, queue, and binding provisioning
- User and permission management
- Credential isolation (admin/API/worker)

## Quick Start

```bash
# Setup RabbitMQ (install and configure)
./setup                    # Non-Docker mode (install RabbitMQ natively)
./setup --docker           # Docker mode (use RabbitMQ container)
./setup --skip-system-packages  # Skip package installation (assumes RabbitMQ is installed)

# Provision RabbitMQ topology (vhost, users, exchange, queues)
./build

# Start RabbitMQ
./start                    # Docker or non-Docker based on QUEUE_MODE
./start --docker           # Force Docker mode

# Stop RabbitMQ
./stop

# Test/verify RabbitMQ configuration
./test

# Clean up (remove containers, volumes in Docker mode)
./scripts/clean.sh
```

## Architecture

### RabbitMQ Topology

```
vhost: provisioner
exchange: provisioner.jobs (topic)
routing key: host.<HOST_ID>
queue: provisioner.worker.<HOST_ID>
binding: queue → exchange via routing key
```

**Example for HOST_ID=local:**
- Routing key: `host.local`
- Queue: `provisioner.worker.local`
- Messages published with routing key `host.local` are delivered to `provisioner.worker.local`

### Credential Model

Three separate credential groups:

1. **Admin credentials** (`QUEUE_ADMIN_USER`, `QUEUE_ADMIN_PASSWORD`)
   - Used by setup/build scripts to bootstrap RabbitMQ
   - Create vhosts, users, exchanges, queues, bindings, permissions
   - Not exposed to API or worker

2. **API publisher credentials** (`QUEUE_API_USER`, `QUEUE_API_PASSWORD`)
   - Used by API to publish job messages
   - Write-only access to exchange
   - Separate from admin for security

3. **Worker consumer credentials** (`WORKER_QUEUE_USER`, `WORKER_QUEUE_PASSWORD`)
   - Used by worker to consume jobs from queue
   - Read-only access to specific queue
   - One user per HOST_ID for isolation

### Connection Construction

No URL-style RabbitMQ env vars. Connections are built from component env vars:

**API (publisher):**
```javascript
const url = `amqp://${QUEUE_API_USER}:${QUEUE_API_PASSWORD}@${QUEUE_HOST}:${QUEUE_PORT}/${QUEUE_VHOST}`;
```

**Worker (consumer):**
```python
url = f"amqp://{WORKER_QUEUE_USER}:{WORKER_QUEUE_PASSWORD}@{WORKER_QUEUE_HOST}:{WORKER_QUEUE_PORT}/{WORKER_QUEUE_VHOST}"
```

**Queue scripts (admin):**
```bash
url="amqp://${QUEUE_ADMIN_USER}:${QUEUE_ADMIN_PASSWORD}@${QUEUE_HOST}:${QUEUE_PORT}/${QUEUE_VHOST}"
```

## Modes

### Docker Mode

- RabbitMQ runs in a Docker container
- Application port exposed on `QUEUE_PORT` (default: 3334)
- Management UI exposed on `QUEUE_MGMT_PORT` (default: 13334)
- Data persisted in Docker volume
- No native RabbitMQ installation required

```bash
cp .env.example .env
# Edit .env: set QUEUE_MODE=docker
./setup --docker
./build
./start
```

### Non-Docker Mode

- RabbitMQ runs as a native system service
- Installs RabbitMQ and dependencies via system package manager
- Supports multiple distros (Debian/Ubuntu, RHEL/Fedora, Arch, etc.)
- Service managed via systemd

```bash
cp .env.example .env
# Edit .env: set QUEUE_MODE=non-docker
./setup
./build
./start
```

## Scripts

### `./setup [--docker] [--skip-system-packages]`

Prepare RabbitMQ environment.

- Load and validate environment variables
- Install RabbitMQ (unless `--skip-system-packages`)
- Enable RabbitMQ management plugin
- In Docker mode, pull RabbitMQ image

### `./build`

Provision RabbitMQ topology (idempotent).

- Create vhost
- Create admin/API/worker users
- Create exchange
- Create worker queue (one per HOST_ID)
- Bind queue to exchange
- Configure permissions

**Note:** Worker credentials must be pre-defined in `.env`. The build script uses those exact values when creating the RabbitMQ user. It does not generate credentials.

### `./start [--docker]`

Start RabbitMQ service.

- Docker mode: Start container, wait for readiness
- Non-Docker mode: Start systemd service
- Verify RabbitMQ is reachable before returning

### `./stop`

Stop RabbitMQ service.

- Docker mode: Stop container (preserves data)
- Non-Docker mode: Stop systemd service

### `./test`

Verify RabbitMQ configuration.

- Check RabbitMQ is reachable
- Verify vhost exists
- Verify exchange exists
- Verify queue exists
- Verify binding exists

### `./scripts/clean.sh`

Clean up RabbitMQ resources (destructive).

- Docker mode: Remove container and volume
- Non-Docker mode: Prompt before removing data

**Warning:** This deletes queue data and messages.

## Environment Variables

See [.env.example](.env.example) for full documentation.

**Required:**
- `QUEUE_MODE` - docker or non-docker
- `QUEUE_HOST` - RabbitMQ host
- `QUEUE_PORT` - RabbitMQ port (default: 3334)
- `QUEUE_ADMIN_USER` - Admin username
- `QUEUE_ADMIN_PASSWORD` - Admin password
- `QUEUE_API_USER` - API publisher username
- `QUEUE_API_PASSWORD` - API publisher password
- `WORKER_QUEUE_USER` - Worker consumer username
- `WORKER_QUEUE_PASSWORD` - Worker consumer password
- `HOST_ID` - Host identifier for queue naming

**Optional:**
- `SKIP_SYSTEM_PACKAGES` - Skip package installation (default: false)

## Integration

### API Integration

The API uses queue credentials to publish job messages:

```javascript
import { createRabbitMqPublisher } from './rabbitmq-publisher.js';

const publisher = await createRabbitMqPublisher({
  host: process.env.QUEUE_HOST,
  port: process.env.QUEUE_PORT,
  vhost: process.env.QUEUE_VHOST,
  user: process.env.QUEUE_API_USER,
  password: process.env.QUEUE_API_PASSWORD,
  exchange: process.env.QUEUE_EXCHANGE,
});

await publisher.publishJob({
  job_id: '123',
  job_type: 'vm.create',
  target_host_id: 'local',
});
```

### Worker Integration

The worker uses queue credentials to consume jobs:

```python
from hlvmp_worker.rabbitmq_consumer import RabbitMqConsumer

consumer = RabbitMqConsumer(
    host=os.environ['WORKER_QUEUE_HOST'],
    port=int(os.environ['WORKER_QUEUE_PORT']),
    vhost=os.environ['WORKER_QUEUE_VHOST'],
    user=os.environ['WORKER_QUEUE_USER'],
    password=os.environ['WORKER_QUEUE_PASSWORD'],
    queue=os.environ['WORKER_QUEUE_NAME'],
)

consumer.consume(callback=process_job)
```

## Message Format

RabbitMQ messages are small and reference durable job state:

```json
{
  "job_id": "123",
  "job_type": "vm.create",
  "target_host_id": "local"
}
```

The worker fetches full job context from the API using `job_id`.

## Testing

```bash
# Run queue subproject tests
npm test

# Test Docker mode
QUEUE_MODE=docker npm test

# Test non-Docker mode
QUEUE_MODE=non-docker npm test
```

## Troubleshooting

### RabbitMQ not starting

```bash
# Check RabbitMQ logs (Docker)
docker logs hlvmp-rabbitmq

# Check RabbitMQ logs (non-Docker)
sudo journalctl -u rabbitmq-server -f

# Verify port is not in use
sudo lsof -i :3334
```

### Permission errors

```bash
# Verify user permissions via management API
curl -u admin:password http://localhost:13334/api/users/provisioner_api

# Rebuild permissions
./build
```

### Connection refused

```bash
# Verify RabbitMQ is listening on correct port
sudo netstat -tlnp | grep 3334

# Verify firewall allows port 3334
sudo iptables -L -n | grep 3334
```

## Architecture Diagram

```
                   RabbitMQ (port 3334)
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    Admin creds       API creds        Worker creds
         │                 │                 │
   setup/build        API publish      Worker consume
   scripts            (write-only)     (read-only)
         │                 │                 │
         └─────────────────┴─────────────────┘
                           │
                  provisioner.jobs
                      (exchange)
                           │
                  host.local (routing key)
                           │
              provisioner.worker.local
                      (queue)
```

## Port Configuration

**RabbitMQ application port:** 3334  
**RabbitMQ management UI:** 13334 (Docker mode only)

The application port 3334 must be consistent across:
- Queue subproject `.env`
- API `.env`
- Worker `.env`
- Root `.env`
- Docker Compose config
- Scripts
- Tests

## Dependencies

**Docker mode:**
- Docker (user responsibility to install)

**Non-Docker mode:**
- RabbitMQ server (installed by setup script)
- rabbitmq-server package
- erlang runtime
- systemd (for service management)

## Related Documentation

- [API job-service.js](../homelab-vm-provisioner-api/src/job-service.js) - Job enqueueing
- [Worker consumer](../homelab-vm-provisioner-worker/hlvmp_worker/rabbitmq_consumer.py) - Job consumption
- [Database schema](../homelab-vm-provisioner-db/migrations/007_job_queue_rabbitmq.sql) - Job state

## License

See [LICENSE](LICENSE) file.
