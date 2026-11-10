local v   = require("vars")
local mod = "SUPER"
local run = function(cmd) return hl.dsp.exec_cmd(v.launch .. cmd) end

-- Apps
hl.bind(mod .. " + Q",     run(v.terminal))
hl.bind(mod .. " + B",     run(v.browser))
hl.bind(mod .. " + E",     run(v.fileManager))
hl.bind(mod .. " + D",     run("discord"))
hl.bind(mod .. " + space", run(v.menu))

-- Windows
hl.bind(mod .. " + X",   hl.dsp.window.close())
hl.bind(mod .. " + F",   hl.dsp.window.float({ action = "toggle" }))
hl.bind(mod .. " + Tab", hl.dsp.window.fullscreen({ mode = "fullscreen" }))
hl.bind(mod .. " + CTRL + Return", hl.dsp.layout("swapwithmaster master"))

-- Session (uwsm takes care of stopping all apps cleanly)
hl.bind(mod .. " + M", hl.dsp.exec_cmd("uwsm stop"))

-- Focus and move with arrow keys
for _, dir in ipairs({ "left", "right", "up", "down" }) do
    hl.bind(mod .. " + " .. dir,           hl.dsp.focus({ direction = dir }))
    hl.bind(mod .. " + SHIFT + " .. dir,   hl.dsp.window.move({ direction = dir }))
end

-- Workspaces 1-10
for i = 1, 10 do
    local key = i % 10
    hl.bind(mod .. " + " .. key,         hl.dsp.focus({ workspace = i }))
    hl.bind(mod .. " + SHIFT + " .. key, hl.dsp.window.move({ workspace = i }))
end
hl.bind(mod .. " + mouse_down", hl.dsp.focus({ workspace = "e+1" }))
hl.bind(mod .. " + mouse_up",   hl.dsp.focus({ workspace = "e-1" }))

-- Mouse: drag to move, right-drag to resize
hl.bind(mod .. " + mouse:272", hl.dsp.window.drag(),   { mouse = true })
hl.bind(mod .. " + mouse:273", hl.dsp.window.resize(), { mouse = true })

-- "Minimize": SUPER+S sends the window away, or brings it back if it is
-- already minimized. SUPER+SHIFT+S shows/hides all minimized windows.
hl.bind(mod .. " + S", function()
    local win = hl.get_active_window()
    if win and win.workspace and win.workspace.special then
        local ws = hl.get_active_workspace()
        hl.dispatch(hl.dsp.workspace.toggle_special("minimized"))
        hl.dispatch(hl.dsp.window.move({ window = win, workspace = ws.id, follow = true }))
    elseif win then
        hl.dispatch(hl.dsp.window.move({ workspace = "special:minimized", follow = false }))
    end
end)
hl.bind(mod .. " + SHIFT + S", hl.dsp.workspace.toggle_special("minimized"))

-- Dropdown terminal: Alt+Tab toggles it, (re)starting it if needed
hl.bind("ALT + Tab", function()
    for _, w in ipairs(hl.get_windows()) do
        if w.class == v.dropdown.class then
            hl.dispatch(hl.dsp.workspace.toggle_special("dropdown"))
            return
        end
    end
    hl.dispatch(hl.dsp.exec_cmd(v.launch .. v.terminal .. " --class " .. v.dropdown.class))
    hl.dispatch(hl.dsp.workspace.toggle_special("dropdown"))
end)

-- Screenshots: Home = select area -> clipboard, SHIFT+Home = whole screen -> file
hl.bind("Home", hl.dsp.exec_cmd([[grim -g "$(slurp -d)" - | wl-copy]]))
hl.bind("SHIFT + Home", hl.dsp.exec_cmd(
    "mkdir -p " .. v.screenshotDir .. " && grim " .. v.screenshotDir .. "/$(date +%F_%H-%M-%S).png"))

-- Media and brightness keys (work on the lock screen too)
local held = { locked = true, repeating = true }
hl.bind("XF86AudioRaiseVolume",  hl.dsp.exec_cmd("wpctl set-volume -l 1 @DEFAULT_AUDIO_SINK@ 5%+"), held)
hl.bind("XF86AudioLowerVolume",  hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-"),      held)
hl.bind("XF86AudioMute",         hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"),     { locked = true })
hl.bind("XF86AudioMicMute",      hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle"),   { locked = true })
hl.bind("XF86MonBrightnessUp",   hl.dsp.exec_cmd("brightnessctl -e4 -n2 set 5%+"),                  held)
hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd("brightnessctl -e4 -n2 set 5%-"),                  held)
hl.bind("XF86AudioPlay",  hl.dsp.exec_cmd("playerctl play-pause"), { locked = true })
hl.bind("XF86AudioPause", hl.dsp.exec_cmd("playerctl play-pause"), { locked = true })
hl.bind("XF86AudioNext",  hl.dsp.exec_cmd("playerctl next"),       { locked = true })
hl.bind("XF86AudioPrev",  hl.dsp.exec_cmd("playerctl previous"),   { locked = true })
