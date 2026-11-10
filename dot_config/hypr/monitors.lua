-- Monitor setup.
-- 1. Fallback: any screen gets its preferred mode and an automatic scale,
--    so the laptop works on its own and with unknown displays.
-- 2. Known monitors are matched by description ("desc:..."), not by port,
--    so it does not matter which port or dock they are plugged into.
--    Find the description with: hyprctl monitors

hl.monitor({ output = "", mode = "preferred", position = "auto", scale = "auto" })

-- Internal OLED panel (2880x1800, 120 Hz)
local internal = "eDP-1"
hl.monitor({ output = internal, mode = "2880x1800@120", position = "auto", scale = 2 })

-- Known external monitors (add when they arrive):
-- hl.monitor({ output = "desc:Dell Inc. DELL U2723QE XXXXXXX", mode = "preferred", position = "auto-left", scale = 1.5 })

-- Lid switch: with an external monitor connected, closing the lid only turns
-- off the internal panel. Without one, logind suspends as usual.
hl.bind("switch:on:Lid Switch", function()
    if #hl.get_monitors() > 1 then
        hl.monitor({ output = internal, disabled = true })
    end
end, { locked = true })

hl.bind("switch:off:Lid Switch", function()
    hl.monitor({ output = internal, mode = "2880x1800@120", position = "auto", scale = 2 })
end, { locked = true })
