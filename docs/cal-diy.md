# cal.diy

`cal.diy/` is a Git submodule pointing at the upstream Cal.diy repository:

```txt
https://github.com/calcom/cal.diy.git
```

This repo keeps Spruce-specific instructions and compose overrides outside the submodule so upstream files can be updated cleanly.

## Clone / initialize

When cloning this infra repo from scratch, initialize submodules shallowly:

```sh
git clone --recurse-submodules --shallow-submodules git@github.com:halfcyan/spruce-infra
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

The upstream Docker Compose stack provides a local Postgres database by default. For the in-stack database, make sure the app container uses the Compose service name, not a host-mapped port:

```txt
DATABASE_HOST=database:5432
DATABASE_URL=postgresql://<POSTGRES_USER>:<POSTGRES_PASSWORD>@database:5432/<POSTGRES_DB>
DATABASE_DIRECT_URL=postgresql://<POSTGRES_USER>:<POSTGRES_PASSWORD>@database:5432/<POSTGRES_DB>
```

Do not use `localhost:5450` in `DATABASE_URL` or `DATABASE_DIRECT_URL` for the `calcom` container. Inside a container, `localhost` is the container itself, so Prisma will fail with `P1001` / `ECONNREFUSED` even though the Postgres container is healthy. The Spruce override configures both the Postgres service and the app-side database URLs from `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB`, defaulting to upstream's local database values (`unicorn_user`, `magical_password`, `calendso`).

## Start

Run Cal.diy using the upstream compose file plus the Spruce override that attaches the web app to the shared Nginx Proxy Manager network:

```sh
cd cal.diy
podman-compose -f docker-compose.yml -f ../cal.diy.compose.override.yml up -d database redis calcom
```

Starting only `database redis calcom` avoids exposing upstream optional services such as Prisma Studio and the API service on host ports that may conflict with Nginx Proxy Manager. Start those optional services only if you intentionally need them.

The override attaches the upstream `calcom` service to the `npm` network, configures Cal.diy services to reach Postgres at `database:5432`, and qualifies upstream short image names for Podman, such as `postgres` and `redis`, as `docker.io/library/...`. `DATABASE_HOST` intentionally includes the port because Cal.diy's startup script passes it to `scripts/wait-for-it.sh`, which requires `host:port` or a URL. Keep application and database changes in `cal.diy/.env` or upstream-supported compose overrides; do not edit generated secrets into Git.

If Cal.diy was already started with `DATABASE_URL` pointing at `localhost:5450`, fix `cal.diy/.env` and recreate the app container so it receives the new environment:

```sh
cd cal.diy
podman-compose -f docker-compose.yml -f ../cal.diy.compose.override.yml up -d --force-recreate calcom
```

If migrations or app-store seeding failed against a brand-new database, rerun them or recreate the database volume only if there is no data worth keeping.

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
