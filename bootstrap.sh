#!/usr/bin/env bash
# bootstrap.sh: turn a fresh Arch install into this desktop.
#
# Expects the base install to be done (see "Not covered" below): booting
# system, user with sudo, network. Then, as that user:
#
#   sudo pacman -S --needed git github-cli
#   gh auth login                       # the repo is private
#   gh repo clone Fubge/dotfiles ~/.local/share/chezmoi
#   ~/.local/share/chezmoi/bootstrap.sh
#
# Every step checks first and only changes what is missing, so running it
# again on a finished system is safe. --dry-run prints what it would do.
#
# Not covered (one-time manual work during the Arch install): partitions,
# LUKS, btrfs subvolumes (@, @home, @snapshots) and fstab, mkinitcpio/UKI,
# GRUB install to the ESP, locale, hostname, user + sudo.
set -euo pipefail

dry=false
[[ ${1-} == --dry-run ]] && dry=true
repo=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

step() { printf '\n\e[1;38;2;255;127;0m==> %s\e[0m\n' "$*"; }
info() { printf '    %s\n' "$*"; }
run() {
    if $dry; then
        printf '    [dry-run] %s\n' "$*"
    else
        "$@"
    fi
}

if ((EUID == 0)); then
    echo "Run as your normal user (sudo is used where needed)." >&2
    exit 1
fi
command -v pacman >/dev/null || { echo "This is not Arch Linux." >&2; exit 1; }
$dry || sudo -v

# ---------------------------------------------------------------- pacman
step "pacman: multilib, parallel downloads"
conf=/etc/pacman.conf
if grep -q '^\[multilib\]' "$conf"; then
    info "multilib already enabled"
else
    # uncomment the [multilib] block (header + Include line below it)
    run sudo sed -i '/^#\[multilib\]/{s/^#//;n;s/^#//}' "$conf"
fi
if grep -q '^ParallelDownloads *= *10' "$conf"; then
    info "ParallelDownloads = 10 already set"
else
    run sudo sed -i 's/^#\?ParallelDownloads.*/ParallelDownloads = 10/' "$conf"
fi
if grep -q '^VerbosePkgLists' "$conf"; then
    info "VerbosePkgLists already set"
else
    run sudo sed -i 's/^#VerbosePkgLists/VerbosePkgLists/' "$conf"
fi
run sudo pacman -Syu --needed --noconfirm git chezmoi

# ---------------------------------------------------------------- dotfiles
# Packages (packages/*.txt), configs, root files from system/, SDDM + GRUB
# themes and the user services all come from chezmoi's run_* scripts.
step "chezmoi: packages, dotfiles, system files, themes"
run chezmoi init --source "$repo"     # only writes chezmoi's config, keeps the repo
run chezmoi apply --source "$repo"

# ---------------------------------------------------------------- services
step "system services"
services=(
    NetworkManager.service
    bluetooth.service
    sddm.service
    power-profiles-daemon.service
    ufw.service
    fstrim.timer       # weekly TRIM
    paccache.timer     # trims the package cache
    reflector.timer    # fresh mirror list
)
for s in "${services[@]}"; do
    if systemctl is-enabled --quiet "$s" 2>/dev/null; then
        info "$s already enabled"
    else
        run sudo systemctl enable "$s"
    fi
done
# sddm is only enabled, not started: starting it here would replace this TTY

step "firewall: deny incoming, allow outgoing"
if sudo ufw status | grep -q '^Status: active'; then
    info "ufw already active"
else
    run sudo ufw default deny incoming
    run sudo ufw default allow outgoing
    run sudo ufw --force enable
fi

# ---------------------------------------------------------------- snapper
# Snapshots of / only (pre/post every pacman run via snap-pac). The
# @snapshots subvolume is mounted at /.snapshots by fstab; snapper's own
# create-config wants to create .snapshots itself, so it is unmounted for
# that, snapper's nested subvolume is removed and fstab's mount comes back.
step "snapper: lean snapshots of /"
if [[ -f /etc/snapper/configs/root ]]; then
    info "config 'root' exists"
elif ! findmnt -n /.snapshots >/dev/null && ! grep -q '/\.snapshots' /etc/fstab; then
    info "SKIPPED: no /.snapshots entry in /etc/fstab (create the @snapshots subvolume first)"
else
    run sudo umount /.snapshots || true
    run sudo rmdir /.snapshots || true
    run sudo snapper -c root create-config /
    run sudo btrfs subvolume delete /.snapshots
    run sudo mkdir /.snapshots
    run sudo mount /.snapshots
    run sudo chmod 750 /.snapshots
fi
if [[ -f /etc/snapper/configs/root ]] || $dry; then
    run sudo snapper -c root set-config TIMELINE_CREATE=no NUMBER_LIMIT=10 \
        NUMBER_LIMIT_IMPORTANT=4 SPACE_LIMIT=0.2 FREE_LIMIT=0.3
    if systemctl is-enabled --quiet snapper-cleanup.timer 2>/dev/null; then
        info "snapper-cleanup.timer already enabled"
    else
        run sudo systemctl enable snapper-cleanup.timer
    fi
fi

# ---------------------------------------------------------------- user
step "user: zsh, groups"
if [[ $(getent passwd "$USER" | cut -d: -f7) == /usr/bin/zsh ]]; then
    info "login shell is already zsh"
else
    run sudo chsh -s /usr/bin/zsh "$USER"
fi
groups=(gamemode)   # GameMode daemon permissions
for g in "${groups[@]}"; do
    if id -nG "$USER" | tr ' ' '\n' | grep -qx "$g"; then
        info "already in group $g"
    else
        run sudo usermod -aG "$g" "$USER"
    fi
done

step "done"
info "Reboot, then pick Arch in GRUB and log in on the SDDM screen."
info "Still manual: fprintd-enroll (fingerprint), gh auth / SSH keys, Steam login."
