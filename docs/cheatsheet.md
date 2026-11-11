# Cheatsheet: working with these dotfiles

The repo (`~/.local/share/chezmoi`) is the source of truth. `chezmoi apply`
copies it to the system (`~/.config`, `~/.local/bin`, ...). Changes made only on
the system are unknown to the repo until you add them.

Run **`dots-check`** any time to see what is not tracked yet.

## Change a config

```sh
chezmoi edit ~/.config/hypr/binds.lua   # edit the repo copy (opens $EDITOR)
chezmoi apply                           # write it to the system
# or both at once:
chezmoi edit --apply ~/.config/hypr/binds.lua
```

Edited the file in `~/.config` directly (or a program rewrote it)?

```sh
chezmoi diff      # show differences
chezmoi re-add    # copy system changes back into the repo
```

Files ending in `.tmpl` in the repo (e.g. `hyprpaper.conf.tmpl`) are templates:
always edit them with `chezmoi edit`, never with `re-add`.

## Track a new config file

```sh
chezmoi add ~/.config/someapp/config.toml
```

## Install a package

1. Add its name to the matching list in `packages/` (`base`, `hardware`,
   `desktop`, `shell`, `apps`, `gaming`, `dev`).
2. `chezmoi apply` installs everything that is missing.

Installed something with `sudo pacman -S` first? Add it to a list afterwards,
otherwise a fresh install will not have it. `dots-check` lists such packages.

## Save and upload

```sh
dots                  # alias for `chezmoi cd` (shell inside the repo)
git status
git add -A
git commit -m "Describe the change"
git push
exit
```

## Other situations

| Situation | Command |
|---|---|
| Get changes from GitHub (other machine) | `chezmoi update` |
| Anything out of sync? | `dots-check` / `chezmoi status` |
| New machine | `gh auth login`, then `chezmoi init --apply Fubge/dotfiles` |
| Changed something outside `$HOME` (`/etc`, ...) | note it in `docs/system-changes.md` |
| Roll back the system after a broken update | see `docs/system-changes.md` |

## Change colors, gaps, rounding or fonts

All apps read the same two files:

- `.chezmoidata/palette.toml` - every color (accent, backgrounds, text, ...)
- `.chezmoidata/design.toml` - rounding, border width, gaps, fonts
- `.chezmoidata/locale.toml` - language of the dates in the bar (default German)

Edit them (`dots`, then `nvim .chezmoidata/palette.toml`), run `chezmoi apply`,
then reload: `hyprctl reload`, `systemctl --user restart waybar`, restart kitty/apps.
Files ending in `.tmpl` are generated from these values.

## Wallpapers

- `SUPER+W` opens the picker: pick an image, or "Shuffle" (new image every 30 min).
- Your own images: drop them into `~/Pictures/Wallpapers` (subfolders work).
- Every login picks a random desktop image and a different one for the next login screen (`wallpaper-random.service`). A menu choice holds until the next login.
- Login screen background: SUPER+W, then Shift+Enter (Ctrl+Enter = desktop and login). Stored in `/var/lib/login-wallpaper` (user-owned); `login_wallpaper` in `.chezmoidata/design.toml` only seeds it.

## Shortcuts and menus

- **SUPER is the left Alt key** (next to the space bar): left Alt and the Windows key
  are swapped (`altwin:swap_lalt_lwin` in `hypr/vars.lua`), so apps get Alt from the
  Windows key. While a game has focus the swap is undone (see Gaming).
- **`SUPER+H`** lists every shortcut (built live from the descriptions in `hypr/binds.lua`).
- The small menus (Wi-Fi `SUPER+N`, Bluetooth `SUPER+SHIFT+B`, audio `SUPER+A`, power
  profile `SUPER+P`, power `SUPER+Escape`) open in the middle of the screen; clicking the
  same icon in the bar opens them under the mouse. All of them go through `rofi-menu`
  and share the style in `rofi/menu.rasi`; the search field only appears for long lists.
- Clicking the brightness icon opens a slider. The slider and the shortcut overview are
  small GTK4 scripts (`brightness-popup`, `keybinds`) styled by `popups/style.css`.

## Gaming

- **Nothing to set up per game.** `game-watch` (started with Hyprland) spots games by
  how they run, not by name: started by a launcher (Steam, Modrinth App, Lutris,
  `umu-run`, gamescope, ...), running under Wine/Proton, or Minecraft. It turns on
  GameMode for them: performance power profile, ends when the game exits
  (`gamemode-hook`). While a game window has focus, left Alt is a normal Alt key.
- **`SUPER+G`** marks / unmarks the focused window as a game, for anything not caught.
- Steam launch option: just `mangohud %command%` (no `gamemoderun`).
- Minecraft: **Modrinth App** (instances: Vanilla or Fabric + Sodium for more FPS).
- Other stores (GOG, Epic, Battle.net): **Lutris**; a single `.exe`: `umu-run game.exe`
  (uses GE-Proton). A new launcher only needs its process name in `LAUNCHERS` in
  `~/.local/bin/game-watch`.
