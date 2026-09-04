# Test certificates

The files in this directory are **throwaway, self-signed test certificates**
used only by the `nginx-test` container in `docker-compose.test.yml`. They are
deliberately generic (CN=localhost) and contain **no** real keys or secrets.

- `test.crt` / `test.key` — a self-signed certificate/key pair.
- `dhparam.pem` — Diffie-Hellman parameters (public values, not a secret).

Regenerate with:

```bash
openssl req -x509 -nodes -newkey rsa:2048 \
  -keyout test.key -out test.crt -days 3650 \
  -subj "/CN=localhost"
openssl dhparam -out dhparam.pem 2048
```
