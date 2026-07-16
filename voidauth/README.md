# VoidAuth

VoidAuth SSO provider for the Spruce services.

Upstream project:

```txt
https://github.com/voidauth/voidauth
```

VoidAuth provides:

- OIDC provider
- Proxy ForwardAuth
- LDAP directory server

## Setup

```sh
cp .env.example .env
chmod 600 .env
```

Edit `.env` and set:

```txt
APP_URL=https://auth.willowidk.dev
STORAGE_KEY=<openssl rand -base64 32>
DB_PASSWORD=<openssl rand -base64 32>
```

## Start

```sh
podman-compose up -d
```

After first start, get the initial admin password reset link from the logs:

```sh
podman-compose logs voidauth
```

## Nginx Proxy Manager

Proxy host:

```txt
auth.willowidk.dev -> http://voidauth:3000
```

In Nginx Proxy Manager:

```txt
Domain: auth.willowidk.dev
Scheme: http
Forward Hostname / IP: voidauth
Forward Port: 3000
```

Request a Let's Encrypt certificate and force SSL.

## Integrating apps

Prefer native OIDC integration when the app supports it:

- Portainer Business Edition: configure OIDC/OAuth against VoidAuth.
- Cal.diy: use native OIDC only if your Cal.diy deployment supports it; avoid blanket proxy auth on public booking pages unless you intentionally want them private.
- Nginx Proxy Manager admin UI: NPM does not have first-class OIDC for its own admin login. Keep the admin UI private with Tailscale/firewalling, or put a separate auth-capable proxy in front of it.

VoidAuth also supports Proxy ForwardAuth for apps that cannot speak OIDC directly, but Nginx Proxy Manager may require custom Nginx config snippets to use that safely.

## Runtime state

These directories are intentionally ignored by Git and should be backed up separately:

- `config/`
- `db/`
