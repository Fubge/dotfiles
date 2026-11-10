#!/usr/bin/env bash
# Dark mode and theme names for GTK apps and the settings portal.
set -euo pipefail
gs="gsettings set org.gnome.desktop.interface"
$gs color-scheme      'prefer-dark'
$gs gtk-theme         'adw-gtk3-dark'
$gs icon-theme        'Papirus-Dark'
$gs cursor-theme      'breeze_cursors'
$gs cursor-size       24
$gs font-name         'Noto Sans 11'
$gs monospace-font-name 'JetBrainsMono Nerd Font 11'
