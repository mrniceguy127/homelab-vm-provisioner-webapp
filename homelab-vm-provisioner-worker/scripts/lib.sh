#!/usr/bin/env bash
# Shared library functions for worker scripts

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
