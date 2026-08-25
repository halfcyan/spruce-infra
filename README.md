# spruce-infra

Rootless Podman infrastructure definitions for the Spruce VPS.

This repository tracks service definitions and templates, not live runtime state or secrets.

## Services

- `nginx-proxy-manager/` - public reverse proxy and Let's Encrypt management.
- `voidauth/` - VoidAuth SSO provider.
- `portainer/` - Portainer Business Edition for container management.
- `willowidk.dev/` - static site Nginx container plus GitHub webhook updater.
- `panel-modeler/` - internal static panel database for the panel-modeler desktop application.
- `calnode/` - self-hosted CalNode booking service with SQLite and Mailcow SMTP.

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
cd ../voidauth
cp .env.example .env
chmod 600 .env
# edit .env and set APP_URL, STORAGE_KEY, and DB_PASSWORD
podman-compose up -d

cd ../portainer
podman-compose up -d

cd ../willowidk.dev
cp .env.example .env
chmod 600 .env
# edit .env and set WEBHOOK_SECRET
podman-compose up -d --build

cd ../panel-modeler
podman-compose up -d

cd ../calnode
cp .env.example .env
chmod 600 .env
# edit .env and set BASE_URL, CALNODE_ENCRYPTION_KEY,
# CALNODE_RECOVERY_SECRET, and the Mailcow SMTP settings
podman-compose up -d
```

See `calnode/README.md` for CalNode, Mailcow SMTP, backup, and update notes.

## Mirroring to GitHub

Tangled is the source of truth for this repository. The pipeline at
[`.tangled/workflows/mirror.yml`](.tangled/workflows/mirror.yml) mirrors every branch
and tag push to GitHub.

Configure these repository secrets in Tangled:

- `GITHUB_TOKEN`: a GitHub fine-grained personal access token with **Contents: Read and write** permission on the destination repository
- `GITHUB_REPOSITORY`: the GitHub destination in `owner/repository` form

The workflow uses `git push --mirror`, so the GitHub repository should be dedicated to
this mirror and should not receive independent changes. The destination must already
exist on GitHub.

## Nginx Proxy Manager hosts

VoidAuth:

```txt
Domain: auth.willowidk.dev
Scheme: http
Forward Hostname / IP: voidauth
Forward Port: 3000
```

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

Panel database:

```txt
Domain: panels.willowidk.dev
Scheme: http
Forward Hostname / IP: panel-modeler-panels
Forward Port: 80
```

The public database URL is `https://panels.willowidk.dev/panels.json`; internally it is
available as `http://panel-modeler-panels/panels.json`. See `panel-modeler/README.md`
for the service details.

CalNode booking site:

```txt
Domain: <the hostname in calnode/.env BASE_URL>
Scheme: http
Forward Hostname / IP: calnode
Forward Port: 3000
```

Portainer:

```txt
Domain: portainer.willowidk.dev
Scheme: https
Forward Hostname / IP: portainer
Forward Port: 9443
```

## Secrets and runtime state

Do not commit:

- `.env`
- Nginx Proxy Manager `data/`
- Nginx Proxy Manager `letsencrypt/`
- VoidAuth `config/` and `db/`
- Portainer `portainer_data` volume
- app `site/` checkouts
- CalNode `.env` runtime configuration and `calnode/data/` SQLite database
- private keys or cert material

Commit safe examples/templates instead, such as `.env.example` and `hooks.json.template`.

## Backups

Git is not a backup for runtime state. Back up at least:

- `nginx-proxy-manager/data/`
- `nginx-proxy-manager/letsencrypt/`
- VoidAuth `voidauth/config/` and `voidauth/db/`
- Portainer `portainer_data` volume
- CalNode `calnode/data/` SQLite database (or configure its Litestream replica)

separately with a tool like `restic`, `borg`, or VPS snapshots.
