#!/usr/bin/env bash
# C# language server for Neovim: csharp-ls (Roslyn, the compiler Visual Studio
# uses) is not packaged for Arch, it comes as a dotnet tool into
# ~/.dotnet/tools (no root needed). Skipped until dotnet-sdk is installed
# (packages/dev.txt); `chezmoi apply` then installs it. Update by hand:
#   dotnet tool update --global csharp-ls
# tools: csharp-ls
set -uo pipefail
export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1
command -v dotnet >/dev/null || { echo "dotnet-tools: dotnet-sdk not installed yet, skipped"; exit 0; }
if dotnet tool list --global | grep -q '^csharp-ls '; then
    echo "dotnet-tools: csharp-ls already installed"
else
    dotnet tool install --global csharp-ls
fi
