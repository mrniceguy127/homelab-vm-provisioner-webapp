#!/usr/bin/env bash
# Clean script for homelab-vm-provisioner-job-queue
#
# WARNING: This is a destructive operation that removes RabbitMQ data
#
# Usage: ./scripts/clean.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QUEUE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$QUEUE_DIR"

# Source component .env
if [[ -f "$QUEUE_DIR/.env" ]]; then
    set -a
    source "$QUEUE_DIR/.env"
    set +a
fi

# Defaults
QUEUE_MODE="${QUEUE_MODE:-docker}"

log() {
    printf '==> %s\n' "$*"
}

warn() {
    printf 'WARNING: %s\n' "$*" >&2
}

run_sudo() {
    if [[ "${EUID}" -eq 0 ]]; then
        "$@"
    else
        sudo "$@"
    fi
}

docker_container_exists() {
    docker inspect "$1" >/dev/null 2>&1
}

log "Queue clean mode: $QUEUE_MODE"

if [[ "$QUEUE_MODE" == "docker" ]]; then
    CONTAINER_NAME="hlvmp-rabbitmq"
    VOLUME_NAME="hlvmp-rabbitmq-data"
    
    warn "This will remove the RabbitMQ container and all queue data"
    
    if [[ -t 0 ]]; then
        read -p "Continue? [y/N] " -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log "Aborted"
            exit 0
        fi
    fi
    
    if docker_container_exists "$CONTAINER_NAME"; then
        log "Removing RabbitMQ container"
        docker rm -f "$CONTAINER_NAME" || true
    fi
    
    if docker volume inspect "$VOLUME_NAME" >/dev/null 2>&1; then
        log "Removing RabbitMQ data volume"
        docker volume rm "$VOLUME_NAME" || true
    fi
    
    log "Docker resources cleaned"
    
elif [[ "$QUEUE_MODE" == "non-docker" ]]; then
    warn "This will remove RabbitMQ data directory"
    warn "RabbitMQ must be stopped first (./stop)"
    
    if [[ -t 0 ]]; then
        read -p "Continue? [y/N] " -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log "Aborted"
            exit 0
        fi
    fi
    
    if [[ -d /var/lib/rabbitmq ]]; then
        log "Removing RabbitMQ data directory"
        run_sudo rm -rf /var/lib/rabbitmq/*
        log "Data directory cleaned"
    else
        log "RabbitMQ data directory does not exist"
    fi
    
else
    printf 'Error: Invalid QUEUE_MODE: %s\n' "$QUEUE_MODE" >&2
    exit 1
fi

log "Clean complete"
