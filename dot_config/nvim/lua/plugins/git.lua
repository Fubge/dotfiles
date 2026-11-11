-- Git integration (mini.diff + mini.git, part of mini.nvim).
--   Signs in the left column show added / changed / deleted lines.
--   ]h / [h      next / previous change ("hunk")       ]H / [H  last / first
--   gh{motion}   stage (apply) a change, e.g. ghgh for the hunk under the cursor
--   gH{motion}   reset (undo) a change
--   <leader>go   overlay: show the old version inline
--   :Git <cmd>   run any git command, e.g. :Git log --oneline

require("mini.diff").setup({
    view = {
        style = "sign",
        signs = { add = "▎", change = "▎", delete = "" },
    },
})
require("mini.git").setup()

vim.keymap.set("n", "<leader>go", function() MiniDiff.toggle_overlay(0) end, { desc = "Toggle diff overlay" })
vim.keymap.set("n", "<leader>gb", "<cmd>vertical Git blame -- %<CR>", { desc = "Blame (who changed each line)" })
vim.keymap.set("n", "<leader>gl", "<cmd>Git log --oneline -20<CR>", { desc = "Recent commits" })
vim.keymap.set("n", "<leader>gs", function() MiniExtra.pickers.git_hunks() end, { desc = "Search changes (hunks)" })
