-- Prints Neovim's key mappings that have a description as JSON, for the
-- shortcut overview (~/.local/bin/keybinds, page "Neovim"):
--     nvim --headless -c "luafile ~/.local/lib/popup/nvim-keys.lua" -c q
-- Read from the running config, so the overview follows every change there.
local out = {}
for _, mode in ipairs({ "n", "x", "i", "t" }) do
    for _, m in ipairs(vim.api.nvim_get_keymap(mode)) do
        if m.desc and m.desc ~= "" then
            table.insert(out, { mode = mode, lhs = m.lhs, desc = m.desc })
        end
    end
end
-- keys that only exist in buffers with a language server (config/lsp.lua)
local ok, lsp = pcall(require, "config.lsp")
if ok and type(lsp) == "table" then
    for _, k in ipairs(lsp.keys or {}) do
        local lhs = k[1]:gsub("<leader>", vim.g.mapleader or "\\")
        table.insert(out, { mode = "n", lhs = lhs, desc = k[3], lsp = true })
    end
end
io.stdout:write(vim.json.encode(out))
