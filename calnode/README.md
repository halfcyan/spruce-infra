# CalNode

[CalNode](https://github.com/Calnode/calnode) is a self-hosted booking service. This deployment runs its single application container with SQLite persisted under `data/` and connects it to the shared Nginx Proxy Manager (`npm`) network.

## Configure and start

```sh
cd calnode
cp .env.example .env
chmod 600 .env
```

Edit `.env` before starting:

- Set `BASE_URL` to the final public HTTPS booking URL, such as `https://book.example.com`.
- Generate and retain both encryption secrets. `CALNODE_ENCRYPTION_KEY` protects encrypted settings; keep `CALNODE_RECOVERY_SECRET` offline as recovery material.
- Configure the dedicated Mailcow mailbox. For the usual Mailcow submission service, use its public mail hostname, port `587`, `EMAIL_SMTP_STARTTLS=true`, and `EMAIL_SMTP_TLS=false`.
- Set both `EMAIL_SMTP_USER` and `EMAIL_FROM_ADDRESS` to a mailbox/address Mailcow permits that account to send as. Do not use the iCloud address or its credentials.

Start it:

```sh
podman-compose up -d
```

On first run, open the configured URL and complete the owner-account setup.

## Nginx Proxy Manager

Create a proxy host that preserves the original `Host` header (the Nginx Proxy Manager default):

```txt
Domain: <the hostname in BASE_URL>
Scheme: http
Forward Hostname / IP: calnode
Forward Port: 3000
```

Issue a Let's Encrypt certificate and enable Force SSL. CalNode uses `BASE_URL` to determine its production mode, secure cookies, booking links, and OAuth callback URLs.

## Mailcow test

After completing initial setup, send a test message from **Settings → Email**. Environment SMTP values take precedence over settings stored in CalNode, so retain the SMTP variables in `.env` as the source of truth. If your Mailcow instance uses an internal-only hostname or a non-standard submission port, use its externally reachable SMTP hostname/port instead.

## Backups and updates

The SQLite database at `calnode/data/calnode.db` contains booking data and must be backed up. Configure the optional `LITESTREAM_*` variables for continuous encrypted-secret-safe database replication to a private S3-compatible bucket, or back up `calnode/data/` while the service is stopped.

To update:

```sh
podman-compose pull
podman-compose up -d
```

Review CalNode release notes and `.env.example` changes before updating.
