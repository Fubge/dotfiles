local v = require("vars")

-- Opens `cmd` and moves its FIRST window matching `class` to `workspace`
-- without switching there, then calls `done` (starts the next app of that
-- class). Later windows of the same app open normally.
local function open_on(workspace, cmd, class, done)
    local sub
    sub = hl.on("window.open", function(win)
        if win and win.class and win.class:lower():find(class, 1, true) then
            hl.dispatch(hl.dsp.window.move({ window = win, workspace = workspace, follow = false }))
            sub:remove()
            if done then done() end
        end
    end)
    hl.exec_cmd(v.launch .. cmd)
end

-- Startup apps sharing a class (two browser windows) would both grab the
-- first window, so each class gets a queue that starts its apps in order
local function start_queues(apps)
    local queues, order = {}, {}
    for _, app in ipairs(apps) do
        if not queues[app.class] then
            queues[app.class] = {}
            table.insert(order, app.class)
        end
        table.insert(queues[app.class], app)
    end
    for _, class in ipairs(order) do
        local q, i = queues[class], 0
        local function next_app()
            i = i + 1
            local app = q[i]
            if app then open_on(app.workspace, app.cmd, app.class, next_app) end
        end
        next_app()
    end
end

-- Opens `cmd` and runs `hide` once its first window matching `class` appears
local function open_hidden(cmd, class, hide)
    local sub
    sub = hl.on("window.open", function(win)
        if win and win.class and win.class:lower():find(class, 1, true) then
            hl.exec_cmd(hide)
            sub:remove()
        end
    end)
    hl.exec_cmd(v.launch .. cmd)
end

hl.on("hyprland.start", function()
    start_queues(v.startup)
    for _, app in ipairs(v.hidden) do
        open_hidden(app.cmd, app.class, app.hide)
    end
    for _, cmd in ipairs(v.background) do
        hl.exec_cmd(v.launch .. cmd)
    end
end)
