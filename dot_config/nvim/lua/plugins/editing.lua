-- Editing helpers: completion, auto-pairs, formatting.

-- Completion popup while typing (mini.completion, part of mini.nvim) ----------
--   <Tab>/<S-Tab> move through suggestions, <CR> accepts, <C-e> closes the popup.
--   Also shows docs for the selected item and function signatures while typing.
require("mini.completion").setup({
    window = {
        info = { border = "rounded" },
        signature = { border = "rounded" },
    },
})

-- Brackets and quotes close themselves: type ( -> ()
require("mini.pairs").setup()

local key = vim.keycode
vim.keymap.set("i", "<Tab>", function()
    return vim.fn.pumvisible() == 1 and key("<C-n>") or key("<Tab>")
end, { expr = true, replace_keycodes = false, desc = "Next suggestion" })
vim.keymap.set("i", "<S-Tab>", function()
    return vim.fn.pumvisible() == 1 and key("<C-p>") or key("<S-Tab>")
end, { expr = true, replace_keycodes = false, desc = "Previous suggestion" })
-- <CR>: accept the selected suggestion, otherwise a normal newline (pair-aware)
vim.keymap.set("i", "<CR>", function()
    if vim.fn.pumvisible() == 1 then
        local selected = vim.fn.complete_info({ "selected" }).selected ~= -1
        return selected and key("<C-y>") or key("<C-y><CR>")
    end
    return MiniPairs.cr()
end, { expr = true, replace_keycodes = false, desc = "Accept suggestion / newline" })

-- Formatting (conform.nvim): runs the right formatter per language on save ----
vim.pack.add({ "https://github.com/stevearc/conform.nvim" })

require("conform").setup({
    formatters_by_ft = {
        lua = { "stylua" },   -- style: ~/.config/stylua/stylua.toml
        sh = { "shfmt" },
        bash = { "shfmt" },
        toml = { "taplo" },
    },
    -- Languages without a formatter above use the language server, if it can format
    default_format_opts = { lsp_format = "fallback" },
    formatters = {
        shfmt = { prepend_args = { "-i", "4", "-ci" } },  -- 4 spaces, indent case branches
    },
    format_on_save = function(buf)
        if vim.g.autoformat == false or vim.b[buf].autoformat == false then return end
        return { timeout_ms = 1000 }
    end,
})

vim.keymap.set({ "n", "v" }, "<leader>cf", function() require("conform").format() end,
    { desc = "Format file / selection" })
vim.api.nvim_create_user_command("FormatToggle", function()
    vim.g.autoformat = vim.g.autoformat == false
    vim.notify("Format on save: " .. (vim.g.autoformat == false and "off" or "on"))
end, { desc = "Toggle format on save" })
