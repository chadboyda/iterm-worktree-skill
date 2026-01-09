# iTerm2 Worktree Manager

A Claude Code skill for managing git worktrees with seamless iTerm2 integration. Work on multiple features in parallel, each in its own isolated environment with dedicated terminal tabs.

## Features

- **Create Worktrees** - Spin up isolated development environments with a single command
- **iTerm2 Integration** - Automatically opens worktrees in new tabs, windows, or panes
- **Branch from Current** - Fork from your current branch with `--from-current`
- **Launch Claude** - Optionally start a Claude Code session in the new worktree
- **Safe Cleanup** - Validates uncommitted changes and unpushed commits before removal
- **Tab Management** - Switch between worktrees or list all with iTerm2 status indicators

## Installation

### Via Claude Code Marketplace (Recommended)

Install from the [chadboyda-agent-marketplace](https://github.com/chadboyda/chadboyda-agent-marketplace):

```
/plugin marketplace add chadboyda/chadboyda-agent-marketplace
/plugin install iterm-worktree@chadboyda-agent-marketplace
```

### Manual Installation

Clone directly to your Claude Code skills directory:

```bash
git clone https://github.com/chadboyda/iterm-worktree-skill.git ~/.claude/skills/iterm-worktree
```

### Standalone Usage

The script works independently without Claude Code:

```bash
git clone https://github.com/chadboyda/iterm-worktree-skill.git
cd iterm-worktree-skill
python3 scripts/worktree.py --help
```

## Usage

### Create a Worktree

```bash
# Basic - branches from main/master
python3 scripts/worktree.py create feature-auth

# Branch from a specific base
python3 scripts/worktree.py create feature-auth --base develop

# Branch from current branch
python3 scripts/worktree.py create feature-auth --from-current

# Open in new window instead of tab
python3 scripts/worktree.py create feature-auth --open-mode new_window

# Launch Claude with a task
python3 scripts/worktree.py create feature-auth --claude --task "Implement user authentication"
```

**Options:**
| Flag | Short | Description |
|------|-------|-------------|
| `--base` | `-b` | Base branch (default: main/master) |
| `--from-current` | `-f` | Branch from current branch |
| `--path` | `-p` | Custom worktree path |
| `--open-mode` | `-o` | `new_tab`, `new_window`, `new_pane_right`, `new_pane_below` |
| `--no-iterm` | | Skip iTerm2 automation |
| `--claude` | `-c` | Launch Claude in the new tab |
| `--task` | `-t` | Task description for Claude |

### List Worktrees

```bash
# Show all worktrees with iTerm2 tab status
python3 scripts/worktree.py list

# Output as JSON
python3 scripts/worktree.py list --json
```

### Switch to a Worktree

```bash
# Focus the iTerm2 tab for a worktree (opens new tab if not found)
python3 scripts/worktree.py switch feature-auth
```

### Open an Existing Worktree

```bash
# Open in new tab
python3 scripts/worktree.py open feature-auth

# Open in split pane
python3 scripts/worktree.py open feature-auth --open-mode new_pane_right

# Force new tab even if already open
python3 scripts/worktree.py open feature-auth --force
```

### Close a Worktree

```bash
# Safe removal (validates clean state)
python3 scripts/worktree.py close feature-auth

# Also delete the branch
python3 scripts/worktree.py close feature-auth --delete-branch

# Force removal (skip validation)
python3 scripts/worktree.py close feature-auth --force
```

## Typical Workflow

```bash
# 1. Start a new feature from main
python3 scripts/worktree.py create feature-dashboard --claude --task "Build analytics dashboard"

# 2. Start another feature in parallel (from current branch)
python3 scripts/worktree.py create feature-charts --from-current

# 3. Switch between features
python3 scripts/worktree.py switch feature-dashboard

# 4. Check what's active
python3 scripts/worktree.py list

# 5. After merging, clean up
python3 scripts/worktree.py close feature-dashboard --delete-branch
```

## Requirements

- macOS with iTerm2
- Python 3.6+
- Git

## How It Works

The skill uses:
- **Git worktrees** for isolated working directories sharing the same repository
- **AppleScript** for iTerm2 automation (creating tabs, windows, panes)
- **Session path detection** to track which tabs are running which worktrees

Each worktree gets its own directory (as a sibling to your main repo by default) and its own branch, allowing you to work on multiple features without stashing or switching branches.

## Credits

This skill was inspired by [claude-code-iterm-worktree-mcp](https://github.com/timoconnellaus/claude-code-iterm-worktree-mcp) by [@timoconnellaus](https://github.com/timoconnellaus). The original project implements similar functionality as an MCP (Model Context Protocol) server. This version reimplements the concept as a native Claude Code skill for simpler installation and usage.

## License

MIT License - see [LICENSE](LICENSE) file.
