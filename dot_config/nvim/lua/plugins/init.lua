-- Plugins are managed by Neovim's built-in plugin manager `vim.pack`.
--   vim.pack.add({...})  installs (first start asks for confirmation) and loads plugins
--   :lua vim.pack.update()  fetches updates, :w confirms, :q cancels
-- Exact versions are pinned in ~/.config/nvim/nvim-pack-lock.json (tracked in the repo).

require("plugins.ui")
require("plugins.search")
require("plugins.treesitter")
require("plugins.editing")
require("plugins.git")
