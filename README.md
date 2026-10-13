# reverse-engineer

Claude Code workspace with [REA (Reverse Engineer Anything)](https://github.com/morluto/rea) installed at project scope:

- `.mcp.json` registers the REA MCP server (`npx -y rea-agents@6.4.0 mcp`).
- `.claude/skills/reverse-engineer-anything/` is the matching REA skill (v6.4.0).

Native binary decompilation also needs Hopper, Ghidra or IDA on the machine running Claude Code; JavaScript/Electron, .NET, Go, WASM and archive inspection work without one.

To update: `npx rea-agents@latest setup --client claude_code --dry-run`, then refresh these files.
