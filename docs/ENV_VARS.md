# Environment Variables

This is the complete reference for `.env`. Copy `.env.example` to `.env` and
adjust the values. Every variable used in `docker-compose.yml` is documented
here; the nginx templates use their own `NGINX_*` variables at render time
(see [REVERSE_PROXY.md](REVERSE_PROXY.md)).

## Compose

| Variable | Default | Description |
|----------|---------|-------------|
| `COMPOSE_PROJECT_NAME` | `nextcloud-aio` | Compose project name. Scopes this Compose project only — it does **not** rename AIO's fixed containers/volumes. |

## Image

| Variable | Default | Description |
|----------|---------|-------------|
| `AIO_IMAGE_REGISTRY` | `ghcr.io/nextcloud-releases` | Registry prefix (change only if mirroring). |
| `AIO_IMAGE_TAG` | `latest` | Release channel: `latest` (stable), `beta`, `develop`. |
| `PULL_POLICY` | `if_not_present` | `always` \| `if_not_present` \| `never`. |

## Docker socket

| Variable | Default | Description |
|----------|---------|-------------|
| `DOCKER_SOCKET_PATH` | `/var/run/docker.sock` | Host socket mounted read-only into the mastercontainer. |
| `WATCHTOWER_DOCKER_SOCKET_PATH` | `/var/run/docker.sock` | Must match `DOCKER_SOCKET_PATH` for self-updates. |

## Domain / networking

| Variable | Default | Description |
|----------|---------|-------------|
| `DOMAIN_NAME` | `nextcloud.example.com` | Public hostname; enter the same domain in the AIO interface. |
| `APACHE_PORT` | `11000` | Host port of AIO's Apache container — nginx proxies here. |
| `APACHE_IP_BINDING` | `127.0.0.1` | Interface the Apache container listens on. |
| `APACHE_ADDITIONAL_NETWORK` | *(empty)* | Optional extra network for AIO's Apache container. |

## AIO interface

| Variable | Default | Description |
|----------|---------|-------------|
| `AIO_INTERFACE_PORT` | `8080` | Host port of the AIO interface (`:8080` in container). |
| `AIO_INTERFACE_BIND_HOST` | `127.0.0.1` | Bind interface for the AIO interface port. |
| `AIO_ADMIN_HOSTNAME` | `aio.example.com` | Hostname used by the `aio-admin` nginx template. |

## Domain validation

| Variable | Default | Description |
|----------|---------|-------------|
| `SKIP_DOMAIN_VALIDATION` | `false` | Set `true` only if AIO cannot validate an otherwise-correct domain. |

## Nextcloud tuning

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXTCLOUD_DATADIR` | *(empty)* | Custom host path/volume for Nextcloud data. Do **not** change after first install. |
| `NEXTCLOUD_MOUNT` | *(empty)* | Host directory mounted into the Nextcloud container (external storage). |
| `NEXTCLOUD_UPLOAD_LIMIT` | `16G` | Max public upload size. |
| `NEXTCLOUD_MAX_TIME` | `3600` | Max execution time (seconds). |
| `NEXTCLOUD_MEMORY_LIMIT` | `512M` | PHP memory limit per process. |
| `NEXTCLOUD_STARTUP_APPS` | *(empty)* | Extra apps installed on first start. |
| `NEXTCLOUD_ADDITIONAL_APKS` | `imagemagick` | Extra Alpine packages for the Nextcloud container. |
| `NEXTCLOUD_ADDITIONAL_PHP_EXTENSIONS` | `imagick` | Extra PHP extensions. |
| `NEXTCLOUD_KEEP_DISABLED_APPS` | `false` | Keep apps disabled in the AIO interface instead of uninstalling. |
| `NEXTCLOUD_TRUSTED_CACERTS_DIR` | *(empty)* | Extra CA certificates to trust (e.g. for LDAPS). |
| `NEXTCLOUD_ENABLE_NVIDIA_GPU` | `false` | Enable NVIDIA GPU acceleration. |

## Backup

| Variable | Default | Description |
|----------|---------|-------------|
| `AIO_DISABLE_BACKUP_SECTION` | `false` | Hide the backup section in the AIO interface. |
| `BORG_RETENTION_POLICY` | *(empty)* | Borg retention. Empty = AIO default `--keep-within=7d --keep-weekly=4 --keep-monthly=6`. |

## Logging / diagnostics

| Variable | Default | Description |
|----------|---------|-------------|
| `AIO_LOG_LEVEL` | `warn` | `error` \| `warn` \| `info` \| `debug`. |
| `DOCKER_API_VERSION` | *(empty)* | Override the internal Docker API version. |
| `COLLABORA_SECCOMP_DISABLED` | `false` | Disable Collabora seccomp if the kernel lacks support. |
| `FULLTEXTSEARCH_JAVA_OPTIONS` | *(empty)* | JVM options for full-text search. |
| `TALK_PORT` | `3478` | Host port for Nextcloud Talk TURN (TCP+UDP). |

## Resources

| Variable | Default | Description |
|----------|---------|-------------|
| `AIO_CPU_LIMIT` | `1.0` | CPU limit for the mastercontainer (cores). |
| `AIO_MEM_LIMIT` | `1g` | Memory limit for the mastercontainer. |
| `AIO_PIDS_LIMIT` | `256` | PID limit for the mastercontainer. |

## Restart / logging

| Variable | Default | Description |
|----------|---------|-------------|
| `RESTART_POLICY` | `unless-stopped` | Restart policy. |
| `LOG_DRIVER` | `json-file` | Logging driver. |
| `LOG_MAX_SIZE` | `10m` | Per-file log rotation size. |
| `LOG_MAX_FILE` | `5` | Number of rotated log files to keep. |
