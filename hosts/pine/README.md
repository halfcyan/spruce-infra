# pine

Tailnet-only host with no port forwarding. Public traffic for pine's services enters
through spruce: Nginx Proxy Manager on spruce terminates TLS and forwards plain HTTP to
pine over the tailnet (WireGuard-encrypted).

```txt
client --https--> spruce:443 (NPM) --http over tailnet--> pine:<port> (container)
```

## Services

- `jellyfin/` - Jellyfin media server at `jellyfin.willowidk.dev`, with iGPU transcoding.

## Host setup

Same as spruce (see the top-level README) with these differences:

- Skip the low-ports sysctl. pine never binds 80/443.
- sshd listens on the port in `deploy.conf`. Change it there if it isn't 22.
- Let tailnet traffic through firewalld so spruce can reach published ports:

  ```sh
  sudo firewall-cmd --permanent --zone=trusted --add-interface=tailscale0
  sudo firewall-cmd --reload
  ```

  Access control is then the tailnet policy's job (below), and the LAN still sees
  only the default zone.

## Tailnet policy

Grant:

- the deploy tag (`TS_ADVERTISE_TAGS`) access to `pine:<SSH_PORT>`
- spruce access to pine's service ports

## Adding a service

Services go in `hosts/pine/<service>/` like on spruce, except they publish a port
instead of joining the `npm` network (there's no proxy on pine):

```ini
[Container]
Image=docker.io/example/app:latest
AutoUpdate=registry
ContainerName=example
PublishPort=8080:3000
EnvironmentFile=%h/spruce-infra/hosts/pine/example/.env
Volume=%h/spruce-infra/hosts/pine/example/data:/data:Z
```

Pick a unique host port per service. Containers that only talk to each other can share
a `.network` unit and skip `PublishPort`.

Secrets go in a `pine` 1Password vault with the same `op://pine/<service>/<VAR>`
convention. Give the deploy service account read access to it.

Then add the proxy host in spruce's NPM:

```txt
Domain: example.willowidk.dev
Scheme: http
Forward Hostname / IP: <pine's 100.x address>
Forward Port: 8080
```

Use the Tailscale IP (`tailscale ip -4 pine`) rather than the MagicDNS name. NPM runs
in rootless Podman, and whether MagicDNS resolves inside the container depends on how
the host's resolver is plumbed through. Check reachability from spruce with:

```sh
podman exec nginx-proxy-manager curl -sI http://<pine's 100.x address>:8080
```

Websocket support and the rest of NPM's options work as usual.
