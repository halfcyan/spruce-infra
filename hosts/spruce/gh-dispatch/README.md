# gh-dispatch

Triggers GitHub Actions workflows through `workflow_dispatch` at the top of every hour.

GitHub's `schedule` trigger drops runs under load, especially on the hour, so
Ultramarine-Linux/packages' hourly `update.yml` only ran a few times a day. This
container calls the dispatch API instead.

## Setup

Create a fine-grained personal access token:

- Resource owner: `Ultramarine-Linux` (an org admin may need to approve it)
- Repository access: only `Ultramarine-Linux/packages`
- Permissions: **Actions: Read and write**

Store it as the `GITHUB_TOKEN` field of a `gh-dispatch` item in the `spruce` 1Password
vault, then:

```sh
op inject -i .env.tpl -o .env
systemctl --user start gh-dispatch
```

The repository, ref, and workflow list are set in `gh-dispatch.container`, and the loop
itself is `dispatch.sh`. Add more workflow file names to `DISPATCH_WORKFLOWS` to
dispatch them too.

The target workflow must keep `workflow_dispatch:` in its `on:` block. Once this is
running, drop its `schedule:` trigger so it doesn't double up when GitHub does fire it.

## Logs

```sh
journalctl --user -u gh-dispatch -f
```

It doesn't fire on start, so restarts and redeploys don't trigger extra runs. Use
`gh workflow run update.yml -R Ultramarine-Linux/packages` to trigger one by hand.
