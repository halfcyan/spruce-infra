# willowidk.dev

Static site service plus GitHub webhook updater. `willowidk-webhook.build` builds the
webhook image from `webhook/Containerfile`. Restart `willowidk-webhook-build` to rebuild it.

## Runtime layout

`site/` is intentionally ignored by Git and should be a separate clone of the website repository:

```sh
git clone git@github.com:halfcyan/willowidk.dev.git site
```

## Setup

Create a `willowidk.dev` item in the `spruce` 1Password vault with a `WEBHOOK_SECRET`
field set to a fresh random secret, then render `.env`:

```sh
op inject -i .env.tpl -o .env
```

Start:

```sh
systemctl --user start willowidk-nginx willowidk-webhook
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
