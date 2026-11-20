-- C# language server (csharp-ls, Roslyn based). Installed as a dotnet tool
-- (.chezmoiscripts/run_onchange_after_25-dotnet-tools.sh), needs dotnet-sdk.
-- It loads the solution (.sln) or project (.csproj) above the file; the first
-- start of a project takes a few seconds (restore). Besides errors, go to
-- definition etc. it sends semantic tokens: classes, interfaces, methods,
-- properties and locals each get their own color, more than Treesitter alone.
return {
    cmd = { vim.fn.expand("~/.dotnet/tools/csharp-ls") },
    filetypes = { "cs" },
    root_dir = function(bufnr, on_dir)
        local root = vim.fs.root(bufnr, function(name)
            return name:match("%.slnx?$") ~= nil
        end) or vim.fs.root(bufnr, function(name)
            return name:match("%.csproj$") ~= nil
        end)
        if root then
            on_dir(root)
        end
    end,
}
