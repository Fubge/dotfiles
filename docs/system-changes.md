# System changes outside of $HOME

Files under `system/` in this repo are installed to `/` automatically by
`run_onchange_after_40-system-files.sh.tmpl` (needs sudo). Everything in the
table below was changed by hand; `bootstrap.sh` will automate these later.

| Managed file (from `system/`) | Purpose |
|---|---|
| `/usr/local/bin/power-profile-auto` | performance on AC, power-saver on battery |
| `/etc/udev/rules.d/99-power-profile.rules` | runs it when the charger is plugged in/out |
| `/etc/systemd/system/power-profile-auto.service` | runs it at boot |
| `/usr/share/sddm/themes/slate/` | login screen theme (`theme.conf` + `background.jpg` generated from the palette) |
| `/etc/sddm.conf.d/10-theme.conf` | selects the theme, cursor, 2x HiDPI for the greeter |
| `/etc/kernel/cmdline` | kernel command line baked into the UKI: LUKS root, `quiet loglevel=3` (no kernel messages over the LUKS prompt); changing it rebuilds the UKI |
| `/etc/default/grub` | native 2880x1800 gfxmode, theme, hides the firmware's BootNext entries |
| `/etc/grub.d/40_custom` | the only two menu entries: Arch Linux (chainloads the UKI) and Windows 11 |
| `/boot/grub/themes/slate/` | GRUB theme, generated from the palette by `run_onchange_after_42-grub-theme.sh.tmpl` |
| `/etc/vconsole.conf` | keymap + Terminus 32px console font (LUKS prompt, TTYs); changing it rebuilds the UKI |

If GRUB ever fails to boot Arch: press F12 at power-on and pick the firmware's
"ArchLinux" entry, or press C in GRUB and run
`search --fs-uuid --set=root D679-77CD; chainloader /EFI/Linux/arch-linux.efi; boot`.

If the login screen ever breaks: switch to a text console with Ctrl+Alt+F3,
log in, run `sudo rm /etc/sddm.conf.d/10-theme.conf` and reboot.

| File / unit | Change | Why |
|---|---|---|
| `/etc/pacman.conf` | `[multilib]`, `ParallelDownloads = 10`, `VerbosePkgLists` | Steam, faster downloads |
| `reflector.timer`, `paccache.timer` | enabled | Fresh mirrors, trimmed package cache |
| `/etc/snapper/configs/root` | no timeline, `NUMBER_LIMIT=10`, `SPACE_LIMIT=0.2`, `FREE_LIMIT=0.3` | Lean pre/post-pacman snapshots of `/` only |
| `/etc/fstab` | `@snapshots` subvolume mounted at `/.snapshots` | Snapshots survive a rollback of `@` |
| `fstrim.timer` | enabled | Weekly TRIM |
| `/etc/grub.d/15_uki` | removed (by the GRUB theme script) | Replaced by the explicit entry in `40_custom` |
| `/etc/grub.d/30_uefi-firmware` | `chmod -x` (by the GRUB theme script) | Hides "UEFI Firmware Settings"; a `grub` update restores it until the script runs again |
| user `raphael` | login shell `/usr/bin/zsh` (`chsh`) | zsh as interactive shell |
| user `raphael` | added to group `gamemode` | GameMode daemon permissions |

## Rollback (root snapshot)

GRUB boots a UKI from the ESP, which is not part of any snapshot, so snapshots
are not bootable from the GRUB menu. To roll back from an Arch ISO:

```sh
cryptsetup open /dev/disk/by-partuuid/be6d10ae-1e30-438c-93ed-68e60cbd28cf root
mount -o subvolid=5 /dev/mapper/root /mnt
mv /mnt/@ /mnt/@broken
btrfs subvolume snapshot /mnt/@snapshots/<N>/snapshot /mnt/@
umount /mnt
mount -o subvol=@ /dev/mapper/root /mnt && mount /dev/nvme0n1p1 /mnt/boot
arch-chroot /mnt mkinitcpio -P   # rebuild UKI from the snapshot's kernel
```
