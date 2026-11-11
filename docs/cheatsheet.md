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

Edit them (`dots`, then `nvim .chezmoidata/palette.toml`), run `chezmoi apply`,
then reload: `hyprctl reload`, `systemctl --user restart waybar`, restart kitty/apps.
Files ending in `.tmpl` are generated from these values.

## Wallpapers

- `SUPER+W` opens the picker: pick an image, or "Shuffle" (new image every 30 min).
- Your own images: drop them into `~/Pictures/Wallpapers` (subfolders work).
- `make-wallpapers` re-renders the palette wallpapers (also runs when the palette changes).
- Login screen background: `login_wallpaper` in `.chezmoidata/design.toml`.
