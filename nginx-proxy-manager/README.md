# Nginx Proxy Manager

Rootless Podman Compose definition for Nginx Proxy Manager.

## Prerequisites

Create the shared proxy network once:

```sh
podman network create npm
```

Rootless Podman also needs permission to bind ports 80 and 443:

```sh
echo 'net.ipv4.ip_unprivileged_port_start=80' | sudo tee /etc/sysctl.d/99-rootless-low-ports.conf
sudo sysctl --system
```

## Start

```sh
podman-compose up -d
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
