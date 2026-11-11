-- LSP: Neovim talks to a "language server" per language, which understands the code.
-- Server configs live in ~/.config/nvim/lsp/<name>.lua; servers are installed with pacman.
-- :checkhealth vim.lsp   shows which servers are attached to the current file.

vim.lsp.enable({ "lua_ls", "bashls", "taplo", "yamlls" })

-- Built-in keys (no setup needed, available whenever a server is attached):
--   K      hover docs            grn  rename            gra  code action
--   grr    references            gri  implementation    grt  type definition
--   gO     symbols in file       [d / ]d  prev/next diagnostic
--   <C-s>  signature help (insert mode)
-- Extra keys below are only added to buffers with a server.
vim.api.nvim_create_autocmd("LspAttach", {
    callback = function(args)
        local map = function(keys, fn, desc)
            vim.keymap.set("n", keys, fn, { buffer = args.buf, desc = desc })
        end
        map("gd", vim.lsp.buf.definition, "Go to definition")
        map("<leader>cd", vim.diagnostic.open_float, "Show diagnostic under cursor")
        map("<leader>ss", function()
            MiniExtra.pickers.lsp({ scope = "document_symbol" })
        end, "Search symbols in file")
        map("<leader>sS", function()
            MiniExtra.pickers.lsp({ scope = "workspace_symbol" })
        end, "Search symbols in project")

        -- Show inlay hints (parameter names, types) where the server supports them
        local client = vim.lsp.get_client_by_id(args.data.client_id)
        if client and client:supports_method("textDocument/inlayHint") then
            vim.lsp.inlay_hint.enable(true, { bufnr = args.buf })
        end
    end,
})

-- How errors and warnings are shown
vim.diagnostic.config({
    severity_sort = true,
    virtual_text = { spacing = 2, prefix = "●" }, -- message at the end of the line
    float = { border = "rounded", source = true },
    signs = {
        text = {
            [vim.diagnostic.severity.ERROR] = "\u{f0159}",
            [vim.diagnostic.severity.WARN] = "\u{f0026}",
            [vim.diagnostic.severity.INFO] = "\u{f02fc}",
            [vim.diagnostic.severity.HINT] = "\u{f0335}",
        },
    },
})
