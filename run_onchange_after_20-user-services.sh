#!/usr/bin/env bash
# Desktop components run as systemd user services (started with the uwsm session).
set -euo pipefail
services=(hyprpaper hypridle hyprpolkitagent waybar)
systemctl --user enable "${services[@]}"
# Start them right away if a graphical session is already running
if systemctl --user is-active --quiet graphical-session.target; then
    systemctl --user restart "${services[@]}"
fi
