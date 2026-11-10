local v = require("vars")

-- Opens `cmd` and moves its FIRST window matching `class` to `workspace`
-- without switching there. Later windows of the same app open normally.
local function open_on(workspace, cmd, class)
    local sub
    sub = hl.on("window.open", function(win)
        if win and win.class and win.class:lower():find(class, 1, true) then
            hl.dispatch(hl.dsp.window.move({ window = win, workspace = workspace, follow = false }))
            sub:remove()
        end
    end)
    hl.exec_cmd(v.launch .. cmd)
end

hl.on("hyprland.start", function()
    for _, app in ipairs(v.startup) do
        open_on(app.workspace, app.cmd, app.class)
    end
    for _, cmd in ipairs(v.background) do
        hl.exec_cmd(v.launch .. cmd)
    end
end)
