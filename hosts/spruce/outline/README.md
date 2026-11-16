# Outline

[Outline](https://github.com/outline/outline) knowledge base, signed in through VoidAuth
OIDC. Runs with Postgres (`outline-db`), Valkey (`outline-redis`), and local file storage
under `data/`.

## Setup

Create an `outline` item in the `spruce` 1Password vault with these fields, each
generated with `openssl rand -hex 32`:

- `SECRET_KEY`
- `UTILS_SECRET`
- `DB_PASSWORD`
- `OIDC_CLIENT_SECRET`

`voidauth/.env.tpl` reads `OIDC_CLIENT_SECRET` from this item to declare the `outline`
OIDC client, so nothing needs to be clicked together in the VoidAuth admin UI. Pushing
restarts VoidAuth along with Outline.

## Nginx Proxy Manager

```txt
Domain: outline.willowidk.dev
Scheme: http
Forward Hostname / IP: outline
Forward Port: 3000
Websockets Support: on
```

Request a Let's Encrypt certificate and force SSL. Websockets are required for
collaborative editing.

## First sign-in

The first VoidAuth user to sign in creates the workspace and becomes its admin. Any
VoidAuth user can sign in after that unless you restrict the client, for example with
`OIDC_outline_CLIENT_GROUPS=<group>` in `voidauth/.env.tpl`.

Outline discovers VoidAuth's endpoints from `https://auth.willowidk.dev/oidc` on
startup, so the container needs to reach that public hostname.

## Runtime state

Back these up:

- `db/` - Postgres
- `data/` - uploaded attachments and images
