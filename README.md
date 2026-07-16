# spruce-infra

Rootless Podman infrastructure definitions for the Spruce VPS.

This repository tracks service definitions and templates, not live runtime state or secrets.

## Services

- `nginx-proxy-manager/` - public reverse proxy and Let's Encrypt management.
- `willowidk.dev/` - static site Nginx container plus GitHub webhook updater.
- `cal.diy/` - Git submodule for the upstream Cal.diy Docker stack.

## Host assumptions

- Fedora Server
- Rootless Podman
- `podman-compose`
- Services run as the same Linux user so they can share the same rootless Podman network.

## First-time host setup

Install tools:

```sh
sudo dnf install podman podman-compose
```

Allow rootless Podman to bind HTTP/HTTPS ports:

```sh
echo 'net.ipv4.ip_unprivileged_port_start=80' | sudo tee /etc/sysctl.d/99-rootless-low-ports.conf
sudo sysctl --system
```

Enable lingering so user services can survive logout/reboot if you later manage containers through user systemd:

```sh
sudo loginctl enable-linger cypress
```

Create the shared Nginx Proxy Manager network:

```sh
podman network create npm
```

## Start order

Start Nginx Proxy Manager first:

```sh
cd nginx-proxy-manager
podman-compose up -d
```

Then start app services:

```sh
cd ../willowidk.dev
cp .env.example .env
chmod 600 .env
# edit .env and set WEBHOOK_SECRET
podman-compose up -d --build

cd ../cal.diy
cp .env.example .env
chmod 600 .env
# edit .env and set NEXT_PUBLIC_WEBAPP_URL, NEXTAUTH_URL, NEXTAUTH_SECRET,
# CALENDSO_ENCRYPTION_KEY, and database settings as needed
podman-compose -f docker-compose.yml -f ../cal.diy.compose.override.yml up -d database redis calcom
```

See `docs/cal-diy.md` for Cal.diy submodule setup and update notes.

## Nginx Proxy Manager hosts

Website:

```txt
Domain: willowidk.dev
Scheme: http
Forward Hostname / IP: willowidk-nginx
Forward Port: 80
```

Webhook:

```txt
Domain: webhook.willowidk.dev
Scheme: http
Forward Hostname / IP: willowidk-webhook
Forward Port: 9000
```

cal.diy website:

```txt
Domain: cal.diy
Scheme: http
Forward Hostname / IP: calcom
Forward Port: 3000
```

## Secrets and runtime state

Do not commit:

- `.env`
- Nginx Proxy Manager `data/`
- Nginx Proxy Manager `letsencrypt/`
- app `site/` checkouts
- Cal.diy `.env` runtime configuration
- private keys or cert material

Commit safe examples/templates instead, such as `.env.example` and `hooks.json.template`.

## Backups

Git is not a backup for runtime state. Back up at least:

- `nginx-proxy-manager/data/`
- `nginx-proxy-manager/letsencrypt/`

separately with a tool like `restic`, `borg`, or your VPS provider snapshots.
