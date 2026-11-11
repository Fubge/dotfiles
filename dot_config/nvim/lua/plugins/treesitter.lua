-- Treesitter: parses code into a syntax tree -> accurate highlighting and indentation.
-- Parsers are compiled locally (needs tree-sitter-cli + a C compiler, both installed).
--   :TSInstall <lang>   add a language      :TSUpdate   update all parsers

vim.pack.add({
    { src = "https://github.com/nvim-treesitter/nvim-treesitter", version = "main" },
})

-- Re-compile parsers whenever the plugin itself gets updated by vim.pack
vim.api.nvim_create_autocmd("PackChanged", {
    callback = function(ev)
        if ev.data.spec.name == "nvim-treesitter" and ev.data.kind == "update" then
            vim.cmd("TSUpdate")
        end
    end,
})

require("nvim-treesitter").install({
    "bash", "c", "css", "diff", "gitcommit", "git_config", "html", "javascript",
    "json", "lua", "markdown", "markdown_inline", "python", "query", "regex",
    "toml", "typescript", "vim", "vimdoc", "yaml",
})

-- Turn Treesitter on for every buffer that has a parser
vim.api.nvim_create_autocmd("FileType", {
    callback = function(args)
        if pcall(vim.treesitter.start, args.buf) then
            vim.bo[args.buf].indentexpr = "v:lua.require'nvim-treesitter'.indentexpr()"
        end
    end,
})
