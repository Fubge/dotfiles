local v = require("vars")
local S = require("strings") -- descriptions in the chosen language (.chezmoidata/locale.toml)
local mod = "SUPER" -- the Windows key
local run = function(cmd)
    return hl.dsp.exec_cmd(v.launch .. cmd)
end
-- Menus and popups start directly: a systemd scope (uwsm) costs time on every
-- press, and they are no apps (resident popups get their command through
-- popup-cmd, ~5 ms; rofi starts apps through uwsm itself, vars.lua M.menu)
local menu = function(cmd)
    return hl.dsp.exec_cmd(cmd)
end
-- bind(keys, action, description[, extra options]): binds with a description show
-- up in the shortcut overview (SUPER+H, built from `hyprctl binds`), grouped into
-- cards by the last group() call above them
local group_name = S.group_other
local function group(name)
    group_name = name
end
local function bind(keys, action, desc, opts)
    opts = opts or {}
    opts.description = desc and (group_name .. ": " .. desc) or nil
    hl.bind(keys, action, opts)
end

group(S.group_apps)
-- the terminal only asks the running kitty server for a window (vars.lua):
-- nothing to put into a scope, so it starts directly like the menus
bind(mod .. " + Q", menu(v.terminal), S.terminal)
bind(mod .. " + B", run(v.browser), S.browser)
bind(mod .. " + E", run(v.fileManager), S.files)
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
end, S.discord)
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
end, S.obsidian)
-- YouTube: workspace 4; reopens the Vivaldi app window if it was closed
-- (rules.lua puts it on workspace 4, so switching there right away is enough)
bind(mod .. " + Y", function()
    local open = false
    for _, w in ipairs(hl.get_windows()) do
        if w.class and w.class:find("^vivaldi%-www%.youtube%.com__") then open = true end
    end
    if not open then hl.dispatch(run(v.browser .. " --app=https://www.youtube.com")) end
    hl.dispatch(hl.dsp.focus({ workspace = "4" }))
end, S.youtube)
bind(mod .. " + space", menu(v.menu), S.launcher)
bind(mod .. " + V", menu(v.bin .. "popup-cmd clipboard-popup toggle --center"), S.clipboard)
bind(mod .. " + Return", menu(v.bin .. "rofi-websearch"), S.websearch)
bind(mod .. " + W", menu(v.bin .. "wallpaper pick"), S.wallpaper)
bind(mod .. " + H", menu(v.bin .. "popup-cmd keybinds toggle"), S.overview)
bind(mod .. " + C", hl.dsp.exec_cmd(v.bin .. "claude-pad toggle"), S.claude)
bind(mod .. " + SHIFT + C", hl.dsp.exec_cmd(v.bin .. "claude-pad ask"), S.claude_ask)
bind(mod .. " + T", menu(v.bin .. "popup-cmd task-popup toggle --center"), S.task)
bind(mod .. " + K", menu(v.bin .. "popup-cmd calendar-popup toggle --center"), S.calendar)
bind(mod .. " + SHIFT + K", menu(v.bin .. "popup-cmd event-popup toggle --center"), S.event)
bind(mod .. " + SHIFT + T", menu(v.bin .. "popup-cmd timer-popup toggle --center"), S.timer)

-- Menus (the same menus open under the mouse when clicked in the bar)
group(S.group_menus)
bind(mod .. " + ALT + space", menu(v.bin .. "popup-cmd system-menu toggle --center"), S.system)
bind(mod .. " + Escape", menu(v.bin .. "popup-cmd session-popup toggle --center"), S.session)
bind(mod .. " + I", menu(v.bin .. "popup-cmd notification-center toggle"), S.notifications)
bind(mod .. " + P", menu(v.bin .. "popup-cmd power-popup toggle --center"), S.power)
bind(mod .. " + N", menu(v.bin .. "popup-cmd wifi-popup toggle --center"), S.wifi)
bind(mod .. " + SHIFT + B", menu(v.bin .. "popup-cmd bluetooth-popup toggle --center"), S.bluetooth)
bind(mod .. " + A", menu(v.bin .. "popup-cmd sound-popup toggle --center"), S.sound)
bind(mod .. " + M", run(v.bin .. "music show"), S.spotify)
bind(mod .. " + G", hl.dsp.exec_cmd(v.bin .. "game-watch toggle"), S.gamemode)
group(S.group_session)
bind(mod .. " + L", hl.dsp.exec_cmd("loginctl lock-session"), S.lock)
-- Log out behind SHIFT: one stray key would end every app
bind(mod .. " + SHIFT + M", hl.dsp.exec_cmd("uwsm stop"), S.logout) -- uwsm stops all apps cleanly

-- Windows
group(S.group_windows)
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
end, S.close)
bind(mod .. " + SHIFT + X", hl.dsp.window.close(), S.kill)
bind(mod .. " + F", hl.dsp.window.float({ action = "toggle" }), S.float)
bind(mod .. " + SHIFT + F", hl.dsp.window.fullscreen({ mode = "fullscreen" }), S.fullscreen)
bind(mod .. " + CTRL + Return", hl.dsp.layout("swapwithmaster master"), S.master)

-- Focus and move with arrow keys (only the first gets a description: one
-- line per group in the overview instead of four)
for n, dir in ipairs({ "left", "right", "up", "down" }) do
    local first = n == 1
    bind(mod .. " + " .. dir, hl.dsp.focus({ direction = dir }), first and S.focus or nil)
    bind(mod .. " + SHIFT + " .. dir, hl.dsp.window.move({ direction = dir }), first and S.move or nil)
end

-- Workspaces 1-10
group(S.group_workspaces)
for i = 1, 10 do
    local key = i % 10
    local first = i == 1
    bind(mod .. " + " .. key, hl.dsp.focus({ workspace = i }), first and S.workspace or nil)
    bind(mod .. " + SHIFT + " .. key, hl.dsp.window.move({ workspace = i }), first and S.send or nil)
end
bind(mod .. " + mouse_down", hl.dsp.focus({ workspace = "e+1" }), S.ws_next)
bind(mod .. " + mouse_up", hl.dsp.focus({ workspace = "e-1" }), S.ws_prev)

-- Mouse: drag to move, right-drag to resize
group(S.group_windows)
bind(mod .. " + mouse:272", hl.dsp.window.drag(), S.move, { mouse = true })
bind(mod .. " + mouse:273", hl.dsp.window.resize(), S.resize, { mouse = true })

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
end, S.minimize)
bind(mod .. " + SHIFT + S", hl.dsp.workspace.toggle_special("minimized"), S.minimized)

group(S.group_apps)
-- Dropdown terminal: SUPER+Tab (physically Alt+Tab) toggles it, (re)starting it if needed
bind(mod .. " + Tab", function()
    for _, w in ipairs(hl.get_windows()) do
        if w.class == v.dropdown.class then
            hl.dispatch(hl.dsp.workspace.toggle_special("dropdown"))
            return
        end
    end
    -- Not running: just start it, the window rule opens the special workspace
    hl.dispatch(hl.dsp.exec_cmd(v.terminal .. " --class " .. v.dropdown.class))
end, S.dropdown)

group(S.group_screenshots)
-- Screenshots: Home = select area -> clipboard, SHIFT+Home = whole screen -> file
bind("Home", hl.dsp.exec_cmd([[grim -g "$(slurp -d)" - | wl-copy]]), S.shot_area)
bind(
    "SHIFT + Home",
    hl.dsp.exec_cmd("mkdir -p " .. v.screenshotDir .. " && grim " .. v.screenshotDir .. "/$(date +%F_%H-%M-%S).png"),
    S.shot_screen
)

-- Discord push-to-talk on ^ (the key left of 1, by keycode so the layout does
-- not matter). Discord registers the shortcut through the portal; Hyprland has
-- no approval dialog, the bind here is the approval. Hyprland sends press and
-- release. non_consuming: ^ still types (Neovim's "start of line")
group(S.group_apps)
bind("code:49", hl.dsp.global("discord:discord-push-to-talk"), S.ptt,
    { non_consuming = true })

-- Media and brightness keys (work on the lock screen too); osd changes the
-- value and shows the pill (~/.local/bin/osd-pill)
local held = { locked = true, repeating = true }
hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd(v.bin .. "osd volume up"), held)
hl.bind("XF86AudioLowerVolume", hl.dsp.exec_cmd(v.bin .. "osd volume down"), held)
hl.bind("XF86AudioMute", hl.dsp.exec_cmd(v.bin .. "osd volume mute"), { locked = true })
hl.bind("XF86AudioMicMute", hl.dsp.exec_cmd(v.bin .. "osd mic mute"), { locked = true })
hl.bind("XF86MonBrightnessUp", hl.dsp.exec_cmd(v.bin .. "osd brightness up"), held)
hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd(v.bin .. "osd brightness down"), held)
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
