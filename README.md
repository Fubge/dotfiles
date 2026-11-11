# dotfiles

Arch Linux + Hyprland on a ThinkPad X9-15p, managed with [chezmoi](https://www.chezmoi.io/).

## New system

After the base Arch install (partitions, LUKS, btrfs subvolumes, UKI, GRUB,
user with sudo, network), as that user:

```sh
sudo pacman -S --needed git github-cli
gh auth login                       # the repo is private
gh repo clone Fubge/dotfiles ~/.local/share/chezmoi
~/.local/share/chezmoi/bootstrap.sh # --dry-run shows what it would do
```

`bootstrap.sh` enables multilib, runs `chezmoi apply` (all packages from
`packages/*.txt`, official repos only, no AUR helper; dotfiles; root files from
`system/`; SDDM and GRUB themes; user services), enables the system services,
sets up ufw and snapper and switches the shell to zsh. It is idempotent: on a
finished system it only reports "already ...".

## Daily use

See [docs/cheatsheet.md](docs/cheatsheet.md) for the full workflow; `dots-check` shows anything untracked.

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
| `system/` | Root-owned files installed to `/` by a run_onchange script |
| `run_onchange_before_10-install-packages.sh.tmpl` | Installs missing packages |
| `dot_config/` | Ends up in `~/.config/` |
| `docs/` | Cheatsheet, manual system changes, rollback guide |
| `.chezmoidata/` | Shared palette and design tokens used by all templates |

Machine-specific values (monitors, sizes, …) live in variables/templates instead of being hardcoded.
