local v = require("vars")
local mod = "SUPER" -- the Windows key
local run = function(cmd)
    return hl.dsp.exec_cmd(v.launch .. cmd)
end
-- Menus and popups start directly: a systemd scope (uwsm app) costs ~0.2 s per
-- press, and they are no apps (resident popups get their command through
-- popup-cmd, ~5 ms; rofi starts apps through uwsm itself, vars.lua M.menu)
local menu = function(cmd)
    return hl.dsp.exec_cmd(cmd)
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
    hl.dispatch(run(v.bin .. "focus-or-run discord " .. v.bin .. "discord-start"))
end, "Discord")
-- Obsidian: same idea, its window lives on workspace 8 (rules.lua). The window
-- class is md.obsidian.Obsidian (it was "obsidian" before 1.15); with the wrong
-- class SUPER+O started a second Obsidian, which only shows the vault picker.
-- The obsidian:// link opens the vault directly, even if Obsidian still runs
-- without a window.
local obsidianVault = "obsidian://open?vault=Obsidian"
bind(mod .. " + O", function()
    for _, w in ipairs(hl.get_windows()) do
        if w.class == "md.obsidian.Obsidian" and not w.workspace.special then
            hl.dispatch(hl.dsp.focus({ window = w }))
            return
        end
    end
    hl.dispatch(run(v.bin .. "focus-or-run md.obsidian.Obsidian obsidian '" .. obsidianVault .. "'"))
end, "Obsidian (notes)")
-- YouTube: workspace 4; reopens the Vivaldi app window if it was closed
-- (rules.lua puts it on workspace 4, so switching there right away is enough)
bind(mod .. " + Y", function()
    local open = false
    for _, w in ipairs(hl.get_windows()) do
        if w.class and w.class:find("^vivaldi%-www%.youtube%.com__") then open = true end
    end
    if not open then hl.dispatch(run(v.browser .. " --app=https://www.youtube.com")) end
    hl.dispatch(hl.dsp.focus({ workspace = "4" }))
end, "YouTube")
bind(mod .. " + space", menu(v.menu), "App launcher / web")
bind(mod .. " + V", menu(v.bin .. "popup-cmd clipboard-popup toggle --center"), "Clipboard history")
bind(mod .. " + Return", menu(v.bin .. "rofi-websearch"), "Web search")
bind(mod .. " + W", menu(v.bin .. "wallpaper pick"), "Wallpaper picker")
bind(mod .. " + H", menu(v.bin .. "popup-cmd keybinds toggle"), "This overview")
bind(mod .. " + C", hl.dsp.exec_cmd(v.bin .. "claude-pad toggle"), "Claude (show / hide)")
bind(mod .. " + SHIFT + C", hl.dsp.exec_cmd(v.bin .. "claude-pad ask"), "Quick question to Claude")
bind(mod .. " + T", menu(v.bin .. "popup-cmd task-popup toggle --center"), "New task for Claude (/todo list)")
bind(mod .. " + K", menu(v.bin .. "popup-cmd calendar-popup toggle --center"), "Calendar (Pia + me)")
bind(mod .. " + SHIFT + K", menu(v.bin .. "popup-cmd event-popup toggle --center"), "New event (\"Kino morgen 20 Uhr\")")
bind(mod .. " + SHIFT + T", menu(v.bin .. "popup-cmd timer-popup toggle --center"), "Timer (\"Pizza 12\")")

-- Menus (the same menus open under the mouse when clicked in the bar)
group("Menus")
bind(mod .. " + ALT + space", menu(v.bin .. "popup-cmd system-menu toggle --center"), "System menu: displays, mouse, keyboard, night light, idle")
bind(mod .. " + Escape", menu(v.bin .. "popup-cmd session-popup toggle --center"), "Lock, suspend, log out, reboot, shut down")
bind(mod .. " + I", menu(v.bin .. "popup-cmd notification-center toggle"), "Notification center")
bind(mod .. " + P", menu(v.bin .. "popup-cmd power-popup toggle --center"), "Power profile, battery")
bind(mod .. " + N", menu(v.bin .. "popup-cmd wifi-popup toggle --center"), "Wi-Fi: networks, password, forget")
bind(mod .. " + SHIFT + B", menu(v.bin .. "popup-cmd bluetooth-popup toggle --center"), "Bluetooth: devices, pairing")
bind(mod .. " + A", menu(v.bin .. "popup-cmd sound-popup toggle --center"), "Sound: volume, outputs, apps")
bind(mod .. " + M", run(v.bin .. "music show"), "Spotify (show / hide)")
bind(mod .. " + G", hl.dsp.exec_cmd(v.bin .. "game-watch toggle"), "Game mode for this window")
group("Session")
bind(mod .. " + L", hl.dsp.exec_cmd("loginctl lock-session"), "Lock screen")
-- Log out behind SHIFT: one stray key would end every app
bind(mod .. " + SHIFT + M", hl.dsp.exec_cmd("uwsm stop"), "Log out") -- uwsm stops all apps cleanly

-- Windows
group("Windows")
bind(mod .. " + X", function()
    local win = hl.get_active_window()
    local keep = win and v.keepAlive[string.lower(win.class or "")]
    if keep then
        -- Spotify / Discord keep their window (vars.lua): Spotify hides (back with
        -- SUPER+M or the music icon), Discord goes back to the previous workspace
        hl.dispatch(keep)
    else
        hl.dispatch(hl.dsp.window.close())
    end
end, "Close window (Spotify / Discord / Claude: keep running)")
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

-- Discord push-to-talk on ^ (the key left of 1, by keycode so the layout does
-- not matter). Discord registers the shortcut through the portal; Hyprland has
-- no approval dialog, the bind here is the approval. Hyprland sends press and
-- release. non_consuming: ^ still types (Neovim's "start of line")
group("Apps")
bind("code:49", hl.dsp.global("discord:discord-push-to-talk"), "Discord push-to-talk (hold ^)",
    { non_consuming = true })

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

-- Waking the screen: hypridle turns it off in the submap "wake" (hypridle.conf),
-- where any key only turns it on again. Without this, the key that wakes it was
-- typed into hyprlock as the first character of the password.
hl.define_submap("wake", function()
    hl.bind("catchall", function()
        hl.dispatch(hl.dsp.dpms({ action = "on" }))
        hl.dispatch(hl.dsp.submap("reset"))
    end, { locked = true })
end)
