# Portainer Business Edition

Rootless Podman Compose definition for Portainer Business Edition.

This mirrors Portainer's Podman example:

```sh
podman run -d -p 8000:8000 -p 9443:9443 --name portainer --restart=always --privileged -v /run/podman/podman.sock:/var/run/docker.sock -v portainer_data:/data portainer/portainer-ee:lts
```

## Prerequisites

The Podman API socket must be enabled. This compose file follows Portainer's example and mounts the system socket:

```txt
/run/podman/podman.sock
```

For the system socket, enable it with:

```sh
sudo systemctl enable --now podman.socket
```

For rootless Podman, the socket is commonly under `/run/user/<uid>/podman/podman.sock` instead. If using the rootless socket, update the socket bind mount in `compose.yml` before starting Portainer.

## Start

```sh
podman-compose up -d
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

The `portainer_data` named volume stores Portainer runtime state and should be backed up separately.

## Security notes

Portainer has access to the Podman socket and runs privileged, matching the upstream example. Treat access to the Portainer UI as administrator-level access to the host's containers.
