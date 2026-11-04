# Unlisted Home API Example

Independent v2 code, not a compiled preset or catalogue entry. The native Settings actions inspect the home snapshot or ask for confirmation before moving a first-page icon to an empty same-page grid cell.

Requires `home.read`/`home.grid`, a verified running `winterx-home-grid-v1` engine and enabled FreeMe for moves. The selected experimental2 does not support it; separate batch2 does. Native dock/folder memberships are not changed. Live native dispatch/runtime-limit validation remains outstanding.

```sh
python3 tools/springys_tool.py build examples/home-tweak builds/Home-API-Example-dev.springys
python3 tools/springys_tool.py inspect builds/Home-API-Example-dev.springys
```

Building/inspection does not install, select an engine or restart Spring. New v2 installation is staged and requires a deliberate full launcher reopen. See the [runtime API](../../docs/tweak-runtime-design.md#experimental-home-api).
