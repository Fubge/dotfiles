-- Bash language server (uses shellcheck for warnings)
return {
    cmd = { "bash-language-server", "start" },
    filetypes = { "sh", "bash", "zsh" },
    root_markers = { ".git" },
}
