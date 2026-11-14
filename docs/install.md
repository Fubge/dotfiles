# Installing

Two ways in. Both end with the same desktop.

| | You have | You get |
|---|---|---|
| **A. Existing Arch** | any working Arch install, any bootloader, any filesystem | the whole desktop; your boot setup stays untouched |
| **B. Full layout** | a fresh disk | the setup as it runs here: LUKS + btrfs snapshots + UKI + themed GRUB |

> Requirements: x86_64, a user with `sudo`, network. Everything comes from the
> official repos (no AUR helper). NVIDIA support exists but is untested.

## A. On an existing Arch install

```sh
sudo pacman -S --needed git
git clone https://github.com/Fubge/dotfiles ~/.local/share/chezmoi
~/.local/share/chezmoi/bootstrap.sh --dry-run   # optional: see what it would do
~/.local/share/chezmoi/bootstrap.sh
reboot
```

`bootstrap.sh` asks a few questions (stored in `~/.config/chezmoi/chezmoi.toml`):

| Question | Default | Used for |
|---|---|---|
| CPU vendor | detected | `intel-ucode` / `amd-ucode` |
| Graphics | `intel` | driver packages from `packages/machine/` (+ NVIDIA env vars) |
| Keyboard layout / xkb options | `us` / `caps:swapescape` | Hyprland input; add `altwin:swap_lalt_lwin` to use left Alt as SUPER |
| Clock locale | `en_US.UTF-8` | date language in the bar (must be in `locale -a`) |
| Display mode / scale | `preferred` / `auto` | internal panel, SDDM DPI |
| Gaming stack | yes | Steam, GameMode, MangoHud, gamescope, Modrinth App |
| Personal apps | yes | Vivaldi, Discord, Bitwarden, Spotify |
| Firmware | `linux-firmware` | all firmware; or only your hardware's split packages, e.g. `linux-firmware-intel linux-firmware-realtek` (check `journalctl -k \| grep -i firmware`), then `sudo pacman -Rns linux-firmware` |
| Manage the boot chain | **no** | only for layout B, see below |

Answer **no** to the boot question unless your system matches layout B: it
rewrites `/etc/kernel/cmdline`, `/etc/vconsole.conf` and the GRUB config.

What `bootstrap.sh` then does, step by step (each step checks first, so it is
safe to run again):

1. `pacman.conf`: `[multilib]` (Steam), parallel downloads
2. `chezmoi apply`: packages, dotfiles, root files from `system/`, SDDM theme, user services
3. enables NetworkManager, bluetooth, **SDDM**, power-profiles-daemon, ufw, fstrim, paccache, reflector
   (disable your old display manager first if you have one)
4. ufw: deny incoming, allow outgoing
5. snapper for `/`, only if `/.snapshots` is in fstab (btrfs layout)
6. zsh as login shell, `gamemode` group

Change an answer later: edit `[data.machine]` in `~/.config/chezmoi/chezmoi.toml`
and run `chezmoi apply`, or delete the key and run `chezmoi init` to be asked again.

Wallpapers: put images into `~/Pictures/Wallpapers` (subfolders work) and press
`SUPER+W`. Until then a gradient in the theme colors is generated.

## B. Full layout from scratch

Boot the Arch ISO, then (replace `/dev/nvme0n1`; partition 1 = ESP, 2 = root):

```sh
# Partitions: 1 GiB EFI + the rest for LUKS
sgdisk -n1:0:+1G -t1:ef00 -n2:0:0 -t2:8309 /dev/nvme0n1
mkfs.fat -F32 /dev/nvme0n1p1
cryptsetup luksFormat /dev/nvme0n1p2
cryptsetup open /dev/nvme0n1p2 root
mkfs.btrfs /dev/mapper/root

# Subvolumes: @ (root), @home, @snapshots (outside @, survives a rollback).
# @games (~/Games) and a ~/.cache subvolume are added on the first chezmoi apply.
mount /dev/mapper/root /mnt
btrfs subvolume create /mnt/{@,@home,@snapshots}
umount /mnt
o=noatime,compress=zstd:1
mount -o $o,subvol=@ /dev/mapper/root /mnt
mount --mkdir -o $o,subvol=@home /dev/mapper/root /mnt/home
mount --mkdir -o $o,subvol=@snapshots /dev/mapper/root /mnt/.snapshots
mount --mkdir /dev/nvme0n1p1 /mnt/boot

# AMD CPU: amd-ucode instead of intel-ucode
pacstrap -K /mnt base linux linux-firmware intel-ucode btrfs-progs mkinitcpio grub efibootmgr networkmanager sudo git neovim
genfstab -U /mnt >> /mnt/etc/fstab
arch-chroot /mnt
```

Inside the chroot: timezone, locale, hostname, root password, your user in
`wheel` (`EDITOR=nvim visudo`), then the UKI:

```sh
# HOOKS in /etc/mkinitcpio.conf:
#   base udev autodetect microcode modconf kms keyboard keymap consolefont block encrypt filesystems
echo "cryptdevice=PARTUUID=$(blkid -s PARTUUID -o value /dev/nvme0n1p2):root:allow-discards,no-read-workqueue,no-write-workqueue root=/dev/mapper/root rootflags=subvol=@ rw quiet" > /etc/kernel/cmdline
# /etc/mkinitcpio.d/linux.preset: comment the *_image lines, uncomment
#   default_uki="/boot/EFI/Linux/arch-linux.efi"
mkdir -p /boot/EFI/Linux && mkinitcpio -P
grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=GRUB
systemctl enable NetworkManager
exit; reboot
```

Log in as your user and continue with **A**, answering **yes** to "Manage the
boot chain". The defaults it offers (EFI UUID, kernel command line) are read
from the running system; also set the console keymap and the native panel
resolution for GRUB. From then on the repo owns `/etc/kernel/cmdline`,
`/etc/vconsole.conf` and GRUB: the menu shows only "Arch Linux" (chainloads the
UKI) and, if you said so, "Windows".

Snapshot rollback and other root-level details: [system-changes.md](system-changes.md).

## After the first login

- `SUPER+H` shows every shortcut.
- `dots-check` reports anything not tracked by the repo.
- Working with the repo day to day: [cheatsheet.md](cheatsheet.md).
- Optional: [Claude Code](https://claude.com/claude-code) for the `SUPER+C` scratchpad and
  the bar pet (hooks: see the cheatsheet). Without it the pet just sleeps.
