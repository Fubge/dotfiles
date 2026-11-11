-- Key mappings. vim.keymap.set(mode, keys, action, options)
--   mode: "n" normal, "i" insert, "v" visual, "t" terminal
local map = vim.keymap.set

-- <Esc> also clears the search highlight
map("n", "<Esc>", "<cmd>nohlsearch<CR>")

-- Leave the built-in terminal with a double <Esc>
map("t", "<Esc><Esc>", "<C-\\><C-n>", { desc = "Exit terminal mode" })

-- Move between split windows with Ctrl + h/j/k/l
map("n", "<C-h>", "<C-w><C-h>", { desc = "Focus left window" })
map("n", "<C-l>", "<C-w><C-l>", { desc = "Focus right window" })
map("n", "<C-j>", "<C-w><C-j>", { desc = "Focus lower window" })
map("n", "<C-k>", "<C-w><C-k>", { desc = "Focus upper window" })

-- Training wheels: arrow keys in normal mode remind you of h/j/k/l.
-- Delete this block once hjkl feels natural.
for key, hint in pairs({ Left = "h", Down = "j", Up = "k", Right = "l" }) do
    map("n", "<" .. key .. ">", function()
        vim.notify("Use " .. hint, vim.log.levels.WARN)
    end)
end

-- Diagnostics (errors/warnings from language servers, used later)
map("n", "<leader>q", vim.diagnostic.setloclist, { desc = "Diagnostics to quickfix list" })
