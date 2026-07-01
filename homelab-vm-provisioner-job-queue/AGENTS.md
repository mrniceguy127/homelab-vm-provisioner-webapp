# Queue Subproject Agents

This document describes available agents for the homelab-vm-provisioner-job-queue subproject.

## Overview

The job queue subproject is strictly for RabbitMQ infrastructure:
- RabbitMQ installation and configuration
- Service lifecycle management (start/stop)
- Topology provisioning (vhost, users, exchange, queues, bindings)
- Credential management

**This subproject does NOT contain job processing logic.** The worker handles job consumption.

## Quick Reference

**Setup and start:**
```bash
./setup                    # Non-Docker mode
./setup --docker           # Docker mode
./build                    # Provision RabbitMQ topology
./start                    # Start RabbitMQ
```

**Verification:**
```bash
./test                     # Verify configuration
```

**Cleanup:**
```bash
./stop                     # Stop RabbitMQ
./scripts/clean.sh         # Remove data (destructive)
```

## Environment Variables

See [.env.example](.env.example) for full documentation.

**Required:**
- `QUEUE_MODE` - docker or non-docker
- `QUEUE_HOST`, `QUEUE_PORT` - RabbitMQ connection
- `QUEUE_VHOST`, `QUEUE_EXCHANGE` - Topology
- `QUEUE_ADMIN_USER`, `QUEUE_ADMIN_PASSWORD` - Admin credentials
- `QUEUE_API_USER`, `QUEUE_API_PASSWORD` - API publisher credentials
- `QUEUE_USER`, `QUEUE_PASSWORD` - Worker consumer credentials
- `HOST_ID` - Host identifier for queue naming

## Common Tasks

### Add support for a new host

1. Update `.env` with new `HOST_ID`
2. Add new worker credentials to `.env`
3. Run `./build` to provision new queue
4. Configure API and worker with matching credentials

### Change RabbitMQ credentials

1. Update `.env` with new credentials
2. Run `./build` to update users
3. Restart API and worker with new credentials

### Switch between Docker and non-Docker

```bash
# Switch to Docker
./stop
# Edit .env: set QUEUE_MODE=docker
./setup --docker
./build
./start

# Switch to non-Docker
./stop
# Edit .env: set QUEUE_MODE=non-docker
./setup
./build
./start
```

### Troubleshooting

**RabbitMQ not starting:**
```bash
# Check logs (Docker)
docker logs hlvmp-rabbitmq

# Check logs (non-Docker)
sudo journalctl -u rabbitmq-server -f
```

**Permission errors:**
```bash
# Rebuild permissions
./build
```

**Port conflicts:**
```bash
# Check what's using port 3334
sudo lsof -i :3334

# Change port in .env and rebuild
```

## Related Documentation

- [README.md](README.md) - Full documentation
- [API integration](../homelab-vm-provisioner-api/src/rabbitmq-publisher.js)
- [Worker integration](../homelab-vm-provisioner-worker/hlvmp_worker/rabbitmq_consumer.py)

## Architecture

The queue subproject is RabbitMQ infrastructure only:

```
Queue Subproject
    ├── Setup/install RabbitMQ
    ├── Start/stop RabbitMQ service
    ├── Provision topology (vhost, exchange, queues, bindings)
    └── Manage credentials (admin, API, worker)

Job Processing (NOT in queue subproject)
    ├── API: Publish job messages
    └── Worker: Consume and process jobs
```

Do NOT add job processing logic to this subproject.
