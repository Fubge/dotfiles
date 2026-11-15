"""User settings made in the system menu (~/.local/bin/system-menu).

They live in ~/.local/state/slate/settings.json, outside the chezmoi repo:
chezmoi never overwrites them and every machine keeps its own (monitors,
mice and taste differ). Next to it, settings.lua is the same data as a Lua
table: Hyprland's config (hypr/settings.lua) reads that one at start and
whenever the menu calls Slate.apply(section) through `hyprctl eval`.

Only what the user changed is stored. Everything else keeps the default from
the repo (hypr/input.lua, hypr/monitors.lua, idle-config, nightlight), so a
new default in the repo still reaches machines that never touched it.

Sections: displays, mouse, touchpad, keyboard, nightlight, idle.
"""
import json
import os

DIR = os.path.expanduser("~/.local/state/slate")
JSON = os.path.join(DIR, "settings.json")
LUA = os.path.join(DIR, "settings.lua")


def load():
    try:
        with open(JSON) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def get(section):
    return load().get(section, {})


def save(data):
    os.makedirs(DIR, exist_ok=True)
    for path, text in ((JSON, json.dumps(data, indent=2, sort_keys=True) + "\n"),
                       (LUA, "-- written by system-menu, do not edit (settings.json is the source)\n"
                             "return " + to_lua(data) + "\n")):
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            f.write(text)
        os.replace(tmp, path)


def update(section, values):
    """Merge values into a section; a value of None removes the key
    (back to the default). Returns the whole new section."""
    data = load()
    sec = data.setdefault(section, {})
    for k, v in values.items():
        if v is None:
            sec.pop(k, None)
        else:
            sec[k] = v
    save(data)
    return sec


def to_lua(v, indent=0):
    pad = "    " * (indent + 1)
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, str):
        return json.dumps(v)        # "..." with \" and \\ escapes: valid Lua too
    if isinstance(v, (list, tuple)):
        return "{ " + ", ".join(to_lua(x, indent) for x in v) + " }"
    if isinstance(v, dict):
        if not v:
            return "{}"
        rows = [f"{pad}[{json.dumps(str(k))}] = {to_lua(x, indent + 1)}," for k, x in v.items()]
        return "{\n" + "\n".join(rows) + "\n" + "    " * indent + "}"
    return "nil"
