local v = require("vars")

hl.config({
    input = {
        kb_layout = v.keyboard.layout,
        kb_options = v.keyboard.options, -- key swaps, see vars.lua
        follow_mouse = 0, -- focus changes on click, not on hover
        float_switch_override_focus = 0, -- ...also between floating and tiled windows
        sensitivity = 0,
        accel_profile = "flat", -- no pointer acceleration (mouse and touchpad)
        touchpad = {
            natural_scroll = true,
            scroll_factor = 0.5, -- 1.0 and 0.8 too fast, 0.3 too slow (per app: rules.lua)
            disable_while_typing = true,
            clickfinger_behavior = true, -- press with 2 fingers anywhere = right click, 3 = middle (2-finger tap = right too)
        },
    },
    cursor = {
        no_warps = true, -- the mouse pointer stays put when a new window takes focus
    },
})

-- 3-finger swipe left/right switches workspaces
hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })

-- External mice: add a block per device (name from `hyprctl devices`)
-- hl.device({ name = "logitech-g502", sensitivity = -0.7 })
