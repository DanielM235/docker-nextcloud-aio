# Networking: bridge vs host, and the upstream alternative

This document explains how the AIO mastercontainer is attached to the network,
corrects a common confusion, and weighs the security implications of the
possible configurations.

## 1 — `network_mode: bridge` does NOT merge with the host

A common misconception: "bridge mode merges the container network with the
host machine's network." That is **not** correct.

| Mode | What happens |
|------|--------------|
| `network_mode: bridge` (our choice, and upstream default) | The container is attached to Docker's **default bridge network** (`docker0`). It gets a private IP from `172.17.0.0/16`, reaches the outside through **NAT**, and the host only sees the ports you explicitly `publish`. The container does **not** share the host's network namespace. |
| `network_mode: host` | The container **shares the host's network stack** — this is the "merge with the host" behaviour. We do **not** use it. |

So in our Compose file:

```yaml
nextcloud-aio-mastercontainer:
  network_mode: bridge
  ports:
    - "127.0.0.1:${AIO_INTERFACE_PORT:-8080}:8080"
```

…the mastercontainer is isolated behind NAT and exposes **only** the AIO
interface on the loopback address. That is the least-privilege option.

## 2 — The upstream commented alternative

The official
[`compose.yaml`](https://github.com/nextcloud/all-in-one/blob/main/compose.yaml)
ships `network_mode: bridge` and, as a **comment**, an alternative:

```yaml
# network_mode: bridge   # ← default
# networks: ["nextcloud-aio"]   # ← alternative
# ...
# networks:
#   nextcloud-aio:
#     name: nextcloud-aio
#     driver_opts:
#       com.docker.network.driver.mtu: 1440
```

What that alternative does: instead of the **default** bridge, it attaches the
mastercontainer to a **user-defined bridge network named `nextcloud-aio`** —
the same network the sibling containers (Nextcloud, Apache, PostgreSQL, …)
automatically join — with an optional **MTU override**.

Why would you want it?

- **Custom MTU** (e.g. `1440`) when the network path (VPN, tunnels) fragments
  packets.
- To place the mastercontainer on the **same user-defined network as the
  siblings** (useful for some containerized reverse-proxy or monitoring
  setups that need DNS-based discovery of `nextcloud-aio-*` names).
- To attach an external reverse proxy container to the AIO network.

## 3 — Security implications for the host

Both bridge variants are **NAT-isolated** from the host — neither exposes the
host network. The differences are about container-to-container connectivity,
not host exposure:

- **Default bridge (`docker0`)**: legacy network; every container attached to
  it can talk to every other container on it (inter-container communication is
  on), and it has **no built-in DNS**. In our setup only the mastercontainer
  sits on `docker0`, so inter-container exposure there is moot.
- **User-defined bridge (`nextcloud-aio`)**: automatic **DNS**, and
  communication is scoped to containers that explicitly join that network —
  generally the cleaner choice.

The host attack surface of our setup is limited to the **published ports**:

| Port | Binding | Exposure |
|------|---------|----------|
| `AIO_INTERFACE_PORT` (8080) | `127.0.0.1` | loopback only (SSH tunnel / reverse proxy) |
| `APACHE_PORT` (11000) | `127.0.0.1` (via `APACHE_IP_BINDING`) | loopback only (host nginx) |
| `80`, `8443` | not published | none |
| `TALK_PORT` (3478 tcp+udp) | only if Talk enabled | must be firewalled |

Because the reverse proxy is the **host** nginx, the mastercontainer never
needs to be on the `nextcloud-aio` network — it orchestrates siblings through
the Docker socket, and nginx reaches the Apache container through
`127.0.0.1:APACHE_PORT`.

## 4 — Recommendation

**Keep `network_mode: bridge` (the default).** It is:

1. what upstream ships and tests,
2. the simplest configuration,
3. equally secure for our host-nginx setup (loopback-only published ports),
4. and it does **not** share the host network.

Switch to the custom `nextcloud-aio` network **only** if a concrete need
appears: MTU problems behind a VPN, or a containerized reverse proxy /
monitoring agent that must resolve `nextcloud-aio-*` names by DNS. In that
case, pre-create the network (with the MTU option) before starting AIO and
replace `network_mode: bridge` with `networks: [nextcloud-aio]`. Never use
`network_mode: host` — it would expose the mastercontainer directly on the
host interfaces and defeat the isolation.
