# System changes outside of $HOME

Files under `system/` (every machine) and `system-boot/` (only with
`machine.boot = true`, see [install.md](install.md)) are installed to `/` by
`.chezmoiscripts/run_onchange_after_40-system-files.sh.tmpl` (needs sudo); `*.tmpl` files are
rendered with the values from `chezmoi init` first. The second table
below is handled by `bootstrap.sh` (pacman.conf, services, ufw, snapper, shell, groups);
only fstab and the GRUB tweaks come from the base install and the GRUB theme script.

| Managed file (from `system/`, `system-boot/`) | Purpose |
|---|---|
| `/usr/local/bin/power-profile-auto` | performance on AC, power-saver on battery |
| `/etc/udev/rules.d/99-power-profile.rules` | runs it when the charger is plugged in/out |
| `/etc/systemd/system/power-profile-auto.service` | runs it at boot |
| `/etc/sysctl.d/99-performance.conf` | zram-friendly swapping (`swappiness 180`, `page-cluster 0`), no NMI watchdog, no split-lock penalty for games |
| `/etc/systemd/journald.conf.d/size.conf` | journal capped at 200 MB |
| `/usr/share/sddm/themes/slate/` | login screen theme (`theme.conf` + `background.jpg` generated from the palette) |
| `/etc/sddm.conf.d/10-theme.conf` | selects the theme, cursor, greeter DPI = 96 x `machine.monitor_scale` |
| `/etc/kernel/cmdline` | *boot only*: `machine.cmdline`, the kernel command line baked into the UKI: LUKS root (`allow-discards,no-read-workqueue,no-write-workqueue`: TRIM and lower NVMe latency, dm-crypt works inline instead of queueing), `quiet loglevel=3` (no kernel messages over the LUKS prompt), `cfg80211.ieee80211_regdom=DE` (global Wi-Fi country for adapters without their own; Intel cards take it from their firmware); changing it rebuilds the UKI |
| `/etc/default/grub` | *boot only*: native gfxmode (`machine.grub_resolution`), theme, hides the firmware's BootNext entries |
| `/etc/grub.d/40_custom` | *boot only*: the only menu entries: Arch Linux (chainloads the UKI) and optionally Windows |
| `/boot/grub/themes/slate/` | *boot only*: GRUB theme, generated from the palette by `.chezmoiscripts/run_onchange_after_42-grub-theme.sh.tmpl` |
| `/etc/vconsole.conf` | *boot only*: console keymap + Terminus font (LUKS prompt, TTYs); changing it rebuilds the UKI |

If GRUB ever fails to boot Arch: press F12 at power-on and pick the firmware's
"ArchLinux" entry, or press C in GRUB and run
`search --fs-uuid --set=root <ESP-UUID>; chainloader /EFI/Linux/arch-linux.efi; boot`
(the UUID is `machine.esp_uuid` in `~/.config/chezmoi/chezmoi.toml`).

If the login screen ever breaks: switch to a text console with Ctrl+Alt+F3,
log in, run `sudo rm /etc/sddm.conf.d/10-theme.conf` and reboot.

| File / unit | Change | Why |
|---|---|---|
| `/etc/pacman.conf` | `[multilib]`, `ParallelDownloads = 10`, `VerbosePkgLists` | Steam, faster downloads |
| `reflector.timer`, `paccache.timer` | enabled | Fresh mirrors, trimmed package cache |
| `/etc/snapper/configs/root` | no timeline, `NUMBER_LIMIT=10`, `SPACE_LIMIT=0.2`, `FREE_LIMIT=0.3` | Lean pre/post-pacman snapshots of `/` only |
| `/etc/fstab` | `@snapshots` subvolume mounted at `/.snapshots` | Snapshots survive a rollback of `@` |
| `/etc/fstab` | btrfs mounts with `noatime,compress=zstd:1` | No metadata write on every file read; fast transparent compression (fewer bytes through dm-crypt) |
| `NetworkManager-wait-online.service` | disabled (by the system-files script) | Nothing waits for the network at boot |
| `fstrim.timer` | enabled | Weekly TRIM |
| `/etc/grub.d/15_uki` | removed (by the GRUB theme script) | Replaced by the explicit entry in `40_custom` |
| `/etc/grub.d/30_uefi-firmware` | `chmod -x` (by the GRUB theme script) | Hides "UEFI Firmware Settings"; a `grub` update restores it until the script runs again |
| your user | login shell `/usr/bin/zsh` (`chsh`) | zsh as interactive shell |
| your user | added to group `gamemode` | GameMode daemon permissions |

## Rollback (root snapshot)

GRUB boots a UKI from the ESP, which is not part of any snapshot, so snapshots
are not bootable from the GRUB menu. To roll back from an Arch ISO:

```sh
cryptsetup open /dev/disk/by-partuuid/<LUKS-PARTUUID> root
mount -o subvolid=5 /dev/mapper/root /mnt
mv /mnt/@ /mnt/@broken
btrfs subvolume snapshot /mnt/@snapshots/<N>/snapshot /mnt/@
umount /mnt
mount -o subvol=@ /dev/mapper/root /mnt && mount /dev/<ESP> /mnt/boot
arch-chroot /mnt mkinitcpio -P   # rebuild UKI from the snapshot's kernel
```
