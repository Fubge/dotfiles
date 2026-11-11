-- Lua language server. Knows Neovim's own Lua API, so `vim.` gets completion and docs.
return {
    cmd = { "lua-language-server" },
    filetypes = { "lua" },
    root_markers = { ".luarc.json", ".git" },
    settings = {
        Lua = {
            runtime = { version = "LuaJIT" },
            workspace = {
                checkThirdParty = false,
                library = { vim.env.VIMRUNTIME }, -- Neovim's runtime (vim.* API)
            },
            diagnostics = { globals = { "vim", "hl" } }, -- hl = Hyprland's Lua API
            telemetry = { enable = false },
        },
    },
}
