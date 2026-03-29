# Auto-Approve Copilot Commands in VS Code

To stop Copilot from asking permission before running terminal commands and tool calls, add one or both of these to your VS Code `settings.json` (`Cmd + ,` → search the setting name, or edit JSON directly):

## Option 1 — Auto-approve all tool invocations

```json
"github.copilot.chat.tools.autoApprove": true
```

This covers terminal commands, file edits, and any other tool calls.

## Option 2 — Auto-confirm terminal commands only

```json
"github.copilot.chat.commandAutoConfirm": "allow"
```

This specifically targets shell commands run in the terminal.

## How to edit settings.json

1. Open the Command Palette: `Cmd + Shift + P`
2. Type **"Preferences: Open User Settings (JSON)"**
3. Add the desired setting(s)
4. Save the file — takes effect immediately
