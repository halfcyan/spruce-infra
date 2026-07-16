# cal.diy

`cal.diy/` is a Git submodule pointing at the upstream Cal.diy repository:

```txt
https://github.com/calcom/cal.diy.git
```

This repo keeps Spruce-specific instructions and compose overrides outside the submodule so upstream files can be updated cleanly.

## Clone / initialize

When cloning this infra repo from scratch, initialize submodules shallowly:

```sh
git clone --recurse-submodules --shallow-submodules <spruce-infra-repo-url>
```

If the repo is already cloned:

```sh
git submodule update --init --recursive --depth 1
```

The submodule is also marked `shallow = true` in `.gitmodules` so normal submodule initialization should avoid fetching Cal.diy's full history.

## Configure

From the upstream Cal.diy checkout:

```sh
cd cal.diy
cp .env.example .env
chmod 600 .env
```

Edit `cal.diy/.env` for this deployment. At minimum, set production-safe values for:

```txt
NEXT_PUBLIC_WEBAPP_URL=https://cal.diy
NEXTAUTH_URL=https://cal.diy/api/auth
NEXTAUTH_SECRET=<openssl rand -base64 32>
CALENDSO_ENCRYPTION_KEY=<openssl rand -base64 24>
```

The upstream Docker Compose stack provides a local Postgres database by default. Review `DATABASE_URL`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, and `DATABASE_HOST` before first start.

## Start

Run Cal.diy using the upstream compose file plus the Spruce override that attaches the web app to the shared Nginx Proxy Manager network:

```sh
cd cal.diy
podman-compose -f docker-compose.yml -f ../cal.diy.compose.override.yml up -d database redis calcom
```

Starting only `database redis calcom` avoids exposing upstream optional services such as Prisma Studio and the API service on host ports that may conflict with Nginx Proxy Manager. Start those optional services only if you intentionally need them.

The override adds only the `npm` network to the upstream `calcom` service. Keep application and database changes in `cal.diy/.env` or upstream-supported compose overrides; do not edit generated secrets into Git.

## Nginx Proxy Manager

Website proxy host:

```txt
Domain: cal.diy
Scheme: http
Forward Hostname / IP: calcom
Forward Port: 3000
```

## Update

Update the submodule to the latest upstream commit shallowly:

```sh
git submodule update --remote --recursive --depth 1 cal.diy
```

Then review upstream release notes and `.env.example` changes before restarting:

```sh
cd cal.diy
podman-compose -f docker-compose.yml -f ../cal.diy.compose.override.yml pull
podman-compose -f docker-compose.yml -f ../cal.diy.compose.override.yml up -d database redis calcom
```
