local v = require("vars")

hl.config({
    general = {
        gaps_in = v.gaps.inner,
        gaps_out = v.gaps.outer,
        border_size = v.border,
        col = {
            active_border = v.colors.accent,
            inactive_border = v.colors.inactive,
        },
        resize_on_border = false,
        allow_tearing = true, -- only used by windows with the "immediate" rule (games)
        layout = "master",
    },

    decoration = {
        rounding = v.rounding,
        rounding_power = 2,
        shadow = {
            enabled = true,
            range = 4,
            render_power = 3,
            color = v.colors.shadow,
        },
        blur = {
            enabled = true,
            size = 5,
            passes = 1,
            ignore_opacity = true,
            vibrancy = 0.1696,
        },
    },

    master = {
        new_status = "slave",
        new_on_top = true,
    },

    animations = { enabled = true },

    render = {
        direct_scanout = 2, -- skip compositing for fullscreen games
    },

    misc = {
        force_default_wallpaper = -1, -- until hyprpaper arrives in phase 4
    },
})

-- Animations (Hyprland defaults)
hl.curve("easeOutQuint", { type = "bezier", points = { { 0.23, 1 }, { 0.32, 1 } } })
hl.curve("linear", { type = "bezier", points = { { 0, 0 }, { 1, 1 } } })
hl.curve("almostLinear", { type = "bezier", points = { { 0.5, 0.5 }, { 0.75, 1 } } })
hl.curve("quick", { type = "bezier", points = { { 0.15, 0 }, { 0.1, 1 } } })
hl.curve("easy", { type = "spring", mass = 1, stiffness = 238.1191, damping = 24.21279333 })

hl.animation({ leaf = "global", enabled = true, speed = 10, bezier = "default" })
hl.animation({ leaf = "border", enabled = true, speed = 5.39, bezier = "easeOutQuint" })
hl.animation({ leaf = "windows", enabled = true, speed = 4.79, spring = "easy" })
hl.animation({ leaf = "windowsIn", enabled = true, speed = 4.1, spring = "easy", style = "popin 87%" })
hl.animation({ leaf = "windowsOut", enabled = true, speed = 1.49, bezier = "linear", style = "popin 87%" })
hl.animation({ leaf = "fadeIn", enabled = true, speed = 1.73, bezier = "almostLinear" })
hl.animation({ leaf = "fadeOut", enabled = true, speed = 1.46, bezier = "almostLinear" })
hl.animation({ leaf = "fade", enabled = true, speed = 3.03, bezier = "quick" })
hl.animation({ leaf = "layers", enabled = true, speed = 3.81, bezier = "easeOutQuint" })
hl.animation({ leaf = "layersIn", enabled = true, speed = 4, bezier = "easeOutQuint", style = "fade" })
hl.animation({ leaf = "layersOut", enabled = true, speed = 1.5, bezier = "linear", style = "fade" })
hl.animation({ leaf = "workspaces", enabled = true, speed = 1.94, bezier = "almostLinear", style = "fade" })
hl.animation({ leaf = "specialWorkspace", enabled = true, speed = 3, bezier = "easeOutQuint", style = "slidevert" })
