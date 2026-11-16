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

# read-only LDAP for Jellyfin on pine, reached through voidauth-ldap on the tailnet
LDAP_ENABLED=true
LDAP_BIND_PASSWORD={{ op://spruce/voidauth/LDAP_BIND_PASSWORD }}

OIDC_outline_CLIENT_DISPLAY_NAME=Outline
OIDC_outline_CLIENT_HOMEPAGE_URL=https://outline.willowidk.dev
OIDC_outline_CLIENT_SECRET={{ op://spruce/outline/OIDC_CLIENT_SECRET }}
OIDC_outline_CLIENT_AUTH_METHOD=client_secret_post
OIDC_outline_CLIENT_REDIRECT_URLS=https://outline.willowidk.dev/auth/oidc.callback
OIDC_outline_CLIENT_POST_LOGOUT_URLS=https://outline.willowidk.dev
OIDC_outline_CLIENT_GRANT_TYPES=authorization_code, refresh_token
OIDC_outline_CLIENT_SKIP_CONSENT=true
