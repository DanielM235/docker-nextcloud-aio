#!/usr/bin/env bash
# setup.sh — Nextcloud (vanilla) bootstrap and operations script
#
# Bootstrap and operate the "vanilla" Nextcloud stack (official image +
# MariaDB + Redis) on a Debian 12 / Ubuntu 24.04 host where a system-level
# nginx terminates TLS (see nginx/ and ../docs/HOST_SECURITY.md).
#
# Usage:
#   ./setup.sh install [--project-name NAME] [--domain DOMAIN] [--port PORT]
#   ./setup.sh start | stop | restart | pull | status | logs [svc]
#   ./setup.sh backup | restore <backup-dir>
#   ./setup.sh update | occ <args> | test
#
# Requirements:
#   - Docker Engine  ≥ 24
#   - Docker Compose v2 (integrated — `docker compose`)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"
ENV_EXAMPLE="${SCRIPT_DIR}/.env.example"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"
COMPOSE_TEST_FILE="${SCRIPT_DIR}/docker-compose.test.yml"
VERSION_FILE="${SCRIPT_DIR}/VERSION"
PROJECT_VERSION="$(cat "${VERSION_FILE}" 2>/dev/null | tr -d '[:space:]' || echo 'unknown')"

info()    { printf '\033[0;34m[INFO]\033[0m  %s\n' "$*"; }
success() { printf '\033[0;32m[OK]\033[0m    %s\n' "$*"; }
warn()    { printf '\033[0;33m[WARN]\033[0m  %s\n' "$*"; }
error()   { printf '\033[0;31m[ERROR]\033[0m %s\n' "$*" >&2; exit 1; }

print_header() {
  cat <<EOF
--------------------------------------------
 Nextcloud (vanilla) — Docker Compose Setup
 Config version : ${PROJECT_VERSION}
--------------------------------------------
EOF
}

check_prerequisites() {
  info "Checking prerequisites…"
  command -v docker &>/dev/null || error "Docker is not installed. See https://docs.docker.com/engine/install/"
  DOCKER_MAJOR=$(docker version --format '{{.Server.Version}}' 2>/dev/null | cut -d. -f1 || echo 0)
  [[ "$DOCKER_MAJOR" -lt 24 ]] && warn "Docker $(docker version --format '{{.Server.Version}}' 2>/dev/null) detected; version ≥ 24 is recommended."
  docker compose version &>/dev/null || error "Docker Compose v2 plugin not found. Run: apt install docker-compose-plugin"
  success "All prerequisites satisfied."
}

generate_secret() {
  local length="${1:-32}" out
  # Read `length` random bytes and hex-encode them (2*length hex chars).
  # `head` exits cleanly after N bytes, so this is pipefail-safe.
  out="$(head -c "$length" /dev/urandom | od -An -v -tx1 | tr -d ' \n')"
  printf '%s\n' "$out"
}

init_env() {
  if [[ -f "$ENV_FILE" ]]; then
    info ".env already exists — skipping generation."
    return
  fi
  info "Generating .env from .env.example…"
  cp "$ENV_EXAMPLE" "$ENV_FILE"

  set_env_value "MYSQL_ROOT_PASSWORD" "$(generate_secret 24)"
  set_env_value "MYSQL_PASSWORD" "$(generate_secret 24)"
  set_env_value "REDIS_HOST_PASSWORD" "$(generate_secret 24)"
  chmod 600 "$ENV_FILE"
  warn "Database and Redis secrets generated and written to .env (chmod 600)."
  warn "Review .env and set DOMAIN_NAME before starting."
}

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

read_env_value() {
  local key="$1"
  grep -m1 "^${key}=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- || true
}

# set_env_value KEY VALUE — replace (or append) a KEY=VALUE line in .env
# line-by-line (values written verbatim, no sed interpolation).
set_env_value() {
  local key="$1" value="$2" tmp="${ENV_FILE}.tmp"
  local found=0 line mode
  mode=$(stat -c '%a' "$ENV_FILE" 2>/dev/null || true)
  : > "$tmp"
  while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ "$line" == "${key}="* ]]; then
      if [[ "$found" -eq 0 ]]; then
        printf '%s=%s\n' "$key" "$value" >> "$tmp"
        found=1
      fi
    else
      printf '%s\n' "$line" >> "$tmp"
    fi
  done < "$ENV_FILE"
  [[ "$found" -eq 0 ]] && printf '%s=%s\n' "$key" "$value" >> "$tmp"
  mv "$tmp" "$ENV_FILE"
  [[ -n "$mode" ]] && chmod "$mode" "$ENV_FILE"
}

require_match() {
  local value="$1" pattern="$2" label="$3"
  [[ "$value" =~ $pattern ]] || error "Invalid ${label}: '${value}'"
}

require_port() {
  local value="$1" label="$2"
  require_match "$value" '^[0-9]{1,5}$' "$label"
  (( value >= 1 && value <= 65535 )) || error "Invalid ${label}: '${value}' (must be 1-65535)"
}

# ----------------------------------------------------------------
# Commands
# ----------------------------------------------------------------
cmd_pull() {
  info "Pulling images…"
  compose pull
  success "Images up to date."
}

cmd_install() {
  local project_name="" domain="" port=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --project-name|-p) [[ -z "${2:-}" ]] && error "--project-name requires a value"; project_name="$2"; shift 2 ;;
      --domain|-d)       [[ -z "${2:-}" ]] && error "--domain requires a value"; domain="$2"; shift 2 ;;
      --port|-P)         [[ -z "${2:-}" ]] && error "--port requires a value"; port="$2"; shift 2 ;;
      *) error "Unknown option for install: $1  (run './setup.sh help')" ;;
    esac
  done

  [[ -n "$project_name" ]] && require_match "$project_name" '^[a-z0-9][a-z0-9-]*$' "project name"
  [[ -n "$domain" ]]       && require_match "$domain" '^[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?$' "domain"
  [[ -n "$port" ]]         && require_port "$port" "port"

  check_prerequisites
  init_env

  [[ -n "$project_name" ]] && { set_env_value "COMPOSE_PROJECT_NAME" "$project_name"; info "COMPOSE_PROJECT_NAME → ${project_name}"; }
  [[ -n "$domain" ]]       && { set_env_value "DOMAIN_NAME" "$domain"; set_env_value "OVERWRITECLIURL" "https://${domain}"; info "DOMAIN_NAME → ${domain}"; }
  [[ -n "$port" ]]         && { set_env_value "APP_HTTP_PORT" "$port"; info "APP_HTTP_PORT → ${port}"; }

  # Prepare the data directory (external disk).  It must be owned by
  # www-data (uid 33) so the install step can write into it.
  local data_dir
  data_dir="$(grep -m1 '^NEXTCLOUD_DATA_DIR=' "$ENV_FILE" | cut -d= -f2-)"
  if [[ -n "$data_dir" && "$data_dir" != /var/www* ]]; then
    mkdir -p "$data_dir"
    if ! chown 33:33 "$data_dir" 2>/dev/null; then
      warn "Could not chown ${data_dir} to 33:33 (www-data)."
      warn "  Mount the disk and run: sudo chown 33:33 ${data_dir}"
    else
      info "Data directory: ${data_dir} (chowned to www-data)"
    fi
  fi

  cmd_pull
  success "Installation complete.  No containers have been started."
  info "Next steps:"
  info "  1. Review .env (especially DOMAIN_NAME and NEXTCLOUD_DATA_DIR)."
  info "  2. Configure nginx to proxy to 127.0.0.1:$(grep -m1 '^APP_HTTP_PORT=' "$ENV_FILE" | cut -d= -f2-)."
  info "  3. Run: ./setup.sh start"
}

cmd_start() {
  [[ -f "$ENV_FILE" ]] || error ".env not found.  Run './setup.sh install' first."
  info "Starting the Nextcloud stack…"
  compose up -d --remove-orphans
  success "Stack is running."
  info "Finish setup at https://$(grep -m1 '^DOMAIN_NAME=' "$ENV_FILE" | cut -d= -f2-)."
}

cmd_stop()   { info "Stopping the stack…";  compose down; success "Stack stopped."; }
cmd_restart(){ cmd_stop; cmd_start; }
cmd_status() { compose ps; }

cmd_logs() {
  local service="${1:-}"
  if [[ -n "$service" ]]; then compose logs --follow "$service"; else compose logs --follow; fi
}

# backup — full instance backup: DB dump + data directory + config volume.
cmd_backup() {
  [[ -f "$ENV_FILE" ]] || error ".env not found.  Run './setup.sh install' first."

  local ts dest backup_root project db root_pass data_dir retention
  ts="$(date +%Y%m%d-%H%M%S-%N)"
  backup_root="$(read_env_value BACKUP_DIR)"; backup_root="${backup_root:-backups}"
  dest="${SCRIPT_DIR}/${backup_root}/${ts}"
  project="$(read_env_value COMPOSE_PROJECT_NAME)"; project="${project:-nextcloud-vanilla}"
  db="$(read_env_value MYSQL_DATABASE)"; db="${db:-nextcloud}"
  root_pass="$(read_env_value MYSQL_ROOT_PASSWORD)"
  data_dir="$(read_env_value NEXTCLOUD_DATA_DIR)"; data_dir="${data_dir:-/mnt/nextcloud-data}"
  mkdir -p "$dest"

  info "Backing up the database (${db})…"
  compose exec -T db mariadb-dump -h 127.0.0.1 -uroot -p"${root_pass}" \
    --single-transaction --quick "${db}" > "${dest}/db.sql"

  info "Backing up the data directory (${data_dir})…"
  if [[ -d "$data_dir" ]]; then
    tar czf "${dest}/data.tgz" -C "$data_dir" .
  else
    warn "Data directory ${data_dir} not found — skipped (is the external disk mounted?)."
  fi

  info "Backing up the config/app volume (${project}_nextcloud)…"
  docker run --rm -v "${project}_nextcloud:/data:ro" alpine:3.20 \
    tar czf - -C /data . > "${dest}/config.tgz"

  [[ -f "$ENV_FILE" ]] && cp "$ENV_FILE" "${dest}/.env"

  {
    echo "timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "project=${project}"
    echo "database=${db}"
    echo "data_dir=${data_dir}"
    echo "nextcloud_image=nextcloud:$(read_env_value NEXTCLOUD_IMAGE_TAG)"
  } > "${dest}/manifest.txt"

  success "Backup created: ${dest}"

  retention="$(read_env_value BACKUP_RETENTION_DAYS)"
  if [[ "$retention" =~ ^[0-9]+$ && "$retention" -gt 0 ]]; then
    find "${SCRIPT_DIR}/${backup_root}" -mindepth 1 -maxdepth 1 -type d \
      -mtime "+${retention}" -exec rm -rf {} + 2>/dev/null || true
  fi
}

# restore — restore a backup created by 'backup'.
cmd_restore() {
  local src="${1:-}"
  [[ -z "$src" ]] && error "Usage: ./setup.sh restore <backup-dir>"
  [[ -f "$ENV_FILE" ]] || error ".env not found.  Run './setup.sh install' first."
  [[ -d "$src" ]] || error "Backup directory not found: $src"

  local project db root_pass data_dir
  project="$(read_env_value COMPOSE_PROJECT_NAME)"; project="${project:-nextcloud-vanilla}"
  db="$(read_env_value MYSQL_DATABASE)"; db="${db:-nextcloud}"
  root_pass="$(read_env_value MYSQL_ROOT_PASSWORD)"
  data_dir="$(read_env_value NEXTCLOUD_DATA_DIR)"; data_dir="${data_dir:-/mnt/nextcloud-data}"

  info "Ensuring the stack is running…"
  compose up -d db

  info "Putting Nextcloud into maintenance mode…"
  compose exec -u www-data -T app php occ maintenance:mode --on 2>/dev/null || warn "Could not enter maintenance mode (app may not be running)."

  if [[ -f "${src}/db.sql" ]]; then
    info "Restoring the database…"
    compose cp "${src}/db.sql" db:/tmp/restore.sql
    compose exec -T db sh -c "mariadb -h 127.0.0.1 -uroot -p'${root_pass}' '${db}' < /tmp/restore.sql && rm /tmp/restore.sql"
    success "Database restored."
  else
    warn "No ${src}/db.sql — skipping DB restore."
  fi

  if [[ -f "${src}/data.tgz" ]]; then
    info "Restoring the data directory…"
    tar xzf "${src}/data.tgz" -C "$data_dir"
    success "Data restored."
  fi

  if [[ -f "${src}/config.tgz" ]]; then
    info "Restoring the config/app volume…"
    docker run --rm -i -v "${project}_nextcloud:/data" alpine:3.20 \
      tar xzf - -C /data < "${src}/config.tgz"
    success "Config restored."
  fi

  info "Leaving maintenance mode…"
  compose exec -u www-data -T app php occ maintenance:mode --off 2>/dev/null || warn "Could not exit maintenance mode."
  success "Restore complete.  Run './setup.sh start' if the stack was stopped."
}

# update — pull newer images and restart (Nextcloud migrates on startup).
cmd_update() {
  [[ -f "$ENV_FILE" ]] || error ".env not found.  Run './setup.sh install' first."
  warn "Upgrade one Nextcloud major version at a time (see docs/UPDATE.md)."
  info "Creating a pre-update backup…"
  cmd_backup
  info "Pulling new images…"
  compose pull
  info "Recreating containers…"
  compose up -d --remove-orphans
  success "Update complete.  Nextcloud ran its own migration on startup."
}

# occ — run a Nextcloud occ command as www-data.
cmd_occ() {
  [[ -f "$ENV_FILE" ]] || error ".env not found.  Run './setup.sh install' first."
  compose exec -u www-data app php occ "$@"
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
  install)  cmd_install "$@" ;;
  start)    cmd_start ;;
  stop)     cmd_stop ;;
  restart)  cmd_restart ;;
  pull)     cmd_pull ;;
  status)   cmd_status ;;
  logs)     cmd_logs "$@" ;;
  backup)   cmd_backup ;;
  restore)  cmd_restore "$@" ;;
  update)   cmd_update ;;
  occ)      cmd_occ "$@" ;;
  test)     cmd_test ;;
  help|--help|-h)
    cat <<'HELP'
Usage: ./setup.sh <command> [options]

Commands:
  install       First-time setup: prerequisites, .env + secrets, pull.
                Does NOT start any container.  Options:
                  --project-name, -p NAME   Set COMPOSE_PROJECT_NAME
                  --domain, -d DOMAIN       Set DOMAIN_NAME (+ OVERWRITECLIURL)
                  --port, -P PORT           Set APP_HTTP_PORT

  start         Start the stack.
  stop          Stop and remove containers (volumes preserved).
  restart       stop + start.
  pull          Pull images.
  status        Show container status.
  logs [svc]    Stream logs.
  backup        Full backup: DB dump + data dir + config volume.
  restore DIR   Restore a backup created by 'backup'.
  update        Pull new images and restart (backup first).  Upgrade one
                major Nextcloud version at a time — see docs/UPDATE.md.
  occ <args>    Run a Nextcloud occ command (as www-data).
  test          Run the integration test suite inside Docker.
  help          Show this message.

Typical first-time setup:
  ./setup.sh install --domain nextcloud.example.com --port 8080
  # review .env, configure nginx, then:
  ./setup.sh start
HELP
    ;;
  *) error "Unknown command: $COMMAND  (run './setup.sh help' for usage)" ;;
esac
