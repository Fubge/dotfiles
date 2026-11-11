-- Look & feel: colorscheme, statusline, icons, keymap hints.
local gh = function(repo) return "https://github.com/" .. repo end

vim.pack.add({
    gh("folke/tokyonight.nvim"),     -- colorscheme
    gh("echasnovski/mini.nvim"),     -- collection of small modules (statusline, icons, ...)
    gh("folke/which-key.nvim"),      -- popup that shows available keys
})

-- Colorscheme ----------------------------------------------------------------
require("tokyonight").setup({
    style = "night",
    -- Small touch of the desktop accent color (orange)
    on_highlights = function(hl)
        hl.CursorLineNr = { fg = "#ff7f00", bold = true }
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
