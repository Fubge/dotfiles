-- Autocommands: run code automatically on events. :help autocmd
local group = vim.api.nvim_create_augroup("user", { clear = true })

-- Briefly highlight what you just yanked (copied)
vim.api.nvim_create_autocmd("TextYankPost", {
    group = group,
    callback = function() vim.hl.on_yank() end,
})

-- Reopen a file at the line where you left it
vim.api.nvim_create_autocmd("BufReadPost", {
    group = group,
    callback = function(args)
        local mark = vim.api.nvim_buf_get_mark(args.buf, '"')
        if mark[1] > 0 and mark[1] <= vim.api.nvim_buf_line_count(args.buf) then
            pcall(vim.api.nvim_win_set_cursor, 0, mark)
        end
    end,
})
