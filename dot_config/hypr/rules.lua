local v = require("vars")

-- Dropdown terminal lives on its own special workspace. Not "silent": on the
-- first launch the workspace only opens once the window exists (no empty flash)
hl.window_rule({
    name = "dropdown-terminal",
    match = { class = "^" .. v.dropdown.class .. "$" },
    float = true,
    size = v.dropdown.size,
    move = v.dropdown.move,
    workspace = "special:dropdown",
    stay_focused = true,
})

-- Bar popups (volume mixer, brightness slider, terminals): centered under the click
local function escape(class)
    return "^" .. (class:gsub("%.", "\\.")) .. "$"
end
for class, size in pairs(v.popup.classes) do
    hl.window_rule({
        name = "popup-" .. class,
        match = { class = escape(class) },
        float = true,
        pin = true,
        size = size,
        move = { "cursor_x-" .. size[1] // 2, tostring(v.popup.top) },
    })
end

for _, class in ipairs(v.popup.placed) do
    hl.window_rule({
        name = "popup-" .. class,
        match = { class = escape(class) },
        float = true,
        pin = true,
        move = { "cursor_x-window_w*0.5", tostring(v.popup.top) },   -- until it places itself
    })
end

-- Overlays: same size and spot as the rofi overlays (horizontally centered)
for _, class in ipairs(v.overlays) do
    hl.window_rule({
        name = "overlay-" .. class,
        match = { class = escape(class) },
        float = true,
        pin = true,
        size = v.overlay.size,
        move = { "monitor_w*0.5-" .. v.overlay.size[1] // 2, tostring(v.overlay.top) },
        rounding = v.overlay.rounding,
    })
end

local function is_popup(win)
    if v.popup.classes[win.class] then
        return true
    end
    for _, class in ipairs(v.popup.placed) do
        if win.class == class then
            return true
        end
    end
    for _, class in ipairs(v.overlays) do
        if win.class == class then
            return true
        end
    end
    return false
end

-- Close popups as soon as another window gets focus
hl.on("window.active", function(active)
    for _, win in ipairs(hl.get_windows()) do
        if is_popup(win) and (not active or win.address ~= active.address) then
            hl.dispatch(hl.dsp.window.close({ window = win }))
        end
    end
end)

-- ...and on a click next to them. A click on the empty desktop moves no focus
-- (no window.active above), so watch the mouse buttons themselves; the bind
-- does not swallow the click. The bar is left out: its icons toggle popups
-- themselves, closing here first would make the same icon open it again.
local function close_popups_outside()
    local p = hl.get_cursor_pos()
    local mon = hl.get_active_monitor()
    if not p or (mon and p.y - (mon.y or 0) < v.popup.top) then
        return
    end
    for _, win in ipairs(hl.get_windows()) do
        if is_popup(win) and not win.hidden then
            local inside = p.x >= win.at.x and p.x < win.at.x + win.size.x
                and p.y >= win.at.y and p.y < win.at.y + win.size.y
            if not inside then
                hl.dispatch(hl.dsp.window.close({ window = win }))
            end
        end
    end
end
for _, button in ipairs({ "mouse:272", "mouse:273", "mouse:274" }) do
    hl.bind(button, close_popups_outside, { non_consuming = true })
end

-- Spotify floats big and centered on its own special workspace "music": it
-- appears over the current workspace and never pushes tiled windows around.
-- Toggle: SUPER+O or a click on the music icon in the bar (~/.local/bin/music show)
hl.window_rule({
    name = "spotify",
    match = { class = "^[Ss]potify$" },
    float = true,
    size = v.music.size,
    center = true,
    workspace = "special:music",
})

-- Claude Code scratchpad: one long-running session on special:claude, same frame
-- as the overlays. "silent": started hidden at login; SUPER+C / the bar robot
-- shows it (~/.local/bin/claude-pad)
hl.window_rule({
    name = "claude-pad",
    match = { class = "^" .. v.claude.class .. "$" },
    float = true,
    size = v.overlay.size,
    move = { "monitor_w*0.5-" .. v.overlay.size[1] // 2, tostring(v.overlay.top) },
    rounding = v.overlay.rounding,
    workspace = "special:claude silent",
})

-- Small tool windows float centered instead of splitting the layout
for class, size in pairs(v.floating) do
    hl.window_rule({
        name = "float-" .. class,
        match = { class = "^" .. class .. "$" },
        float = true,
        size = size,
        center = true,
    })
end

-- Discord has its own workspace 5 (chat) and opens there, tiled full size,
-- without switching (it starts at login). SUPER+D jumps there (focus-or-run).
-- Title must end in "Discord": the updater splash stays where it pops up.
hl.window_rule({
    name = "discord",
    match = { class = "^discord$", title = ".*Discord$" },
    workspace = "5 silent",
})

-- YouTube runs as a Vivaldi app window (own class) on workspace 4, whether
-- youtube-autostart opens it or Vivaldi restores it with the last session
hl.window_rule({
    name = "youtube",
    match = { class = "^vivaldi-www\\.youtube\\.com__.*$" },
    workspace = "4 silent",
})

-- Ignore maximize requests from apps
hl.window_rule({
    name = "suppress-maximize-events",
    match = { class = ".*" },
    suppress_event = "maximize",
})

-- Fix dragging issues with XWayland
hl.window_rule({
    name = "fix-xwayland-drags",
    match = { class = "^$", title = "^$", xwayland = true, float = true, fullscreen = false, pin = false },
    no_focus = true,
})

-- Games: Steam games (steam_app_*) and gamescope open fullscreen on
-- workspace 6 (never tiled next to the launcher, no bar), may tear (lower
-- latency) and skip animations.
hl.window_rule({
    name = "games",
    match = { class = "^(steam_app_.*|gamescope)$" },
    workspace = "6",
    fullscreen = true,
    immediate = true,
    no_anim = true,
})

-- Minecraft (native Wayland via SDL) goes there too, fullscreen, but without tearing:
-- in fullscreen with "immediate" it stops taking keyboard and mouse input
hl.window_rule({
    name = "minecraft",
    match = { class = "^com\\.mojang\\.minecraft$" },
    workspace = "6",
    fullscreen = true,
    no_anim = true,
})

-- Launchers (Steam client, Modrinth App) live on the games workspace 6 too
-- (all their windows, dialogs included) and switch there when started
hl.window_rule({
    name = "steam",
    match = { class = "^(steam|modrinth-app)$" },
    workspace = "6",
})

-- Steam (CEF) scrolls far more per touchpad swipe than other apps: slow it down
hl.window_rule({
    name = "steam-scroll",
    match = { class = "^steam$" },
    scroll_touchpad = 0.15,
})

-- Vivaldi (Chromium, also its app windows like YouTube) scrolls much further
-- per swipe than the terminal, although it runs natively on Wayland
hl.window_rule({
    name = "vivaldi-scroll",
    match = { class = "^vivaldi-.*$" },
    scroll_touchpad = 0.15,
})

-- Discord (Electron, Chromium inside) overshoots the same way
hl.window_rule({
    name = "discord-scroll",
    match = { class = "^discord$" },
    scroll_touchpad = 0.15,
})

-- Terminals (kitty windows) scroll a bit faster than the global 0.5
hl.window_rule({
    name = "terminal-scroll",
    match = { class = "^(kitty|" .. v.dropdown.class .. "|" .. v.claude.class .. ")$" },
    scroll_touchpad = 0.6,
})

-- Steam client: small dialogs float
hl.window_rule({
    name = "steam-dialogs",
    match = { class = "^steam$", title = "^(Friends List|Steam Settings|Steam - News.*)$" },
    float = true,
})

-- File pickers (open/save/choose folder) from the GTK portal: float and center.
-- Tiled, they ended up under floating dialogs that opened them (Steam Settings)
hl.window_rule({
    name = "file-picker",
    match = { class = "^xdg-desktop-portal-gtk$" },
    float = true,
    size = { 900, 600 },
    center = true,
})

-- rofi menus: blur the translucent panel and dim the desktop behind it
hl.layer_rule({
    name = "rofi",
    match = { namespace = "^rofi$" },
    blur = true,
    ignore_alpha = 0.1,
    dim_around = true,
})

-- Notifications (dunst) slide in from the right edge and out again
hl.layer_rule({
    name = "notifications",
    match = { namespace = "^notifications$" },
    animation = "slide right",
})
