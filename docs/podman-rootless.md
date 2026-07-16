# Rootless Podman notes

## Low ports

Rootless containers cannot bind ports below 1024 by default. For Nginx Proxy Manager on ports 80 and 443, configure:

```sh
echo 'net.ipv4.ip_unprivileged_port_start=80' | sudo tee /etc/sysctl.d/99-rootless-low-ports.conf
sudo sysctl --system
```

## Shared networks

Rootless Podman networks are user-scoped. Nginx Proxy Manager and app containers must run as the same Linux user to share the `npm` network.

Create the network once:

```sh
podman network create npm
```

## SELinux volume labels

Use `:Z` for private service volumes and `:z` for shared bind mounts. This repo currently uses:

- `:Z` for Nginx Proxy Manager runtime directories.
- `:z` for the site directory mounted by both webhook and Nginx.

## Permissions

If a container cannot write to a bind mount, fix host ownership for the rootless user:

```sh
sudo chown -R cypress:cypress path/to/directory
chmod -R u+rwX path/to/directory
```
