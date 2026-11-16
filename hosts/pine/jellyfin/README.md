# Jellyfin

Jellyfin media server on pine, published on port 8096 and proxied publicly by spruce's
NPM at `https://jellyfin.willowidk.dev`.

## Host setup on pine

Media is mounted read-only from `/mass-storage/bigboi/media`. Change the `Volume=` line in
`jellyfin.container` if the library lives somewhere else. cypress needs read access to
it. The `z` label relabels the library once for container access, so don't point it at
a directory another confined service (Samba, NFS) also labels.

Hardware transcoding uses the i7-10700's UHD 630 through `/dev/dri/renderD128`:

```sh
sudo setsebool -P container_use_dri_devices 1
sudo usermod -aG render cypress
# the user manager has to pick up the new group
sudo systemctl restart user@$(id -u cypress).service
```

## Spruce NPM host

```txt
Domain: jellyfin.willowidk.dev
Scheme: http
Forward Hostname / IP: <pine's 100.x address>
Forward Port: 8096
Websockets Support: on
```

Allow spruce to reach `pine:8096` in the tailnet policy.

## First run

Open `https://jellyfin.willowidk.dev` (or `http://pine:8096` over the tailnet) and run the
setup wizard. Add libraries from `/media`.

Then set Dashboard → Playback → Transcoding:

- Hardware acceleration: Intel QuickSync (QSV). Fall back to VA-API if QSV breaks, since
  Jellyfin says pre-Ice Lake chips are losing QSV support on Linux.
- Enable hardware decoding for H.264, HEVC, HEVC 10-bit, VP8, and VP9. Leave AV1 off.
  UHD 630 can't decode it.
- Allow encoding in HEVC.
- Leave low-power encoders off. On Gen 9.5 they only cover H.264 and need
  `i915.enable_guc=2`.

Check that it works by playing something that has to transcode and running
`intel_gpu_top` on pine.

## VoidAuth sign-in (LDAP)

Jellyfin authenticates against VoidAuth's LDAP server on spruce
(`100.101.21.106:3890`, tailnet only). Allow pine to reach `spruce:3890` in the tailnet
policy.

In VoidAuth, create the security groups `jellyfin_users` and `jellyfin_admins` and add
people to them.

### MFA accounts

LDAP simple bind can't do a second factor, so VoidAuth refuses binds for any account with
MFA enabled or in an MFA-required group. MFA is per account, not per app, so there's no
exemption for Jellyfin. For an account like that, create a second password-only VoidAuth
account just for Jellyfin (e.g. `cypress-media`):

- give it a strong unique password, kept in 1Password
- add it to `jellyfin_users` (and `jellyfin_admins` if wanted)
- keep it out of any group with "MFA Required" on, and out of `auth_admins`

That account can only sign in to things that don't require MFA, so it's no weaker than
Jellyfin's own local logins.

### Plugin settings

Dashboard → Plugins → Catalog → **LDAP Authentication**, install it, and restart
Jellyfin (`systemctl --user restart jellyfin`). Then under My Plugins → LDAP-Auth:

```txt
LDAP Server:                   100.101.21.106
LDAP Port:                     3890
Secure LDAP:                   off  (the tailnet encrypts it)
LDAP Bind User:                cn=ldap_bind,dc=voidauth
LDAP Bind User Password:       op://spruce/voidauth/LDAP_BIND_PASSWORD
LDAP Base DN for searches:     dc=voidauth
LDAP Search Filter:            (memberOf=cn=jellyfin_users,ou=groups,dc=voidauth)
LDAP Search Attributes:        uid, mail
LDAP Uid Attribute:            uid
LDAP Username Attribute:       uid
LDAP Admin Filter:             (memberOf=cn=jellyfin_admins,ou=groups,dc=voidauth)
Enable User Creation:          on
```

Use **Save and Test LDAP Server Settings** and **Test LDAP User Search** before logging
out. Keep the local admin account from the setup wizard as a break-glass login in case
LDAP or spruce is down.

## Runtime state

`config/` and `cache/` are ignored by Git. Back up `config/`. `cache/` can be rebuilt.
