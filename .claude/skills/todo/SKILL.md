---
name: todo
description: Work through the open system tasks (bugs, improvements, ideas) the user collected in the Obsidian note "10 - Linux/Arch Setup/Aufgaben.md". Use when the user types /todo or asks to process the task list.
---

# Process the Arch setup task list

Task file: `~/Nextcloud/Obsidian/10 - Linux/Arch Setup/Aufgaben.md` (German, the user writes it).

Format: checkbox lines under `## Offen`, tagged `#bug`, `#verbesserung` or `#idee`,
optional indented sub-bullets with details. Done items move to `## Erledigt`.

## Steps

1. Read the file. Skip the example line (starts with "Beispiel:"). If nothing is open, say so and stop.
2. The user runs this unattended (before sleeping / while away). Do NOT ask for
   confirmation and do not wait for answers: work through every open task on your own,
   including `#idee`. When something is unclear, pick the sensible default and note it.
3. Work through them one by one, following the repo conventions and memory rules.
   One commit per task, message in English. Do not push.
   Hard limits, even unattended (leave a `❓` sub-bullet instead of doing it):
   - no kernel changes, no live restarts of NetworkManager/iwd/Wi-Fi, no reboot or logout
   - nothing destructive or hard to undo (deleting user data, repartitioning, bootloader)
   - anything that needs sudo/a password: prepare the change in the repo, commit it,
     and note the exact command the user has to run in the sub-bullet
   - do not kill or restart the running Hyprland session or apps the user may have open
4. Update the note after each task:
   - Done: change `- [ ]` to `- [x]`, append ` ✅ YYYY-MM-DD` (Tasks plugin format),
     add an indented sub-bullet `- Claude: <what was changed, commit hash>` in German,
     move the item (with its sub-bullets) to `## Erledigt` (newest on top).
   - Needs input from the user: leave it under Offen, add an indented sub-bullet `- ❓ <question>` in German.
   - Needs a reboot/relogin to take effect: say so in the Claude sub-bullet.
5. Edit the note with the Edit tool only (it syncs via Nextcloud; never rewrite the whole file,
   the user may be editing it on another device).
6. End with a short summary in German.
