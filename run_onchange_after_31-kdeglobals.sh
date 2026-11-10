#!/usr/bin/env bash
# KDE apps (Dolphin) read colors and icons from kdeglobals: use Breeze Dark.
set -euo pipefail
src=/usr/share/color-schemes/BreezeDark.colors
[[ -f $src ]] || exit 0
{
    cat "$src"
    printf '\n[General]\nColorScheme=BreezeDark\nTerminalApplication=kitty\n\n[Icons]\nTheme=Papirus-Dark\n'
} > "$HOME/.config/kdeglobals"

# Without Plasma, KDE apps pick Breeze Light by default: force Breeze Dark per app.
for app in dolphinrc; do
    kwriteconfig6 --file "$app" --group UiSettings --key ColorScheme BreezeDark
done
