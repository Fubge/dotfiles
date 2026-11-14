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
2. List the open tasks to the user in one short block with a one-line plan each, and say
   which ones you would do now. Ideas (`#idee`) and anything invasive need an OK first.
3. Work through them one by one, following the repo conventions and memory rules
   (no kernel changes, no live network restarts, spell out invasive steps first).
   One commit per task, message in English.
4. Update the note after each task:
   - Done: change `- [ ]` to `- [x]`, append ` ✅ YYYY-MM-DD` (Tasks plugin format),
     add an indented sub-bullet `- Claude: <what was changed, commit hash>` in German,
     move the item (with its sub-bullets) to `## Erledigt` (newest on top).
   - Needs input from the user: leave it under Offen, add an indented sub-bullet `- ❓ <question>` in German.
   - Needs a reboot/relogin to take effect: say so in the Claude sub-bullet.
5. Edit the note with the Edit tool only (it syncs via Nextcloud; never rewrite the whole file,
   the user may be editing it on another device).
6. End with a short summary in German.
