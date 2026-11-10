-- Central place for all values that would otherwise be hardcoded.
local M = {}

-- Applications ---------------------------------------------------------------
-- Every app is launched through uwsm so it runs in its own systemd scope.
M.launch      = "uwsm app -- "
M.terminal    = "kitty"
M.browser     = "vivaldi"
M.fileManager = "dolphin"
-- App launcher; text without a matching app is searched on the web
M.menu        = "rofi -show combi -modes combi,web:" .. os.getenv("HOME") .. "/.local/bin/rofi-web-mode -combi-modes web,drun -display-combi Apps"
M.bin         = os.getenv("HOME") .. "/.local/bin/"

-- Startup layout: workspace 1 stays empty --------------------------------------
M.startup = {
    { workspace = 2, cmd = M.browser,  class = "vivaldi" },
    { workspace = 3, cmd = M.terminal, class = "kitty" },
}
M.background = {
    "discord --start-minimized",
    "wl-paste --watch cliphist store",   -- clipboard history
}

-- Look -----------------------------------------------------------------------
M.colors = {
    accent   = "rgba(ff7f00ff)",
    inactive = "rgba(646464ff)",
    shadow   = 0xee1a1a1a,
}
M.gaps     = { inner = 6, outer = 6 }
M.border   = 1
M.rounding = 10
M.terminalOpacity = "0.9"

-- Dropdown terminal (Alt+Tab), sizes relative to the monitor -------------------
M.dropdown = {
    class = "dropdown_terminal",
    size  = { "monitor_w*0.6", "monitor_h*0.4" },
    move  = { "monitor_w*0.2", "monitor_h*0.05" },
}

-- Input ----------------------------------------------------------------------
M.keyboard = { layout = "de", options = "caps:swapescape" }
M.touchpad = "gxtp5400:00-27c6:0f96-touchpad"

-- Screenshots ----------------------------------------------------------------
M.screenshotDir = os.getenv("HOME") .. "/Pictures/Screenshots"

return M
