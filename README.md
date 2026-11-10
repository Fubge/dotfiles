# dotfiles

Arch Linux + Hyprland on a ThinkPad X9-15p, managed with [chezmoi](https://www.chezmoi.io/).

## New system

```sh
sudo pacman -S --needed git chezmoi
chezmoi init --apply Fubge/dotfiles
```

`chezmoi apply` installs every package from `packages/*.txt` that is missing
(official repos only, no AUR helper) and re-runs automatically whenever a list changes.
A `bootstrap.sh` for services and system files will follow.

## Daily use

| Command | Purpose |
|---|---|
| `chezmoi edit ~/.config/…` | Edit a file in the source repo |
| `chezmoi diff` | Show what would change |
| `chezmoi apply` | Apply changes |
| `chezmoi cd` | Open a shell in the repo (git commit/push) |

## Layout

| Path | Content |
|---|---|
| `packages/` | Package lists per topic (not copied to `~`) |
| `run_onchange_before_10-install-packages.sh.tmpl` | Installs missing packages |
| `dot_config/` | Ends up in `~/.config/` |

Machine-specific values (monitors, sizes, …) live in variables/templates instead of being hardcoded.
