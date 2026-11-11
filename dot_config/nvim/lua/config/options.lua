-- Editor options. `:help 'option'` explains any of them, e.g. :help 'scrolloff'
local o = vim.opt

-- Line numbers: absolute on the cursor line, relative elsewhere (great for 5j, 3k, ...)
o.number = true
o.relativenumber = true
o.cursorline = true -- highlight the line the cursor is on
o.signcolumn = "yes" -- always show the sign column (git/diagnostics), no jumping text

-- Indentation: 4 spaces, never tabs
o.tabstop = 4
o.shiftwidth = 4
o.expandtab = true
o.smartindent = true
o.breakindent = true -- wrapped lines keep their indentation

-- Search: case-insensitive, unless the search contains a capital letter
o.ignorecase = true
o.smartcase = true
o.inccommand = "split" -- live preview of :s/old/new/ in a split

-- Windows
o.splitright = true -- vertical splits open to the right
o.splitbelow = true -- horizontal splits open below
o.scrolloff = 10 -- keep 10 lines visible above/below the cursor

-- Show invisible characters that usually mean trouble
o.list = true
o.listchars = { tab = "» ", trail = "·", nbsp = "␣" }

-- Behaviour
o.mouse = "a" -- mouse works in all modes
o.showmode = false -- the statusline shows the mode later on
o.undofile = true -- undo history survives closing the file
o.updatetime = 250 -- faster CursorHold events (diagnostics, git signs)
o.timeoutlen = 300 -- time to finish a key sequence like <leader>sf
o.confirm = true -- ask to save instead of failing on :q with changes
o.termguicolors = true

-- System clipboard (wl-clipboard). Scheduled so it does not slow down startup.
vim.schedule(function()
    o.clipboard = "unnamedplus"
end)
