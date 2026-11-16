# Public HTTPS URL for the CalNode admin UI, OAuth callbacks, and booking links.
BASE_URL={{ op://spruce/calnode/BASE_URL }}
# Set only when public booking links use a different hostname.
# PUBLIC_BASE_URL=

# Generate once with: openssl rand -hex 32
# Losing this key makes encrypted SMTP/OAuth settings unrecoverable.
CALNODE_ENCRYPTION_KEY={{ op://spruce/calnode/CALNODE_ENCRYPTION_KEY }}
# Recommended break-glass secret; store it separately from this server.
# Generate once with: openssl rand -hex 32
CALNODE_RECOVERY_SECRET={{ op://spruce/calnode/CALNODE_RECOVERY_SECRET }}

DATABASE_URL=sqlite:///data/calnode.db

# Mailcow SMTP: use a dedicated mailbox or alias, not an iCloud account.
EMAIL_SMTP_HOST={{ op://spruce/calnode/EMAIL_SMTP_HOST }}
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USER={{ op://spruce/calnode/EMAIL_SMTP_USER }}
EMAIL_SMTP_PASS={{ op://spruce/calnode/EMAIL_SMTP_PASS }}
EMAIL_SMTP_TLS=false
EMAIL_SMTP_STARTTLS=true
EMAIL_FROM_ADDRESS={{ op://spruce/calnode/EMAIL_SMTP_USER }}
EMAIL_FROM_NAME=CalNode

# Optional calendar sign-in/integration. op inject resolves references even in
# comments, so add the fields to the calnode item before uncommenting with
# 1Password references like the ones above.
# GOOGLE_CLIENT_ID=
# GOOGLE_CLIENT_SECRET=

# Optional continuous SQLite backup via an S3-compatible provider.
# LITESTREAM_REPLICA_URL=s3://your-private-bucket/calnode
# LITESTREAM_ACCESS_KEY_ID=
# LITESTREAM_SECRET_ACCESS_KEY=
# LITESTREAM_ENDPOINT=
# LITESTREAM_REGION=
