local v = require("vars")

-- Dropdown terminal lives on its own special workspace
hl.window_rule({
    name = "dropdown-terminal",
    match = { class = "^" .. v.dropdown.class .. "$" },
    float = true,
    size = v.dropdown.size,
    move = v.dropdown.move,
    workspace = "special:dropdown silent",
    stay_focused = true,
})

-- Bar popups (volume mixer, Wi-Fi/Bluetooth terminals)
for _, class in ipairs(v.popup.classes) do
    hl.window_rule({
        name = "popup-" .. class,
        match = { class = "^" .. (class:gsub("%.", "\\.")) .. "$" },
        float = true,
        pin = true,
        size = v.popup.size,
        move = v.popup.move,
    })
end

local function is_popup(win)
    for _, class in ipairs(v.popup.classes) do
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
