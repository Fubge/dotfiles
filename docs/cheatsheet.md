# Cheatsheet: working with these dotfiles

The repo (`~/.local/share/chezmoi`) is the source of truth. `chezmoi apply`
copies it to the system (`~/.config`, `~/.local/bin`, ...). Changes made only on
the system are unknown to the repo until you add them.

Run **`dots-check`** any time to see what is not tracked yet.

## Change a config

```sh
chezmoi edit ~/.config/hypr/binds.lua   # edit the repo copy (opens $EDITOR)
chezmoi apply                           # write it to the system
# or both at once:
chezmoi edit --apply ~/.config/hypr/binds.lua
```

Edited the file in `~/.config` directly (or a program rewrote it)?

```sh
chezmoi diff      # show differences
chezmoi re-add    # copy system changes back into the repo
```

Files ending in `.tmpl` in the repo (e.g. `hyprpaper.conf.tmpl`) are templates:
always edit them with `chezmoi edit`, never with `re-add`.

## Track a new config file

```sh
chezmoi add ~/.config/someapp/config.toml
```

## Install a package

1. Add its name to the matching list in `packages/` (`base`, `hardware`,
   `desktop`, `shell`, `apps`, `gaming`, `dev`).
2. `chezmoi apply` installs everything that is missing.

Installed something with `sudo pacman -S` first? Add it to a list afterwards,
otherwise a fresh install will not have it. `dots-check` lists such packages.

AUR packages (only `packages/aur.txt`, keep it tiny) are never updated by
`pacman -Syu`. Run `aur-update` now and then; it shows the PKGBUILD changes and
asks before building. One stops starting after a system update? `aur-update --rebuild`.

## Stream to a TV

Miracast (Samsung "Screen Mirroring", most smart TVs): open **Network Displays**
(`gnome-network-displays`), pick the TV, confirm on the TV. Picture and sound both
go to the TV, so they stay in sync. Hotel TVs often block it: take an HDMI cable.
Keep watching with the lid closed: power popup -> "Keep running with lid closed"
(screen goes dark; the Wi-Fi antennas sit in the lid, so leave it a crack open
if the picture stutters).

Needs NetworkManager on `wpa_supplicant` (Wi-Fi Direct). No Wi-Fi after a reboot?
Ctrl+Alt+F3, log in, `sudo wifi-backend iwd`, reboot: back on iwd.

## Save and upload

```sh
dots                  # alias for `chezmoi cd` (shell inside the repo)
git status
git add -A
git commit -m "Describe the change"
git push
exit
```

## Other situations

| Situation | Command |
|---|---|
| Get changes from GitHub (other machine) | `chezmoi update` |
| Anything out of sync? | `dots-check` / `chezmoi status` |
| New machine | see [install.md](install.md) |
| Displays, mouse, keyboard, night light, idle times | `SUPER+ALT+Space` (system menu), see below |
| Change machine settings (keyboard, GPU, monitor, ...) | edit `[data.machine]` in `~/.config/chezmoi/chezmoi.toml`, then `chezmoi apply` |
| Changed something outside `$HOME` (`/etc`, ...) | note it in `docs/system-changes.md` |
| Roll back the system after a broken update | see `docs/system-changes.md` |

## Change colors, gaps, rounding or fonts

All apps read the same files:

- `.chezmoidata/palette.toml` - every color (accent, backgrounds, text, ...)
- `.chezmoidata/design.toml` - rounding, border width, gaps, fonts
- `.chezmoidata/locale.toml` - every visible text (popups, bar, notifications,
  shortcut descriptions), German and English side by side; which one is used
  is `lang` in `~/.config/chezmoi/chezmoi.toml`. `chezmoi apply` restarts popups and waybar

Edit them (`dots`, then `nvim .chezmoidata/palette.toml`), run `chezmoi apply`,
then reload: `hyprctl reload`, `systemctl --user restart waybar`, restart kitty/apps.
Files ending in `.tmpl` are generated from these values.

## Wallpapers

- `SUPER+W` opens the picker: pick an image, or "Shuffle" (new image every 30 min).
- Your own images: drop them into `~/Pictures/Wallpapers` (subfolders work).
- Every login picks a random desktop image and a different one for the next login screen (`wallpaper-random.service`). A menu choice holds until the next login.
- Login screen background: SUPER+W, then Shift+Enter (Ctrl+Enter = desktop and login). Stored in `/var/lib/login-wallpaper` (user-owned); `machine.login_wallpaper` in `~/.config/chezmoi/chezmoi.toml` only seeds it.

## Shortcuts and menus

- **SUPER** is the Windows key, everywhere, games included (no Alt/Super swap).
- **`SUPER+H`** lists every shortcut (built live from the descriptions in `hypr/binds.lua`).
- The popups below open in the middle of the screen from their shortcut and under
  the mouse from their bar icon; a second click on the icon closes them, Escape too.
  Each one opens with a small entrance (the title types itself like the lock screen
  greeting, the rows slide in one after the other); running things breathe or spin.
- **Wi-Fi** (`SUPER+N` or a click on the network icon; right click opens `nmtui`):
  on/off switch, the network in use (click: signal, band, Disconnect, Auto-join,
  Forget), saved networks in range, other networks. Opening it scans (again every
  20 s while open). A new secured network asks for its password right in its row;
  a wrong one brings the field back. Hidden and enterprise networks: "Network
  settings" (nm-connection-editor).
- **Power** (`SUPER+P` or a click on the profile or battery icon): battery level, time
  left / until full, draw, health and charge limit; the three power profiles.
- **Session** (`SUPER+Escape` or the power button at the right end of the bar), always in
  the middle of the screen: the greeting types itself like on the lock screen, round
  buttons for Lock, Suspend, Log out, Reboot, Shut down (keys L S E R P). The last three
  turn red and ask for a second click.
- **System menu** (`SUPER+ALT+Space`), centered: a grid of round tiles with a live
  status each. Wi-Fi, Bluetooth, Sound, Power and Shortcuts open their popups,
  Wallpaper the picker, Updates runs `sudo pacman -Syu` in a terminal (the tile counts
  pending updates via `checkupdates`). The rest are pages in the menu itself; Escape
  goes back. Everything applies at once:
  - *Displays*: the screens to scale (click one), main screen (gets workspaces 1-8,
    the laptop gets 9), arrangement left / right / above / below / mirror / off,
    resolution, refresh rate, scale, adaptive sync, laptop panel off while a screen is
    attached. Changes to the picture ask "keep?" and undo themselves after 15 s.
    Screens are remembered by their description, so port or dock do not matter; a new
    screen sits right of the laptop with its preferred mode until set up.
  - *Mouse & touchpad*: speed, acceleration, scroll speed and direction (mice and
    touchpad apart), left-handed, tap to click, off while typing, right click by two
    fingers or by the bottom right corner.
  - *Keyboard*: layout, repeat delay and rate (with a field to try them), Caps/Escape
    and Alt/Super swaps.
  - *Night light* (`nightlight`, drives `hyprsunset`): off, from sunset (times from the
    time zone's city, 45 min fade), own times, always; warmth slider previews live.
  - *Lock & idle*: when to dim, lock, turn the screen off and suspend, separately for
    charger and battery (`idle-config` writes hypridle's config and switches it when the
    charger comes or goes).

  These settings are machine-local: `~/.local/state/slate/settings.json` (chezmoi never
  touches it; Hyprland reads the `settings.lua` next to it through `hypr/settings.lua`).
  Delete a key there to get the repo default back.
- The right click menus of the Claude pet and the music icon go through `list-menu`,
  a resident list window (`list-menu-popup`); typing filters.
- **Bluetooth** (`SUPER+SHIFT+B` or a click on the Bluetooth icon; right click opens
  `bluetoothctl`): on/off switch, paired devices with battery (click connects or
  disconnects; the arrow next to it opens "Pair again" and "Forget"). "Add a device"
  searches right in the popup, new devices show up live, a click pairs, trusts and
  connects; a passkey to type on a keyboard appears in its row.
- **Clipboard** (`SUPER+V`): history from cliphist, newest first. Images show a
  thumbnail, colors a swatch, links their site. Typing filters; Enter or a click
  copies, Delete or the x removes an entry; "Clear" wipes it all (asks once more).
- **Sound** (`SUPER+A` or a click on the speaker; right click mutes): volume and
  microphone sliders, output device, one slider per app that plays sound, "Open mixer"
  for pavucontrol. Click an icon to mute that slider, `m` mutes the output.
- Clicking the brightness icon opens a slider, with the keyboard backlight levels below
  it on laptops that have one. All these popups and the shortcut overview are small GTK4
  scripts (`wifi-popup`, `bluetooth-popup`, `sound-popup`, `power-popup`, `session-popup`,
  `brightness-popup`, `list-menu-popup`, `pet-picker`, `keybinds`) styled by
  `popups/style.css`. All but the overview stay
  resident and only hide (`~/.local/lib/popup/resident.py`, autostart `--hidden`,
  restarted by `chezmoi apply` when their code changes): they open instantly.

## Claude scratchpad

- **`SUPER+C`** shows / hides one long-running Claude Code session (kitty on
  `special:claude`, started hidden at login). `SUPER+X` only hides it, `SUPER+SHIFT+X`
  ends it. **`SUPER+SHIFT+C`** = small prompt pill, the question goes into that session.
- **`SUPER+T`** = new task for Claude: a small centered popup (`~/.local/bin/task-popup`),
  task text, optional details, tag bug / verbesserung (preselected) / idee (click or Alt+B/V/I), Enter.
  It goes to the end of "## Offen" in the Obsidian note `02 - Linux/Arch Setup/Aufgaben.md`;
  `/todo` in Claude Code works through that list.
- **Calendar** (the two shared Nextcloud calendars, Flauschebär = own, Pia): vdirsyncer
  syncs them every 5 min both ways into `~/.local/share/calendars` (password in the
  keyring: `secret-tool lookup service nextcloud-caldav`).
  - **`SUPER+K`** or click on the bar date = calendar popup:
    Google-style month (event bars / pills), the chosen day right (cards, trash asks first), arrows / PgUp / PgDn / T, N = new event.
    Click a card / double click an event = edit (text, date, time, place, calendar);
    drag an event onto another day = move it. Avatars top right hide / show a calendar.
  - **`SUPER+SHIFT+K`** or right click = new event in one line: "Kino morgen 20 Uhr",
    "Zahnarzt 24.11. 14:30 für 30 min", "Fr 18-20 Grillen", "Urlaub 10.12.-14.12.";
    Alt+F / Alt+P whose calendar, Alt+R reminder.
  - Reminders as notifications (`calendar-remind`): alarms from the events, own timed
    events 15 min before, a "Guten Morgen" with today's events (7-12 Uhr).
  - The new event popup shows the event's week like the month view, the new one glowing.
- **Timer** (`SUPER+SHIFT+T` or click on the countdown): kitchen-timer dial, type
  "Pizza 12", "25 min Fokus", "1h 30", "2:30" (a bare number = minutes), ↑/↓ or scroll
  = ±1 min (Shift ±5), six presets start right away (Alt+1..6: Ei, Tee, Nudeln, Pizza,
  Pause, Fokus; hover shows their time on the dial). Running timers as cards: pause,
  +1 min, stop. While one runs, a tab with the countdown hangs below the middle of the bar
  (click = popup, right click = pause / go on); when one is up it turns red, a
  notification stays (+ 5 Min / Aus) and the alarm sounds up to three times; right click
  on the red tab = quiet.
- A little pixel pet left of the window title shows its state: sleeps while Claude
  is off, potters about when ready (dozes at night), mines / types / thinks while
  working, jumps with a "!" when it needs you, cheers and shows a gem when it finished
  while hidden (plus a notification). Right click = new chat, resume, restart, quit,
  "Choose pet" (popup with live previews: Mochi fluffball, Kitty, Bunny; ←/→ + Enter or
  click; `claude-pad pet NAME`, `~/.local/bin/pet-picker`). Clicking it also
  makes it hop. Each animation is only as wide as it needs, the title glides. Script:
  `~/.local/bin/claude-pad`; the pets are drawn in `~/.local/lib/pet/pet.py`
  (`pet.py sheet FILE` = contact sheet), frames are rendered into
  `~/.config/waybar/pet` by a chezmoi run script.
- It runs in this repo, not in `~`: Claude Code never remembers the trust prompt for
  the home folder. Its memory folder is a symlink so it shares the home one:
  `~/.claude/projects/-home-<user>--local-share-chezmoi/memory -> ../-home-<user>/memory`.
- The state comes from hooks in `~/.claude/settings.json` (not in this repo: Claude
  Code rewrites that file). On a new machine add for each event
  `[ -z "$CLAUDE_PAD" ] || ~/.local/bin/claude-pad hook EV`:
  SessionStart `start`, UserPromptSubmit `prompt`, PostToolUse `tool`, Stop `stop`,
  SessionEnd `end`, PreToolUse (matcher `AskUserQuestion`) and Notification
  (matcher `permission_prompt|elicitation_dialog`) `ask`.

## Gaming

- **Install all games into `~/Games`.** It is its own btrfs subvolume (`@games`),
  so games never end up in snapshots or backups. Steam: Settings > Storage > add
  `~/Games/Steam` as a library and make it the default. Heroic and Lutris use
  `~/Games` out of the box. `~/.cache` is a subvolume for the same reason.
- **Nothing to set up per game.** `game-watch` (started with Hyprland) spots games by
  how they run, not by name: started by a launcher (Steam, Modrinth App,
  `umu-run`, gamescope, ...), running under Wine/Proton, or Minecraft. It turns on
  GameMode for them: performance power profile, ends when the game exits
  (`gamemode-hook`).
- **`SUPER+G`** marks / unmarks the focused window as a game, for anything not caught.
- Steam launch option: just `mangohud %command%` (no `gamemoderun`).
- Newest GE-Proton for Steam: run `update-proton-ge`, restart Steam, then pick it under
  Properties > Compatibility.
- Minecraft: **Modrinth App** (instances: Vanilla or Fabric + Sodium for more FPS).
- A single Windows `.exe` (GOG, ...): `umu-run game.exe`
  (uses GE-Proton). A new launcher only needs its process name in `LAUNCHERS` in
  `~/.local/bin/game-watch`.
