local v = require("vars")
local mod = "SUPER" -- the physical left Alt key (Alt and Super are swapped, see vars.lua)
local run = function(cmd)
    return hl.dsp.exec_cmd(v.launch .. cmd)
end
-- bind(keys, action, description[, extra options]): binds with a description show
-- up in the shortcut overview (SUPER+H, built from `hyprctl binds`), grouped into
-- cards by the last group() call above them
local group_name = "Other"
local function group(name)
    group_name = name
end
local function bind(keys, action, desc, opts)
    opts = opts or {}
    opts.description = desc and (group_name .. ": " .. desc) or nil
    hl.bind(keys, action, opts)
end

group("Apps")
bind(mod .. " + Q", run(v.terminal), "Terminal")
bind(mod .. " + B", run(v.browser), "Browser")
bind(mod .. " + E", run(v.fileManager), "File manager")
-- Discord: jump straight to its window (looked up here, no process to start);
-- without one, focus-or-run starts it and switches once the window is there
bind(mod .. " + D", function()
    for _, w in ipairs(hl.get_windows()) do
        if w.class == "discord" and not w.workspace.special then
            hl.dispatch(hl.dsp.focus({ window = w }))
            return
        end
    end
    hl.dispatch(run(v.bin .. "focus-or-run discord discord"))
end, "Discord")
bind(mod .. " + space", run(v.menu), "App launcher / web")
bind(mod .. " + V", run(v.bin .. "rofi-clipboard"), "Clipboard history")
bind(mod .. " + Return", run(v.bin .. "rofi-websearch"), "Web search")
bind(mod .. " + W", run(v.bin .. "wallpaper pick"), "Wallpaper picker")
bind(mod .. " + H", run(v.bin .. "keybinds"), "This overview")

-- Menus (the same menus open under the mouse when clicked in the bar)
group("Menus")
bind(mod .. " + Escape", run(v.bin .. "rofi-power"), "Power menu")
bind(mod .. " + P", run(v.bin .. "power-profile menu"), "Power profile")
bind(mod .. " + N", run(v.bin .. "rofi-wifi"), "Wi-Fi")
bind(mod .. " + SHIFT + B", run(v.bin .. "rofi-bluetooth"), "Bluetooth")
bind(mod .. " + A", run(v.bin .. "rofi-volume"), "Audio output / mute")
bind(mod .. " + O", run(v.bin .. "music show"), "Spotify (show / hide)")
bind(mod .. " + G", hl.dsp.exec_cmd(v.bin .. "game-watch toggle"), "Game mode for this window")
group("Session")
bind(mod .. " + L", hl.dsp.exec_cmd("loginctl lock-session"), "Lock screen")
bind(mod .. " + M", hl.dsp.exec_cmd("uwsm stop"), "Log out") -- uwsm stops all apps cleanly

-- Windows
group("Windows")
bind(mod .. " + X", function()
    local win = hl.get_active_window()
    local keep = win and v.keepAlive[string.lower(win.class or "")]
    if keep then
        -- Spotify / Discord keep their window (vars.lua): Spotify hides (back with
        -- SUPER+O or the music icon), Discord goes back to the previous workspace
        hl.dispatch(keep)
    else
        hl.dispatch(hl.dsp.window.close())
    end
end, "Close window (Spotify / Discord: keep running)")
bind(mod .. " + SHIFT + X", hl.dsp.window.close(), "Really close (Spotify too)")
bind(mod .. " + F", hl.dsp.window.float({ action = "toggle" }), "Float / tile window")
bind(mod .. " + SHIFT + F", hl.dsp.window.fullscreen({ mode = "fullscreen" }), "Fullscreen")
bind(mod .. " + CTRL + Return", hl.dsp.layout("swapwithmaster master"), "Main window")

-- Focus and move with arrow keys (only the first gets a description: one
-- line per group in the overview instead of four)
for n, dir in ipairs({ "left", "right", "up", "down" }) do
    local first = n == 1
    bind(mod .. " + " .. dir, hl.dsp.focus({ direction = dir }), first and "Focus window" or nil)
    bind(mod .. " + SHIFT + " .. dir, hl.dsp.window.move({ direction = dir }), first and "Move window" or nil)
end

-- Workspaces 1-10
group("Workspaces")
for i = 1, 10 do
    local key = i % 10
    local first = i == 1
    bind(mod .. " + " .. key, hl.dsp.focus({ workspace = i }), first and "Go to workspace" or nil)
    bind(mod .. " + SHIFT + " .. key, hl.dsp.window.move({ workspace = i }), first and "Send window" or nil)
end
bind(mod .. " + mouse_down", hl.dsp.focus({ workspace = "e+1" }), "Next workspace")
bind(mod .. " + mouse_up", hl.dsp.focus({ workspace = "e-1" }), "Previous workspace")

-- Mouse: drag to move, right-drag to resize
group("Windows")
bind(mod .. " + mouse:272", hl.dsp.window.drag(), "Move window", { mouse = true })
bind(mod .. " + mouse:273", hl.dsp.window.resize(), "Resize window", { mouse = true })

-- "Minimize": SUPER+S sends the window away, or brings it back if it is
-- already minimized. SUPER+SHIFT+S shows/hides all minimized windows.
bind(mod .. " + S", function()
    local win = hl.get_active_window()
    if win and win.workspace and win.workspace.special then
        local ws = hl.get_active_workspace()
        hl.dispatch(hl.dsp.workspace.toggle_special("minimized"))
        hl.dispatch(hl.dsp.window.move({ window = win, workspace = ws.id, follow = true }))
    elseif win then
        hl.dispatch(hl.dsp.window.move({ workspace = "special:minimized", follow = false }))
    end
end, "Minimize / restore window")
bind(mod .. " + SHIFT + S", hl.dsp.workspace.toggle_special("minimized"), "Minimized windows")

group("Apps")
-- Dropdown terminal: SUPER+Tab (physically Alt+Tab) toggles it, (re)starting it if needed
bind(mod .. " + Tab", function()
    for _, w in ipairs(hl.get_windows()) do
        if w.class == v.dropdown.class then
            hl.dispatch(hl.dsp.workspace.toggle_special("dropdown"))
            return
        end
    end
    -- Not running: just start it, the window rule opens the special workspace
    hl.dispatch(hl.dsp.exec_cmd(v.launch .. v.terminal .. " --class " .. v.dropdown.class))
end, "Dropdown terminal")

group("Screenshots")
-- Screenshots: Home = select area -> clipboard, SHIFT+Home = whole screen -> file
bind("Home", hl.dsp.exec_cmd([[grim -g "$(slurp -d)" - | wl-copy]]), "Area to clipboard")
bind(
    "SHIFT + Home",
    hl.dsp.exec_cmd("mkdir -p " .. v.screenshotDir .. " && grim " .. v.screenshotDir .. "/$(date +%F_%H-%M-%S).png"),
    "Screen to file"
)

-- Media and brightness keys (work on the lock screen too)
local held = { locked = true, repeating = true }
hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd("wpctl set-volume -l 1 @DEFAULT_AUDIO_SINK@ 5%+"), held)
hl.bind("XF86AudioLowerVolume", hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-"), held)
hl.bind("XF86AudioMute", hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"), { locked = true })
hl.bind("XF86AudioMicMute", hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle"), { locked = true })
hl.bind("XF86MonBrightnessUp", hl.dsp.exec_cmd("brightnessctl -e2 -n1 set 5%+"), held)
hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd("brightnessctl -e2 -n1 set 5%-"), held)
hl.bind("XF86AudioPlay", hl.dsp.exec_cmd("playerctl play-pause"), { locked = true })
hl.bind("XF86AudioPause", hl.dsp.exec_cmd("playerctl play-pause"), { locked = true })
hl.bind("XF86AudioNext", hl.dsp.exec_cmd("playerctl next"), { locked = true })
hl.bind("XF86AudioPrev", hl.dsp.exec_cmd("playerctl previous"), { locked = true })
