-- Hyprland entry point. Everything lives in modules next to this file.
-- Tunables (apps, colors, sizes) are in vars.lua.

-- vars is only required by the other modules, so a config reload kept the old
-- copy cached: drop it, every reload then sees changed vars
package.loaded["vars"] = nil

require("env")
require("monitors")
require("look")
require("input")
require("binds")
require("rules")
require("autostart")
