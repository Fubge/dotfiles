local v = require("vars")
local s = require("settings")

hl.config({
    input = {
        follow_mouse = 0, -- focus changes on click, not on hover
        float_switch_override_focus = 0, -- ...also between floating and tiled windows
    },
    cursor = {
        no_warps = true, -- the mouse pointer stays put when a new window takes focus
    },
})

-- Keyboard, mouse and touchpad: the defaults here, changed in the system menu
-- (SUPER+ALT+Space -> keyboard / mouse & touchpad), which applies them live
local function apply_input()
    local k, m, t = s.get("keyboard"), s.get("mouse"), s.get("touchpad")
    local pick = s.pick
    hl.config({
        input = {
            kb_layout = pick(k.layout, v.keyboard.layout),
            kb_options = pick(k.options, v.keyboard.options), -- key swaps, see vars.lua
            repeat_rate = pick(k.repeat_rate, 25), -- keys per second while held
            repeat_delay = pick(k.repeat_delay, 600), -- ms until repeating starts
            -- mice (the touchpad gets its own values below)
            sensitivity = pick(m.sensitivity, 0),
            accel_profile = pick(m.accel, "flat"), -- flat = no pointer acceleration
            scroll_factor = pick(m.scroll, 1.0),
            natural_scroll = pick(m.natural, false),
            left_handed = pick(m.left_handed, false),
            touchpad = {
                natural_scroll = pick(t.natural, true),
                scroll_factor = pick(t.scroll, 0.5), -- 1.0 and 0.8 too fast, 0.3 too slow (per app: rules.lua)
                disable_while_typing = pick(t.dwt, true),
                tap_to_click = pick(t.tap, true),
                -- true: press with 2 fingers anywhere = right click, 3 = middle;
                -- false: click zones, bottom right corner = right click
                clickfinger_behavior = pick(t.clickfinger, true),
            },
        },
    })
    -- pointer speed and acceleration of the touchpad itself (the input values
    -- above would otherwise apply to it too)
    hl.device({
        name = v.touchpad,
        sensitivity = pick(t.sensitivity, 0),
        accel_profile = pick(t.accel, "flat"),
    })
end
apply_input()
s.on_apply("keyboard", apply_input)
s.on_apply("mouse", apply_input)
s.on_apply("touchpad", apply_input)

-- 3-finger swipe left/right switches workspaces
hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })
