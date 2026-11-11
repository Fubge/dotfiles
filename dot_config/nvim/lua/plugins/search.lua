-- Search & navigation with mini.pick (fuzzy finder) and mini.files (file explorer).
-- Both come with mini.nvim, which ui.lua already installs.
-- Inside the picker: type to filter, <C-n>/<C-p> or arrows to move, <CR> open,
-- <C-s> open in split, <C-v> vertical split, <Esc> close.

local pick = require("mini.pick")
pick.setup({
    window = {
        -- Centered floating window, 60% of the screen
        config = function()
            local h = math.floor(0.6 * vim.o.lines)
            local w = math.floor(0.6 * vim.o.columns)
            return {
                anchor = "NW", height = h, width = w, border = "rounded",
                row = math.floor((vim.o.lines - h) / 2),
                col = math.floor((vim.o.columns - w) / 2),
            }
        end,
    },
})
require("mini.extra").setup()   -- extra pickers: keymaps, diagnostics, recent files, ...
vim.ui.select = MiniPick.ui_select  -- use the picker for every "choose one" prompt

require("mini.files").setup({ windows = { preview = true, width_preview = 50 } })

local map = vim.keymap.set
local builtin, extra = MiniPick.builtin, MiniExtra.pickers

map("n", "<leader>sf", builtin.files,      { desc = "Search files" })
map("n", "<leader>sg", builtin.grep_live,  { desc = "Search by grep (live)" })
map("n", "<leader>sw", function() builtin.grep({ pattern = vim.fn.expand("<cword>") }) end,
    { desc = "Search word under cursor" })
map("n", "<leader>sh", builtin.help,       { desc = "Search help" })
map("n", "<leader>sk", extra.keymaps,      { desc = "Search keymaps" })
map("n", "<leader>sd", extra.diagnostic,   { desc = "Search diagnostics" })
map("n", "<leader>s/", extra.buf_lines,    { desc = "Search lines in open buffers" })
map("n", "<leader>sr", builtin.resume,     { desc = "Resume last search" })
map("n", "<leader>sc", function() builtin.files(nil, { source = { cwd = vim.fn.stdpath("config") } }) end,
    { desc = "Search Neovim config" })
map("n", "<leader><leader>", extra.oldfiles, { desc = "Recent files" })
map("n", "<leader>b",  builtin.buffers,    { desc = "Open buffers" })

-- File explorer: opens at the current file. Inside: h/l = up/into, = to save changes
map("n", "<leader>e", function() MiniFiles.open(vim.api.nvim_buf_get_name(0)) end,
    { desc = "File explorer" })
