# willowidk.dev

Static site service plus GitHub webhook updater.

## Runtime layout

`site/` is intentionally ignored by Git and should be a separate clone of the website repository:

```sh
git clone git@github.com:halfcyan/willowidk.dev.git site
```

## Setup

```sh
cp .env.example .env
chmod 600 .env
```

Edit `.env` and set a fresh GitHub webhook secret.

Start:

```sh
podman-compose up -d --build
```

## GitHub webhook

URL:

```txt
https://webhook.willowidk.dev/hooks/rebuild-site
```

Settings:

- Content type: `application/json`
- Secret: same value as `.env`
- SSL verification: enabled
- Events: push events

## Nginx Proxy Manager

Website proxy host:

```txt
willowidk.dev -> http://willowidk-nginx:80
```

Webhook proxy host:

```txt
webhook.willowidk.dev -> http://willowidk-webhook:9000
```
