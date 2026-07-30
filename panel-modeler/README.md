# panel-modeler panel database

This service publishes the panel-modeler JSON database to the shared rootless
Podman `npm` network. It is intentionally internal by default; expose it through
Nginx Proxy Manager only if the database should be reachable from outside the VPS.

## Setup

Copy or update `data/panels.json` from the panel-modeler repository, then start it
from this directory:

```sh
podman-compose up -d
```

The internal service address is:

```text
http://panel-modeler-panels/panels.json
```

In Nginx Proxy Manager, an optional public proxy host can use:

```text
Domain: panels.<your-domain>
Scheme: http
Forward Hostname / IP: panel-modeler-panels
Forward Port: 80
```

Prefer keeping this service internal unless remote clients need the database. If it
is public, configure HTTPS and restrict access as appropriate.

## Updating the database

The tracked copy is `data/panels.json`. Validate it before restarting:

```sh
python3 -m json.tool data/panels.json >/dev/null
podman-compose config >/dev/null
podman-compose up -d
```

Panel values are nominal and should be checked against current manufacturer
datasheets before use.
