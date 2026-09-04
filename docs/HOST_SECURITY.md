# Host security guidance

This document lists the host-level hardening that applies **regardless** of
whether you run the AIO (`aio/`) or the vanilla (`vanilla/`) configuration.
Target: Debian 12 / Ubuntu 24.04.

The principles: only expose what is necessary (SSH and nginx), block direct
access to Docker-published ports, and add rate-limiting / intrusion detection.

---

## 1. Firewall — nftables

Both configurations publish application ports on **loopback only**
(`127.0.0.1`), so from the public interface only `80`/`443` (nginx) and SSH
should ever be reachable. A minimal `/etc/nftables.conf`:

```
#!/usr/sbin/nft -f

flush ruleset

table inet filter {
    chain input {
        type filter hook input priority 0; policy drop;

        # loopback
        iif lo accept

        # established / related
        ct state established,related accept

        # ICMP (rate-limited)
        ip protocol icmp icmp type { echo-request } limit rate 10/second accept
        ip6 nexthdr icmpv6 icmpv6 type { echo-request } limit rate 10/second accept

        # SSH — restrict to your management IP/VPN if possible
        tcp dport 22 accept

        # HTTP / HTTPS (nginx)
        tcp dport { 80, 443 } accept
        # UDP 443 only if you enable HTTP/3 on nginx
        # udp dport 443 accept

        # Nextcloud Talk TURN (only if you self-host Talk)
        # tcp dport 3478 accept
        # udp dport 3478 accept
    }

    chain forward {
        type filter hook forward priority 0; policy drop;

        # allow Docker bridge containers to reach the internet
        ct state established,related accept

        # explicitly drop anything from the public interface INTO docker
        # networks — this prevents a container published on 0.0.0.0 from
        # bypassing the host firewall (defence in depth; our containers are
        # loopback-bound anyway).
        iif != "lo" oifname "docker*" drop
        iif != "lo" oifname "br-*" drop
        iif != "lo" oifname "veth*" drop
    }

    chain output {
        type filter hook output priority 0; policy accept;
    }
}
```

Apply: `nft -f /etc/nftables.conf` and `systemctl enable nftables`.

> The `forward` drop rules are the important part for Docker: even if a
> container is published on `0.0.0.0`, the host firewall can still stop
> external traffic reaching it.

---

## 2. SSH hardening

Edit `/etc/ssh/sshd_config`:

```
PermitRootLogin no
PasswordAuthentication no          # use keys only
PubkeyAuthentication yes
MaxAuthTries 3
X11Forwarding no
AllowAgentForwarding no
```

Then `systemctl reload ssh`. Consider also `sshguard` or fail2ban's `sshd`
jail (below) for brute-force protection.

---

## 3. TLS

TLS terminates at nginx. Use Certbot with the Let's Encrypt nginx plugin:

```bash
apt install certbot python3-certbot-nginx
certbot --nginx -d nextcloud.example.com
```

- Enable HSTS in the nginx template (already present, `includeSubDomains`).
- Keep the strong TLS ciphers shipped in the templates.
- Enable automatic renewal: `systemctl enable --now certbot.timer`.

---

## 4. fail2ban

Install and enable:

```bash
apt install fail2ban
systemctl enable --now fail2ban
```

### Nextcloud jail

Create `/etc/fail2ban/filter.d/nextcloud.conf` (the standard Nextcloud filter)
and a jail that watches the Nextcloud log. The log path depends on the
configuration:

- **Vanilla**: `NEXTCLOUD_DATA_DIR/nextcloud.log` (e.g.
  `/mnt/nextcloud-data/nextcloud.log`).
- **AIO**: inside the nextcloud volume, e.g.
  `/var/lib/docker/volumes/nextcloud_aio_nextcloud/_data/data/nextcloud.log`.

`/etc/fail2ban/jail.d/nextcloud.local`:

```
[nextcloud]
enabled  = true
port     = 80,443
protocol = tcp
filter   = nextcloud
logpath  = /mnt/nextcloud-data/nextcloud.log
maxretry = 5
bantime  = 86400
```

Reload: `systemctl reload fail2ban`.

---

## 5. Automatic security updates

```bash
apt install unattended-upgrades needrestart
dpkg-reconfigure -plow unattended-upgrades   # choose "yes"
```

On Debian/Ubuntu, configure `/etc/apt/apt.conf.d/50unattended-upgrades` to
enable `Unattended-Upgrade::Automatic-Reboot` (or reboot on your own
schedule) so kernel updates take effect.

---

## 6. Docker hygiene

- Never expose the Docker API (`-H tcp://…`); keep `/var/run/docker.sock`
  root-only.
- Only root (or a dedicated, trusted user) should be in the `docker` group.
- Enable Docker log rotation (our compose files already set `max-size` /
  `max-file`).
- Run `docker system prune` periodically to remove unused images.

---

## 7. Data disk (external drive)

Mount the external drive with sensible options in `/etc/fstab`, e.g.:

```
UUID=<uuid>  /mnt/nextcloud-data  ext4  defaults,noatime  0  2
```

- Use **ext4** (or XFS) — avoid NTFS/FAT for the data directory.
- Keep the data directory **outside any webroot** (our configs do this).
- Consider a filesystem-level snapshot (LVM/btrfs) in addition to application
  backups.

---

## 8. Nextcloud-level settings

- Restrict admin access to your LAN/VPN: in `config.php`, set
  `'allowed_admin_ranges' => ['192.168.1.0/24']` (or your VPN range).
- Keep `trusted_domains` to the single domain.
- Use a dedicated subdomain (not a path) — same-origin policy.

---

## Verification checklist

- [ ] `nft list ruleset` shows policy drop + the docker-forward drop rules.
- [ ] From outside: only 22/80/443 open (`nmap` / `ss -lntp`).
- [ ] SSH login is key-only.
- [ ] `fail2ban-client status nextcloud` shows an active jail.
- [ ] `systemctl status unattended-upgrades` active.
- [ ] Data disk mounted `noatime`, and `NEXTCLOUD_DATA_DIR` points at it.
