# FAQ

## PrintScreen doesn't work after setup

The `gsd-media-keys` daemon might not have picked up the new keybindings. Run `waysnip setup` again (it restarts the daemon automatically), or restart it manually:

```bash
killall gsd-media-keys
/usr/libexec/gsd-media-keys &
```

If that doesn't help, log out and back in.

## PrintScreen doesn't work while a tray menu is open

While any system-tray application's context menu is open (waysnip's or another app's), pressing PrintScreen does nothing. This is GNOME Shell behavior, not a waysnip bug. The same suppression happens whether your shortcut runs waysnip or any other command.

The mechanism: `gnome-settings-daemon` registers user custom keybindings with a mode mask of `NORMAL | OVERVIEW` only ([`shortcuts-list.h`](https://github.com/GNOME/gnome-settings-daemon/blob/master/plugins/media-keys/shortcuts-list.h)). When any popup menu is open, GNOME Shell's `Main.actionMode` is `POPUP`, and its [`_filterKeybinding()`](https://github.com/GNOME/gnome-shell/blob/main/js/ui/windowManager.js) slot tells mutter to drop the binding because the masks don't intersect. Same outcome on X11 via a different code path (the popup installs an X11 keyboard grab).

Workaround: close the menu first with Esc, then press PrintScreen.

## Saved image looks flat, can't re-edit annotations

The save mode must be `"annotated"` (the default). Check your config:

```bash
waysnip config --edit
```

Make sure `[save]` has `mode = "annotated"`. If you used `"editable"` or flattened the image via the gallery context menu, annotations are baked into the pixels.

## How do I change the save location?

Either use the settings GUI:

```bash
waysnip config
```

Or edit `~/.config/waysnip/config.toml` directly and change `directory` under `[save]`.

## How do I uninstall completely?

```bash
waysnip uninstall && pipx uninstall waysnip
```

`waysnip uninstall` removes keybindings, the autostart entry, the launcher wrapper, and restores GNOME's default screenshot keys.

## Multi-monitor: capture looks wrong

Different DPI across monitors is a known limitation. Region and fullscreen captures work across all monitors, but mixed DPI setups can cause scaling issues. This is being improved.

## WaySnip doesn't start in the tray on login

Make sure you ran `waysnip setup`. This creates an autostart entry at `~/.config/autostart/waysnip.desktop`. Check that the file exists and that `X-GNOME-Autostart-enabled` is set to `true`.
