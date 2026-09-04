# Troubleshooting

## The AIO interface won't load

- The AIO interface listens on `https://127.0.0.1:AIO_INTERFACE_PORT` with a
  **self-signed certificate** — accept the certificate warning in your
  browser, or access it through your reverse proxy (`aio-admin` vhost).
- Always use an **IP address** (or your `aio-admin` hostname), not the
  Nextcloud domain, for port `AIO_INTERFACE_PORT` — HSTS can otherwise lock
  you out.
- Check the mastercontainer logs: `docker logs nextcloud-aio-mastercontainer`.

## Domain validation fails

1. Make sure `DOMAIN_NAME` resolves to the server's public IP.
2. Make sure `APACHE_PORT` in `.env` matches the `proxy_pass` port in your
   nginx config.
3. If you are behind Cloudflare or use the ACME DNS challenge, set
   `SKIP_DOMAIN_VALIDATION=true` in `.env` and recreate the mastercontainer.
4. Re-read the upstream debug checklist:
   https://github.com/nextcloud/all-in-one/blob/main/reverse-proxy.md

## Nextcloud loads but uploads / logins are broken

- Ensure `client_max_body_size 0` and `proxy_request_buffering off` are set in
  the nginx vhost (the template already sets them).
- Ensure the WebSocket headers are present (the template already sets them).
- If a hard upload cap is desired, keep it out of nginx and use
  `NEXTCLOUD_UPLOAD_LIMIT` instead.

## Reverse proxy cannot reach AIO

From the server running nginx, verify the Apache port is reachable:

```bash
nc -z 127.0.0.1 11000; echo $?
```

`0` = reachable. If not, check `APACHE_IP_BINDING` (must be `127.0.0.1` when
nginx is on the same host) and that the Apache container is running
(`docker ps | grep nextcloud-aio-apache`).

## Nextcloud Talk

If you enable Talk, open `TALK_PORT` (default `3478`) for **TCP and UDP** in
your firewall/router.

## Port 80 / 8443

This setup runs behind an external reverse proxy, so ports `80` and `8443`
are intentionally **not** published. Do not try to use AIO's built-in HTTPS
(`443`/`80`/`8443`) at the same time — that is the "integrated" mode and
conflicts with the host nginx.

## Reset the instance

To start over, use the AIO interface to stop containers, then remove all
`nextcloud-aio-*` containers and volumes (see the upstream
["How to properly reset the instance"](https://github.com/nextcloud/all-in-one#how-to-properly-reset-the-instance)
section).
