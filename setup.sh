#!/usr/bin/env bash
# setup.sh — Nextcloud AIO bootstrap and operations script
#
# Bootstrap and operate a Nextcloud AIO deployment on a Debian 12 or
# Ubuntu 24.04 host where a system-level nginx already terminates TLS
# for the domain (see nginx/ and docs/REVERSE_PROXY.md).
#
# Workflow:
#   1. install — prerequisites check, .env creation, image pull.
#                No containers are started.  Validate .env and nginx
#                first.
#   2. start   — bring the mastercontainer up.  Then open the AIO
#                interface, enter your domain and start Nextcloud.
#
# Usage:
#   ./setup.sh install [--project-name NAME] [--domain DOMAIN]
#                      [--aio-port PORT] [--apache-port PORT]
#   ./setup.sh start | stop | restart | pull | status | logs [svc]
#   ./setup.sh backup | backup-check | test
#
# Options accepted by 'install':
#   --project-name, -p NAME   Override COMPOSE_PROJECT_NAME in .env
#   --domain,       -d DOMAIN Override DOMAIN_NAME
#   --aio-port        PORT    Override AIO_INTERFACE_PORT in .env
#   --apache-port     PORT    Override APACHE_PORT in .env
#
# Requirements:
#   - Docker Engine  ≥ 24
#   - Docker Compose v2 (integrated — `docker compose`)

set -euo pipefail

# ----------------------------------------------------------------
# Constants
# ----------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"
ENV_EXAMPLE="${SCRIPT_DIR}/.env.example"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"
COMPOSE_TEST_FILE="${SCRIPT_DIR}/docker-compose.test.yml"
VERSION_FILE="${SCRIPT_DIR}/VERSION"
PROJECT_VERSION="$(cat "${VERSION_FILE}" 2>/dev/null | tr -d '[:space:]' || echo 'unknown')"

# Fixed by upstream — the mastercontainer name cannot be changed.
AIO_MASTER_CONTAINER="${AIO_MASTER_CONTAINER:-nextcloud-aio-mastercontainer}"

# ----------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------
info()    { printf '\033[0;34m[INFO]\033[0m  %s\n' "$*"; }
success() { printf '\033[0;32m[OK]\033[0m    %s\n' "$*"; }
warn()    { printf '\033[0;33m[WARN]\033[0m  %s\n' "$*"; }
error()   { printf '\033[0;31m[ERROR]\033[0m %s\n' "$*" >&2; exit 1; }

print_header() {
  cat <<EOF
--------------------------------------------
 Nextcloud AIO — Docker Compose Setup
 Config version : ${PROJECT_VERSION}
--------------------------------------------
EOF
}

check_prerequisites() {
  info "Checking prerequisites…"

  # Docker
  if ! command -v docker &>/dev/null; then
    error "Docker is not installed. Install it from https://docs.docker.com/engine/install/"
  fi

  DOCKER_VERSION=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "0.0.0")
  DOCKER_MAJOR=$(echo "$DOCKER_VERSION" | cut -d. -f1)
  if [[ "$DOCKER_MAJOR" -lt 24 ]]; then
    warn "Docker $DOCKER_VERSION detected; version ≥ 24 is recommended."
  fi

  # Docker Compose v2 (integrated plugin — `docker compose`)
  if ! docker compose version &>/dev/null; then
    error "Docker Compose v2 plugin not found. Run: apt install docker-compose-plugin"
  fi

  success "All prerequisites satisfied."
}

init_env() {
  if [[ -f "$ENV_FILE" ]]; then
    info ".env already exists — skipping generation."
    return
  fi

  info "Generating .env from .env.example…"
  cp "$ENV_EXAMPLE" "$ENV_FILE"

  warn "Nextcloud AIO generates its own secrets internally during setup —"
  warn "there are no secrets to fill in here."
  warn "Review .env and set DOMAIN_NAME before starting."
}

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

# ----------------------------------------------------------------
# .env editing and input validation
# ----------------------------------------------------------------

# set_env_value KEY VALUE — replace (or append) a KEY=VALUE line in .env.
# Rewrites the file line-by-line instead of using sed so that values
# containing '|', '&', backslashes or other special characters are
# written verbatim.
set_env_value() {
  local key="$1" value="$2" tmp="${ENV_FILE}.tmp"
  local found=0 line
  : > "$tmp"
  while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ "$line" == "${key}="* ]]; then
      if [[ "$found" -eq 0 ]]; then
        printf '%s=%s\n' "$key" "$value" >> "$tmp"
        found=1
      fi
      # drop duplicate lines for this key
    else
      printf '%s\n' "$line" >> "$tmp"
    fi
  done < "$ENV_FILE"
  if [[ "$found" -eq 0 ]]; then
    printf '%s=%s\n' "$key" "$value" >> "$tmp"
  fi
  mv "$tmp" "$ENV_FILE"
}

# Validate a value against an ERE pattern; abort on mismatch.
require_match() {
  local value="$1" pattern="$2" label="$3"
  if [[ ! "$value" =~ $pattern ]]; then
    error "Invalid ${label}: '${value}'"
  fi
}

# Validate a TCP port number (1-65535).
require_port() {
  local value="$1" label="$2"
  require_match "$value" '^[0-9]{1,5}$' "$label"
  if (( value < 1 || value > 65535 )); then
    error "Invalid ${label}: '${value}' (must be 1-65535)"
  fi
}

# ----------------------------------------------------------------
# Commands
# ----------------------------------------------------------------
cmd_pull() {
  info "Pulling the mastercontainer image…"
  compose pull
  success "Image up to date."
}

cmd_install() {
  local project_name="" domain="" aio_port="" apache_port=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --project-name|-p)
        [[ -z "${2:-}" ]] && error "--project-name requires a value"
        project_name="$2"; shift 2 ;;
      --domain|-d)
        [[ -z "${2:-}" ]] && error "--domain requires a value"
        domain="$2"; shift 2 ;;
      --aio-port)
        [[ -z "${2:-}" ]] && error "--aio-port requires a value"
        aio_port="$2"; shift 2 ;;
      --apache-port)
        [[ -z "${2:-}" ]] && error "--apache-port requires a value"
        apache_port="$2"; shift 2 ;;
      *) error "Unknown option for install: $1  (run './setup.sh help')" ;;
    esac
  done

  # Validate CLI overrides up-front — reject values that could corrupt
  # .env or break docker compose interpolation.
  [[ -n "$project_name" ]] && require_match "$project_name" '^[a-z0-9][a-z0-9-]*$' "project name"
  [[ -n "$domain" ]]       && require_match "$domain" '^[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?$' "domain"
  [[ -n "$aio_port" ]]     && require_port "$aio_port" "AIO interface port"
  [[ -n "$apache_port" ]]  && require_port "$apache_port" "Apache port"

  check_prerequisites
  init_env

  # Apply CLI overrides to .env --------------------------------------
  [[ -n "$project_name" ]] && { set_env_value "COMPOSE_PROJECT_NAME" "$project_name"; info "COMPOSE_PROJECT_NAME → ${project_name}"; }
  [[ -n "$domain" ]]       && { set_env_value "DOMAIN_NAME" "$domain"; info "DOMAIN_NAME        → ${domain}"; }
  [[ -n "$aio_port" ]]     && { set_env_value "AIO_INTERFACE_PORT" "$aio_port"; info "AIO_INTERFACE_PORT → ${aio_port}"; }
  [[ -n "$apache_port" ]]  && { set_env_value "APACHE_PORT" "$apache_port"; info "APACHE_PORT        → ${apache_port}"; }
  # --------------------------------------------------------------------

  cmd_pull

  success "Installation complete.  No containers have been started."
  info "Next steps:"
  info "  1. Review .env (especially DOMAIN_NAME)."
  info "  2. Configure nginx to proxy to 127.0.0.1:$(grep -m1 '^APACHE_PORT=' "$ENV_FILE" | cut -d= -f2-)."
  info "  3. Run: ./setup.sh start"
}

cmd_start() {
  [[ -f "$ENV_FILE" ]] || error ".env not found.  Run './setup.sh install' first."
  info "Starting the Nextcloud AIO mastercontainer…"
  compose up -d --remove-orphans
  local aio_port
  aio_port=$(grep -m1 '^AIO_INTERFACE_PORT=' "$ENV_FILE" | cut -d= -f2-)
  success "Mastercontainer is running."
  info "Open the AIO interface (self-signed) at https://127.0.0.1:${aio_port}"
  info "  via an SSH tunnel or your reverse proxy (see docs/REVERSE_PROXY.md)."
}

cmd_stop() {
  info "Stopping Nextcloud AIO…"
  compose down
  success "Stack stopped."
}

cmd_restart() {
  cmd_stop
  cmd_start
}

cmd_status() {
  compose ps
}

cmd_logs() {
  local service="${1:-}"
  if [[ -n "$service" ]]; then
    compose logs --follow "$service"
  else
    compose logs --follow
  fi
}

# backup — trigger AIO's built-in Borg backup (creates a full, encrypted
# instance backup).  Configure the backup directory in the AIO interface.
cmd_backup() {
  info "Triggering AIO built-in backup (DAILY_BACKUP=1)…"
  docker exec --env DAILY_BACKUP=1 "$AIO_MASTER_CONTAINER" /daily-backup.sh
  success "Backup requested.  Check the AIO interface for progress."
}

# backup-check — run an integrity check of all AIO Borg backups.
cmd_backup_check() {
  info "Triggering AIO backup integrity check…"
  docker exec --env DAILY_BACKUP=0 --env CHECK_BACKUP=1 --env STOP_CONTAINERS=0 \
    "$AIO_MASTER_CONTAINER" /daily-backup.sh
  success "Backup check requested.  Results appear in the 'nextcloud-aio-borgbackup' container logs."
}

cmd_test() {
  info "Running integration tests inside Docker…"
  docker compose --env-file "$ENV_FILE" \
    -f "$COMPOSE_FILE" -f "$COMPOSE_TEST_FILE" \
    run --rm --build test-runner
}

# ----------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------
print_header

COMMAND="${1:-help}"
shift || true

case "$COMMAND" in
  install)      cmd_install "$@" ;;
  start)        cmd_start ;;
  stop)         cmd_stop ;;
  restart)      cmd_restart ;;
  pull)         cmd_pull ;;
  status)       cmd_status ;;
  logs)         cmd_logs "$@" ;;
  backup)       cmd_backup ;;
  backup-check) cmd_backup_check ;;
  test)         cmd_test ;;
  help|--help|-h)
    cat <<'HELP'
Usage: ./setup.sh <command> [options]

Commands:
  install       First-time setup: check prerequisites, create .env, pull
                the image.  Does NOT start any container.
                Options:
                  --project-name, -p NAME   Set COMPOSE_PROJECT_NAME
                  --domain, -d DOMAIN       Set DOMAIN_NAME
                  --aio-port PORT           Set AIO_INTERFACE_PORT
                  --apache-port PORT        Set APACHE_PORT

  start         Start the mastercontainer.
  stop          Stop and remove containers (data volumes are preserved).
  restart       Equivalent to stop + start.
  pull          Pull the mastercontainer image.
  status        Show running container status.
  logs [svc]    Stream logs (optionally pass a service name).
  backup        Trigger AIO's built-in Borg backup.
  backup-check  Run an integrity check of AIO's Borg backups.
  test          Run the integration test suite inside Docker.
  help          Show this help message.

Typical first-time setup:
  ./setup.sh install --domain nextcloud.example.com --apache-port 11000
  # review .env, configure nginx, then:
  ./setup.sh start
  # open https://127.0.0.1:8080, enter your domain, start Nextcloud

Updating Nextcloud AIO:
  Updates are handled by AIO itself.  Run './setup.sh backup', then use
  the AIO interface (or its automatic update notifications) to stop,
  update and restart the containers.
HELP
    ;;
  *)
    error "Unknown command: $COMMAND  (run './setup.sh help' for usage)" ;;
esac
