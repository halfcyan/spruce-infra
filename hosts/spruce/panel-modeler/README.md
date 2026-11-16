# panel-modeler panel database

This service publishes the panel-modeler JSON database to the shared rootless
Podman `npm` network. It is intentionally internal by default; expose it through
Nginx Proxy Manager only if the database should be reachable from outside the VPS.

## Setup

Copy or update `data/panels.json` from the panel-modeler repository, then start it
with:

```sh
systemctl --user start panel-modeler-panels
```

The internal service address is:

```text
http://panel-modeler-panels/panels.json
```

In Nginx Proxy Manager, configure this public proxy host:

```text
Domain: panels.willowidk.dev
Scheme: http
Forward Hostname / IP: panel-modeler-panels
Forward Port: 80
```

The public database URL is:

```text
https://panels.willowidk.dev/panels.json
```

Prefer keeping this service internal unless remote clients need the database. If it
is public, configure HTTPS and restrict access as appropriate.

## Updating the database

The tracked copy is `data/panels.json`. Validate it before restarting:

```sh
python3 -m json.tool data/panels.json >/dev/null
systemctl --user restart panel-modeler-panels
```

Panel values are nominal and should be checked against current manufacturer
datasheets before use.
