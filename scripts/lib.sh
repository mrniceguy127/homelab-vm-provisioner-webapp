#!/usr/bin/env bash
# Shared library functions for all monorepo scripts
# Source this file at the beginning of setup/build/start scripts

# Logging
log() {
    printf '==> %s\n' "$*"
}

error() {
    printf 'Error: %s\n' "$*" >&2
}

# Command and path checks
require_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        error "Missing command: $1"
        printf 'Please install %s before continuing\n' "$1" >&2
        exit 1
    fi
}

require_path() {
    if [[ ! -e "$1" ]]; then
        error "Missing required path: $1"
        exit 1
    fi
}

# Sudo management (only when actually needed)
run_sudo() {
    if [[ "${EUID}" -eq 0 ]]; then
        "$@"
    else
        sudo "$@"
    fi
}

ensure_sudo_once() {
    local reason="$1"
    
    # Skip if already root
    if [[ "${EUID}" -eq 0 ]]; then
        return 0
    fi
    
    # Skip if sudo not available
    if ! command -v sudo >/dev/null 2>&1; then
        error "sudo is required but not installed"
        return 1
    fi
    
    # Skip if already cached
    if sudo -n -v >/dev/null 2>&1; then
        return 0
    fi
    
    # Must be interactive terminal
    if [[ ! -t 0 || ! -t 1 ]]; then
        error "$reason"
        printf 'Run from an interactive terminal or pre-authorize with: sudo -v\n' >&2
        return 1
    fi
    
    log "$reason"
    sudo -v
}

# Environment sourcing
source_env() {
    local env_file="$1"
    if [[ -f "$env_file" ]]; then
        set -a
        source "$env_file"
        set +a
    fi
}

# Docker utilities
docker_container_exists() {
    docker inspect "$1" >/dev/null 2>&1
}

docker_container_running() {
    [[ "$(docker inspect -f '{{.State.Running}}' "$1" 2>/dev/null || true)" == "true" ]]
}

docker_container_image_id() {
    docker inspect -f '{{.Image}}' "$1" 2>/dev/null || true
}

docker_image_id() {
    docker image inspect -f '{{.Id}}' "$1" 2>/dev/null || true
}

docker_container_label() {
    local container_name="$1"
    local label_name="$2"
    docker inspect -f "{{index .Config.Labels \"$label_name\"}}" "$container_name" 2>/dev/null || true
}

# Hash utilities
hash_string() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum | cut -d' ' -f1
        return 0
    fi
    if command -v shasum >/dev/null 2>&1; then
        shasum -a 256 | cut -d' ' -f1
        return 0
    fi
    error "Missing command: sha256sum or shasum"
    return 1
}

# Path utilities
relative_path() {
    python3 -c 'import os,sys; print(os.path.relpath(sys.argv[2], sys.argv[1]))' "$1" "$2"
}

# OS detection
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

# System package installation (centralized)
install_system_packages_nodejs() {
    local os_id="$(detect_os)"
    
    case "$os_id" in
        ubuntu|debian)
            run_sudo apt-get update
            
            # Check if Node.js 18+ is installed
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

install_system_packages_python() {
    local os_id="$(detect_os)"
    
    case "$os_id" in
        ubuntu|debian)
            run_sudo apt-get update
            run_sudo apt-get install -y python3 python3-pip python3-venv
            ;;
        fedora|rhel|centos)
            run_sudo dnf install -y python3 python3-pip
            ;;
        arch)
            run_sudo pacman -S --needed python python-pip
            ;;
        macos)
            if ! command -v python3 >/dev/null 2>&1; then
                error "Python 3 not found. Install with: brew install python@3.11"
                return 1
            fi
            ;;
        *)
            error "Unsupported OS: $os_id"
            return 1
            ;;
    esac
}

install_system_packages_postgresql_client() {
    local os_id="$(detect_os)"
    
    case "$os_id" in
        ubuntu|debian)
            run_sudo apt-get update
            run_sudo apt-get install -y postgresql-client
            ;;
        fedora|rhel|centos)
            run_sudo dnf install -y postgresql
            ;;
        arch)
            run_sudo pacman -S --needed postgresql-libs
            ;;
        macos)
            if ! command -v psql >/dev/null 2>&1; then
                log "PostgreSQL client not found. Install with: brew install postgresql@15"
            fi
            ;;
        *)
            error "Unsupported OS: $os_id"
            return 1
            ;;
    esac
}

install_system_packages_postgresql_server() {
    local os_id="$(detect_os)"
    
    case "$os_id" in
        ubuntu|debian)
            run_sudo apt-get update
            run_sudo apt-get install -y postgresql postgresql-contrib
            ;;
        fedora|rhel|centos)
            run_sudo dnf install -y postgresql-server postgresql-contrib
            run_sudo postgresql-setup --initdb --unit postgresql
            run_sudo systemctl enable postgresql
            run_sudo systemctl start postgresql
            ;;
        arch)
            run_sudo pacman -S --needed postgresql
            run_sudo -u postgres initdb -D /var/lib/postgres/data
            run_sudo systemctl enable postgresql
            run_sudo systemctl start postgresql
            ;;
        macos)
            if ! command -v postgres >/dev/null 2>&1; then
                log "PostgreSQL server not found. Install with: brew install postgresql@15 && brew services start postgresql@15"
            fi
            ;;
        *)
            error "Unsupported OS: $os_id"
            return 1
            ;;
    esac
}

# Argument parsing helper
parse_common_args() {
    # Sets global vars: SKIP_NPM, SKIP_SYSTEM_PACKAGES, DOCKER_MODE, SHOW_HELP
    SKIP_NPM=false
    SKIP_SYSTEM_PACKAGES=false
    DOCKER_MODE=false
    SHOW_HELP=false
    REMAINING_ARGS=()
    
    for arg in "$@"; do
        case "$arg" in
            --skip-npm)
                SKIP_NPM=true
                ;;
            --skip-system-packages)
                SKIP_SYSTEM_PACKAGES=true
                ;;
            --docker)
                DOCKER_MODE=true
                ;;
            --help)
                SHOW_HELP=true
                ;;
            *)
                REMAINING_ARGS+=("$arg")
                ;;
        esac
    done
}
