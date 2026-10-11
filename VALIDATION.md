# Validation

Real-world validation of Super Debugger across MCP-compatible clients.

## Summary

| Client | ping | debug_run | debug_continue | debug_stop |
| :--- | :--- | :--- | :--- | :--- |
| MCP Inspector | ✅ | ✅ | ✅ | ✅ |
| Claude Desktop | ✅ | ✅ | ✅ | ✅ |
| VS Code + GitHub Copilot Chat | ✅ | ✅ | ✅ | ✅ |
| Cline | ✅ | ✅ | ✅ | ✅ |
| Continue | ✅ | ✅ | ✅ | ✅ |
| Cursor | ⏳ | ⏳ | ⏳ | ⏳ |

**5 of 6 clients fully validated.**

## Details per client

### MCP Inspector (official Anthropic inspector)
- **Model**: N/A (raw MCP calls)
- **Result**: All 9 tools callable
- **Notes**: Reference for protocol-level validation

### Claude Desktop
- **Model**: Claude Sonnet (desktop default)
- **Result**: Full cycle works out of the box
- **Notes**: No special configuration needed

### VS Code + GitHub Copilot Chat
- **Result**: Full cycle works
- **Notes**: `mcp.json` must point `command` to the project `.venv` interpreter
  (not the global `python` binary)

### Cline
- **Model**: Pixel Canary (free tier)
- **Result**: Full cycle works with explicit prompts
- **Notes**: The free model tends to suggest terminal commands instead of
  MCP tools. Adding *"Usá EXCLUSIVAMENTE la herramienta MCP \"X\" del
  servidor \"Y\"..."* fixes it.

### Continue
- **Model**: Gemini 3.5 Flash Lite (free tier)
- **Result**: Full cycle works with two adjustments
- **Notes**:
  1. Requires `connectionTimeout: 120000` in `mcpServers` because FastMCP
     takes longer than the default timeout to boot.
  2. Same explicit-prompt requirement as Cline.

### Cursor
- **Status**: Not yet tested

## Test scenario

All validations used the same deterministic test:

```python
# test_target.py
import time

def compute():
    total = 0
    for i in range(5):
        total += i      # breakpoint at line 7
        time.sleep(0.1)
    return total

if __name__ == "__main__":
    result = compute()
    print(f"Resultado: {result}")