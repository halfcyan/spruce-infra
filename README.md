# spruce-infra

Rootless Podman infrastructure definitions for the Spruce VPS and pine.

This repository tracks service definitions and templates, not live runtime state or secrets.

## Hosts

- `hosts/spruce/` - public VPS. Runs Nginx Proxy Manager, which is the only public entry point.
- `hosts/pine/` - tailnet-only box without port forwarding. Its public services are proxied
  through spruce's NPM over the tailnet. See [`hosts/pine/README.md`](hosts/pine/README.md).

Each host directory has a `deploy.conf` with its SSH port and user for the deploy pipeline.
The directory name must match the host's Tailscale machine name.

## Services on spruce

- `nginx-proxy-manager/` - public reverse proxy and Let's Encrypt management.
- `voidauth/` - VoidAuth SSO provider.
- `portainer/` - Portainer Business Edition for container management.
- `willowidk.dev/` - static site Nginx container plus GitHub webhook updater.
- `panel-modeler/` - internal static panel database for the panel-modeler desktop application.
- `calnode/` - self-hosted CalNode booking service with SQLite and Mailcow SMTP.
- `outline/` - Outline knowledge base with VoidAuth OIDC sign-in.
- `gh-dispatch/` - hourly `workflow_dispatch` trigger for Ultramarine-Linux/packages' update workflow.

## Host assumptions

- Fedora Server
- Rootless Podman 5 with [Quadlet](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html)
- This repository checked out at `~/spruce-infra` for the `cypress` user. Units reference
  files there through `%h/spruce-infra/hosts/<host>`.
- Services run as the same Linux user so they can share the same rootless Podman network.

Every service is a set of Quadlet units (`.container`, `.network`, `.volume`, `.build`)
in `hosts/<host>/<service>/`. `deploy.sh --host <host>` copies that host's units into `~/.config/containers/systemd/spruce-infra/`,
so systemd starts them at boot, restarts them when they exit, and orders dependencies
like VoidAuth waiting for a healthy database.

## First-time host setup

Install tools:

```sh
sudo dnf install podman git
```

Allow rootless Podman to bind HTTP/HTTPS ports:

```sh
echo 'net.ipv4.ip_unprivileged_port_start=80' | sudo tee /etc/sysctl.d/99-rootless-low-ports.conf
sudo sysctl --system
```

Enable lingering so user services start at boot without a login:

```sh
sudo loginctl enable-linger cypress
```

Enable the Podman API socket for Portainer and automatic image updates for units with
`AutoUpdate=registry`:

```sh
systemctl --user enable --now podman.socket podman-auto-update.timer
```

Clone the repository over HTTPS so pulls don't need credentials:

```sh
git clone https://tangled.org/willowidk.dev/spruce-infra ~/spruce-infra
```

Authorize the deploy pipeline's SSH key (the public half of `OP_SSH_KEY_REF`) in
`~/.ssh/authorized_keys`, and allow the pipeline's Tailscale tag to reach the host on
its sshd port (`SSH_PORT` in `hosts/<host>/deploy.conf`, 1010 on spruce) in the tailnet policy.

## Secrets

Service secrets live in a 1Password vault named after the host (`spruce`, `pine`), never
in this repository. Each service has a committed `.env.tpl` with plain values for
non-secret settings and `{{ op://<host>/<service>/<VAR> }}` references for everything else. Item names match
the service directory, and field names match the variable name.

Render a service's `.env` with the 1Password CLI:

```sh
op inject -i .env.tpl -o .env
```

`op inject` writes the file with mode `0600`. The deploy pipeline does the same thing
for every service using a read-only 1Password service account.

## Deploying

Pushes to `main` run [`.tangled/workflows/deploy.yml`](.tangled/workflows/deploy.yml).
It joins the tailnet, renders every `.env.tpl` from 1Password, and for each directory in
`hosts/` uploads that host's `.env` files, pulls the repository there, and runs:

```sh
./deploy.sh --host <host> --since <previous HEAD> --env-dir ~/.cache/spruce-infra-env
```

A host that's unreachable or fails to deploy doesn't stop the others, but fails the run.

`deploy.sh` installs changed units and `.env` files, reloads systemd, restarts services
whose directory changed (documentation excluded), starts anything that isn't running,
and stops services whose units were removed. Run it by hand on a host the same way, or
with no arguments to install units for `hosts/$(hostname -s)` and start whatever is stopped.

The first deploy after the move to `hosts/` migrates leftover ignored state (`.env`,
`data/`, `db/`, ...) from the old top-level service directories into `hosts/<host>/`.

Check `./validate.sh` before pushing. It runs the Quadlet generator over every unit.

Day to day:

```sh
systemctl --user status voidauth
journalctl --user -u voidauth -f
systemctl --user restart voidauth
```

Ordering is handled by the units: everything on the `npm` network waits for
`npm-network.service`, and `voidauth` waits for `voidauth-db` to pass its healthcheck.

See `hosts/spruce/calnode/README.md` for CalNode, Mailcow SMTP, backup, and update notes.

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

Services on pine are proxied the same way, forwarding to pine's Tailscale IP and
published port. See [`hosts/pine/README.md`](hosts/pine/README.md).

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
available as `http://panel-modeler-panels/panels.json`. See `hosts/spruce/panel-modeler/README.md`
for the service details.

CalNode booking site:

```txt
Domain: <the hostname in calnode/.env BASE_URL>
Scheme: http
Forward Hostname / IP: calnode
Forward Port: 3000
```

Outline:

```txt
Domain: docs.willowidk.dev
Scheme: http
Forward Hostname / IP: outline
Forward Port: 3000
Websockets Support: on
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
- Outline `db/` and `data/`
- Portainer `portainer_data` volume
- app `site/` checkouts
- gh-dispatch `.env` GitHub token
- CalNode `.env` runtime configuration and `calnode/data/` SQLite database
- private keys or cert material

Commit templates instead, such as `.env.tpl` (1Password references only) and `hooks.json.template`.

## Backups

Git is not a backup for runtime state. Back up at least these, under `hosts/spruce/`,
plus whatever pine's services keep in `hosts/pine/`:

- `nginx-proxy-manager/data/`
- `nginx-proxy-manager/letsencrypt/`
- VoidAuth `voidauth/config/` and `voidauth/db/`
- Portainer `portainer_data` volume
- CalNode `calnode/data/` SQLite database (or configure its Litestream replica)

separately with a tool like `restic`, `borg`, or VPS snapshots.
