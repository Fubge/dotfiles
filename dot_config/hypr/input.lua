local v = require("vars")

hl.config({
    input = {
        kb_layout = v.keyboard.layout,
        kb_options = v.keyboard.options, -- Caps Lock <-> Escape (great for Neovim)
        follow_mouse = 0, -- focus changes on click, not on hover
        float_switch_override_focus = 0, -- ...also between floating and tiled windows
        sensitivity = 0,
        touchpad = {
            natural_scroll = true,
            scroll_factor = 0.8, -- 1.0 felt a bit too fast
            disable_while_typing = true,
            clickfinger_behavior = true, -- 2-finger click = right, 3-finger = middle
        },
    },
})

-- 3-finger swipe left/right switches workspaces
hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })

-- External mice: add a block per device (name from `hyprctl devices`)
-- hl.device({ name = "logitech-g502", sensitivity = -0.7 })
