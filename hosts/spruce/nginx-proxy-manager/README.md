# Nginx Proxy Manager

Quadlet units for Nginx Proxy Manager and the shared `npm` network.

## Prerequisites

`npm.network` creates the shared proxy network named `npm`. Every service that Nginx
Proxy Manager forwards to joins it with `Network=npm.network`.

Rootless Podman also needs permission to bind ports 80 and 443:

```sh
echo 'net.ipv4.ip_unprivileged_port_start=80' | sudo tee /etc/sysctl.d/99-rootless-low-ports.conf
sudo sysctl --system
```

## Start

```sh
systemctl --user start nginx-proxy-manager
```

Admin UI:

```txt
http://SERVER_IP:81
```

## Runtime state

These directories are intentionally ignored by Git:

- `data/`
- `letsencrypt/`

Back them up separately if you want to preserve NPM configuration and certificates.
