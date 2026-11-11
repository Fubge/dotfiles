-- Look & feel: colorscheme, statusline, icons, keymap hints.
local gh = function(repo) return "https://github.com/" .. repo end

vim.pack.add({
    gh("folke/tokyonight.nvim"),     -- colorscheme
    gh("echasnovski/mini.nvim"),     -- collection of small modules (statusline, icons, ...)
    gh("folke/which-key.nvim"),      -- popup that shows available keys
})

-- Colorscheme ----------------------------------------------------------------
-- tokyonight provides good syntax rules; the colors come from the desktop palette.
local p = require("config.palette")
require("tokyonight").setup({
    style = "night",
    on_colors = function(c)
        -- Surfaces
        c.bg, c.bg_dark, c.bg_highlight = p.bg, p.bg_dark, p.bg_alt
        c.bg_float, c.bg_popup, c.bg_sidebar = p.bg_dark, p.bg_dark, p.bg_dark
        c.bg_statusline, c.bg_visual = p.bg_dark, p.steel
        c.border, c.border_highlight = p.steel, p.accent
        -- Text
        c.fg, c.fg_dark, c.fg_gutter = p.fg, p.fg_muted, p.steel
        c.comment, c.dark3, c.dark5 = p.comment, p.steel, p.slate
        -- Syntax / semantic colors
        c.orange, c.yellow, c.red, c.green = p.accent, p.yellow, p.red, p.green
        c.blue, c.cyan, c.magenta, c.purple = p.blue, p.cyan, p.magenta, p.magenta
        c.error, c.warning = p.red, p.yellow
    end,
    on_highlights = function(hl, c)
        hl.CursorLineNr = { fg = p.accent, bold = true }
        hl.FloatBorder  = { fg = p.accent, bg = p.bg_dark }
        hl.WinSeparator = { fg = p.steel }
        hl.Search       = { fg = p.bg, bg = p.yellow }
        hl.IncSearch    = { fg = p.bg, bg = p.accent }
        hl.Cursor       = { fg = p.bg, bg = p.accent }
        -- Statusline mode pill: same colors as the active workspace in waybar
        hl.MiniStatuslineModeNormal  = { fg = p.bg, bg = p.accent, bold = true }
        hl.MiniStatuslineModeInsert  = { fg = p.bg, bg = p.green, bold = true }
        hl.MiniStatuslineModeVisual  = { fg = p.bg, bg = p.magenta, bold = true }
        hl.MiniStatuslineModeReplace = { fg = p.bg, bg = p.red, bold = true }
        hl.MiniStatuslineModeCommand = { fg = p.bg, bg = p.yellow, bold = true }
        hl.MiniStatuslineDevinfo     = { fg = p.fg, bg = p.steel }
        hl.MiniStatuslineFileinfo    = { fg = p.fg, bg = p.steel }
        hl.MiniStatuslineFilename    = { fg = p.fg_muted, bg = p.bg_dark }
    end,
})
vim.cmd.colorscheme("tokyonight-night")

-- Icons (Nerd Font). Also pretends to be nvim-web-devicons for other plugins.
require("mini.icons").setup()
MiniIcons.mock_nvim_web_devicons()

-- Statusline: mode, git branch, diagnostics, file name, position
require("mini.statusline").setup()

-- which-key: press <leader> (Space) and wait to see what follows
require("which-key").setup({
    preset = "helix",
    spec = {
        { "<leader>s", group = "Search" },
        { "<leader>g", group = "Git" },
        { "<leader>c", group = "Code" },
    },
})
