# System changes outside of $HOME

Files under `system/` in this repo are installed to `/` automatically by
`run_onchange_after_40-system-files.sh.tmpl` (needs sudo). Everything in the
table below was changed by hand; `bootstrap.sh` will automate these later.

| Managed file (from `system/`) | Purpose |
|---|---|
| `/usr/local/bin/power-profile-auto` | performance on AC, power-saver on battery |
| `/etc/udev/rules.d/99-power-profile.rules` | runs it when the charger is plugged in/out |
| `/etc/systemd/system/power-profile-auto.service` | runs it at boot |

| File / unit | Change | Why |
|---|---|---|
| `/etc/pacman.conf` | `[multilib]`, `ParallelDownloads = 10`, `VerbosePkgLists` | Steam, faster downloads |
| `reflector.timer`, `paccache.timer` | enabled | Fresh mirrors, trimmed package cache |
| `/etc/snapper/configs/root` | no timeline, `NUMBER_LIMIT=10`, `SPACE_LIMIT=0.2`, `FREE_LIMIT=0.3` | Lean pre/post-pacman snapshots of `/` only |
| `/etc/fstab` | `@snapshots` subvolume mounted at `/.snapshots` | Snapshots survive a rollback of `@` |
| `/etc/kernel/cmdline` | `cryptdevice=…:root:allow-discards` | Let TRIM pass through LUKS to the SSD |
| `fstrim.timer` | enabled | Weekly TRIM |
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
