# dotfiles

Arch Linux + Hyprland, verwaltet mit [chezmoi](https://www.chezmoi.io/).

## Neues System

```sh
sudo pacman -S --needed git chezmoi
chezmoi init --apply Fubge/dotfiles
```

(Später: `bootstrap.sh` installiert Pakete und aktiviert Dienste.)

## Alltag

| Befehl | Zweck |
|---|---|
| `chezmoi edit ~/.config/…` | Datei im Repo bearbeiten |
| `chezmoi diff` | Zeigen, was sich ändern würde |
| `chezmoi apply` | Änderungen anwenden |
| `chezmoi cd` | Ins Repo wechseln (git commit/push) |

## Aufbau

- `packages/` – Paketlisten (pacman), nicht nach `~` kopiert
- `dot_config/` – landet in `~/.config/`
- Rechnerspezifisches (Monitore, Variablen) über chezmoi-Templates
