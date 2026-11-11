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

-- Two scopes:
--   project  = git root of the current file (fallback: current directory)
--   home     = everything in ~ (heavy folders are skipped via ~/.config/ripgrep/ignore)
local function project_root()
    return vim.fs.root(0, ".git") or vim.uv.cwd()
end
local function in_dir(picker, dir, label, extra_opts)
    return function()
        local local_opts = vim.tbl_extend("force", { tool = "rg" }, extra_opts or {})
        picker(local_opts, { source = { cwd = dir(), name = label } })
    end
end
local home = function() return vim.env.HOME end

map("n", "<leader>sf", in_dir(builtin.files, project_root, "Files (project)"),     { desc = "Files in project" })
map("n", "<leader>sg", in_dir(builtin.grep_live, project_root, "Grep (project)"),  { desc = "Grep in project" })
map("n", "<leader>sw", function()
    builtin.grep({ tool = "rg", pattern = vim.fn.expand("<cword>") },
        { source = { cwd = project_root(), name = "Word (project)" } })
end, { desc = "Word under cursor in project" })
map("n", "<leader>sF", in_dir(builtin.files, home, "Files (home)"),                { desc = "Files everywhere (~)" })
map("n", "<leader>sG", in_dir(builtin.grep_live, home, "Grep (home)"),             { desc = "Grep everywhere (~)" })
map("n", "<leader>sh", builtin.help,       { desc = "Search help" })
map("n", "<leader>sk", extra.keymaps,      { desc = "Search keymaps" })
map("n", "<leader>sd", extra.diagnostic,   { desc = "Search diagnostics" })
map("n", "<leader>s/", extra.buf_lines,    { desc = "Search lines in open buffers" })
map("n", "<leader>sr", builtin.resume,     { desc = "Resume last search" })
map("n", "<leader>sc", function() builtin.files(nil, { source = { cwd = vim.fn.stdpath("config") } }) end,
    { desc = "Search Neovim config" })
map("n", "<leader><leader>", extra.oldfiles, { desc = "Recent files" })
map("n", "<leader>b",  builtin.buffers,    { desc = "Open buffers" })

-- File explorer: <leader>e toggles it (opens at the current file).
-- Inside: h/l = up/into, edit lines to rename/delete/create, = saves changes, q or <Esc> closes.
map("n", "<leader>e", function()
    if not MiniFiles.close() then
        local file = vim.api.nvim_buf_get_name(0)
        MiniFiles.open(file ~= "" and file or nil)
    end
end, { desc = "File explorer (toggle)" })

vim.api.nvim_create_autocmd("User", {
    pattern = "MiniFilesBufferCreate",
    callback = function(args)
        vim.keymap.set("n", "<Esc>", MiniFiles.close, { buffer = args.data.buf_id, desc = "Close explorer" })
    end,
})
