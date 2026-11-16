# Portainer Business Edition

Quadlet units for Portainer Business Edition.

This mirrors Portainer's Podman example:

```sh
podman run -d -p 8000:8000 -p 9443:9443 --name portainer --restart=always --privileged -v /run/podman/podman.sock:/var/run/docker.sock -v portainer_data:/data portainer/portainer-ee:lts
```

## Prerequisites

The Podman API socket must be enabled for the user running Portainer:

```sh
systemctl --user enable --now podman.socket
```

`portainer.container` mounts the user's socket through `%t/podman/podman.sock`, which
systemd expands to `$XDG_RUNTIME_DIR/podman/podman.sock` (`/run/user/1000/...` for cypress).

Portainer's upstream Podman example mounts the system socket at `/run/podman/podman.sock`, but this repo runs rootless Podman. Using the system socket from a rootless container can fail with `statfs /run/podman/podman.sock: permission denied`.

## Start

```sh
systemctl --user start portainer
```

Portainer listens on:

```txt
https://SERVER_IP:9443
```

Port `8000` is also published for Portainer Edge agent tunneling.

## Nginx Proxy Manager

Optional proxy host:

```txt
portainer.willowidk.dev -> https://portainer:9443
```

In Nginx Proxy Manager, set the scheme to `https`, forward hostname to `portainer`, and forward port to `9443`.

## Runtime state

The `portainer_portainer_data` named volume stores Portainer runtime state and should be backed up separately. `portainer-data.volume` keeps the name podman-compose originally gave it so existing state carries over.

## Security notes

Portainer has access to the Podman socket and runs privileged, matching the upstream example. Treat access to the Portainer UI as administrator-level access to the host's containers.
