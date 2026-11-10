local v = require("vars")

-- Dropdown terminal lives on its own special workspace
hl.window_rule({
    name  = "dropdown-terminal",
    match = { class = "^" .. v.dropdown.class .. "$" },
    float = true,
    size  = v.dropdown.size,
    move  = v.dropdown.move,
    workspace    = "special:dropdown silent",
    stay_focused = true,
})

hl.window_rule({
    name    = "terminal-opacity",
    match   = { class = "^kitty$" },
    opacity = v.terminalOpacity,
})

hl.window_rule({
    name   = "discord-float",
    match  = { class = "^discord$" },
    float  = true,
    size   = { "monitor_w*0.6", "monitor_h*0.65" },
    center = true,
})

-- Ignore maximize requests from apps
hl.window_rule({
    name  = "suppress-maximize-events",
    match = { class = ".*" },
    suppress_event = "maximize",
})

-- Fix dragging issues with XWayland
hl.window_rule({
    name  = "fix-xwayland-drags",
    match = { class = "^$", title = "^$", xwayland = true, float = true, fullscreen = false, pin = false },
    no_focus = true,
})
