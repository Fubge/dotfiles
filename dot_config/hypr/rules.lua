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

-- Discord has its own workspace 5 (chat) and opens there, tiled full size.
-- Title must end in "Discord": the updater splash at login ("Discord Updater")
-- should not pull you over to workspace 5.
hl.window_rule({
    name = "discord",
    match = { class = "^discord$", title = ".*Discord$" },
    workspace = "5",
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

-- Games: Steam games (steam_app_*) and gamescope open on workspace 4,
-- may tear (lower latency) and skip animations.
hl.window_rule({
    name = "games",
    match = { class = "^(steam_app_.*|gamescope)$" },
    workspace = "4",
    immediate = true,
    no_anim = true,
})

-- Steam client: small dialogs float
hl.window_rule({
    name = "steam-dialogs",
    match = { class = "^steam$", title = "^(Friends List|Steam Settings|Steam - News.*)$" },
    float = true,
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
