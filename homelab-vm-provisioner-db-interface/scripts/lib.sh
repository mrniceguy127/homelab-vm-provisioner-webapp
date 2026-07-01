#!/usr/bin/env bash
# Shared library functions for the db-interface microservice scripts

log() {
    printf '==> %s\n' "$*"
}

error() {
    printf 'Error: %s\n' "$*" >&2
}

require_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        error "Missing command: $1"
        exit 1
    fi
}

run_sudo() {
    if [[ "${EUID}" -eq 0 ]]; then
        "$@"
    else
        sudo "$@"
    fi
}

ensure_sudo_once() {
    local reason="$1"

    [[ "${EUID}" -eq 0 ]] && return 0

    if ! command -v sudo >/dev/null 2>&1; then
        error "sudo is required but not installed"
        return 1
    fi

    sudo -n -v >/dev/null 2>&1 && return 0

    if [[ ! -t 0 || ! -t 1 ]]; then
        error "$reason"
        printf 'Run from an interactive terminal or pre-authorize with: sudo -v\n' >&2
        return 1
    fi

    log "$reason"
    sudo -v
}

source_env() {
    local env_file="$1"
    if [[ -f "$env_file" ]]; then
        set -a
        source "$env_file"
        set +a
    fi
}

detect_os() {
    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        echo "${ID}"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    else
        echo "unknown"
    fi
}

install_system_packages_nodejs() {
    local os_id="$(detect_os)"

    case "$os_id" in
        ubuntu|debian)
            run_sudo apt-get update
            if ! command -v node >/dev/null 2>&1 || [[ "$(node -v | cut -d. -f1 | tr -d 'v')" -lt 18 ]]; then
                log "Installing Node.js 18.x from NodeSource"
                if [[ ! -f /etc/apt/keyrings/nodesource.gpg ]]; then
                    run_sudo mkdir -p /etc/apt/keyrings
                    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | run_sudo gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
                fi
                echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_18.x nodistro main" | run_sudo tee /etc/apt/sources.list.d/nodesource.list
                run_sudo apt-get update
                run_sudo apt-get install -y nodejs
            fi
            ;;
        fedora|rhel|centos)
            if ! command -v node >/dev/null 2>&1 || [[ "$(node -v | cut -d. -f1 | tr -d 'v')" -lt 18 ]]; then
                log "Installing Node.js 18.x"
                run_sudo dnf module install -y nodejs:18
            fi
            ;;
        arch)
            run_sudo pacman -S --needed nodejs npm
            ;;
        macos)
            if ! command -v node >/dev/null 2>&1; then
                error "Node.js not found. Install with: brew install node"
                return 1
            fi
            ;;
        *)
            error "Unsupported OS: $os_id"
            return 1
            ;;
    esac
}
