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

-- Overlays: same size and spot as the rofi overlays (centered on the screen)
for _, class in ipairs(v.overlays) do
    hl.window_rule({
        name = "overlay-" .. class,
        match = { class = escape(class) },
        float = true,
        pin = true,
        size = v.overlay.size,
        move = { "monitor_w*0.5-" .. v.overlay.size[1] // 2, "monitor_h*0.5-" .. v.overlay.size[2] // 2 },
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

hl.window_rule({
    name = "discord-float",
    match = { class = "^discord$" },
    float = true,
    size = { "monitor_w*0.6", "monitor_h*0.65" },
    center = true,
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

-- Games: Steam games (steam_app_*) and gamescope open on workspace 5,
-- may tear (lower latency) and skip animations.
hl.window_rule({
    name = "games",
    match = { class = "^(steam_app_.*|gamescope)$" },
    workspace = "5",
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
