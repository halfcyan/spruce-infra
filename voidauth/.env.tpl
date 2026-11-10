# Public URL used by VoidAuth for redirects and issuer metadata.
APP_URL=https://auth.willowidk.dev

# Generate with: openssl rand -base64 32
STORAGE_KEY={{ op://spruce/voidauth/STORAGE_KEY }}

# Shared with voidauth-db as POSTGRES_PASSWORD.
# Generate with: openssl rand -base64 32
DB_PASSWORD={{ op://spruce/voidauth/DB_PASSWORD }}
POSTGRES_PASSWORD={{ op://spruce/voidauth/DB_PASSWORD }}

# Upstream default for the compose database service.
DB_ADAPTER=postgres
DB_HOST=voidauth-db
