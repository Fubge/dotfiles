-- Settings made in the system menu (SUPER+ALT+Space, ~/.local/bin/system-menu).
-- They are machine-local: ~/.local/state/slate/settings.lua (written by the
-- menu next to settings.json, never by chezmoi). Only changed values are in
-- there; the modules fall back to their own defaults for the rest.
--
-- Modules register what to redo when a section changes:
--     S.on_apply("mouse", function() ... end)
-- The menu calls the global Slate.apply("mouse") through `hyprctl eval`,
-- which reloads the file and runs those functions.

local S = { appliers = {} }
local path = os.getenv("HOME") .. "/.local/state/slate/settings.lua"

function S.load()
    local ok, t = pcall(dofile, path)
    S.data = (ok and type(t) == "table") and t or {}
end

-- One section as a table (empty if never set)
function S.get(section)
    return S.data[section] or {}
end

-- value, or the default when it was never set (false is a value)
function S.pick(value, default)
    if value == nil then return default end
    return value
end

function S.on_apply(section, fn)
    S.appliers[section] = S.appliers[section] or {}
    table.insert(S.appliers[section], fn)
end

function S.apply(section)
    S.load()
    for name, fns in pairs(S.appliers) do
        if section == nil or section == name then
            for _, fn in ipairs(fns) do fn() end
        end
    end
end

S.load()
Slate = S   -- global on purpose: reachable from `hyprctl eval`
return S
