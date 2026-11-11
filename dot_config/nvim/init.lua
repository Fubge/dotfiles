-- Neovim config, built step by step.
-- Each module in lua/config/ covers one topic.

-- Leader key: <Space>. Must be set before any mapping uses <leader>.
vim.g.mapleader = " "
vim.g.maplocalleader = " "

require("config.options")
require("config.keymaps")
require("config.autocmds")
require("plugins")
require("config.lsp")
