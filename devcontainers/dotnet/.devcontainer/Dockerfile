# set platform for apple silicon users
FROM --platform=linux/amd64 mcr.microsoft.com/vscode/devcontainers/dotnet:8.0-bookworm

# Remove problematic yarn repository with expired GPG key
RUN sudo rm -f /etc/apt/sources.list.d/yarn.list 2>/dev/null || true