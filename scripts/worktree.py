#!/usr/bin/env python3
"""
Git Worktree Manager with iTerm2 Integration

Manages git worktrees with automatic iTerm2 tab/window creation.
Provides create, close, list, switch, and open operations.
"""

import subprocess
import sys
import json
import os
import argparse
from pathlib import Path


def run_git(*args, cwd=None, check=True):
    """Run a git command and return output."""
    result = subprocess.run(
        ["git"] + list(args),
        capture_output=True,
        text=True,
        cwd=cwd
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"Git error: {result.stderr.strip()}")
    return result


def get_repo_root(cwd=None):
    """Get the root directory of the git repository."""
    result = run_git("rev-parse", "--show-toplevel", cwd=cwd)
    return result.stdout.strip()


def get_worktrees(cwd=None):
    """List all worktrees in the repository."""
    result = run_git("worktree", "list", "--porcelain", cwd=cwd)
    worktrees = []
    current = {}

    for line in result.stdout.strip().split("\n"):
        if not line:
            if current:
                worktrees.append(current)
                current = {}
            continue

        if line.startswith("worktree "):
            current["path"] = line[9:]
        elif line.startswith("HEAD "):
            current["head"] = line[5:]
        elif line.startswith("branch "):
            current["branch"] = line[7:].replace("refs/heads/", "")
        elif line == "bare":
            current["bare"] = True
        elif line == "detached":
            current["detached"] = True

    if current:
        worktrees.append(current)

    return worktrees


def branch_exists(branch_name, cwd=None):
    """Check if a branch already exists."""
    result = run_git("branch", "--list", branch_name, cwd=cwd, check=False)
    return bool(result.stdout.strip())


def get_default_branch(cwd=None):
    """Get the default branch name (main or master)."""
    result = run_git("symbolic-ref", "refs/remotes/origin/HEAD", cwd=cwd, check=False)
    if result.returncode == 0:
        return result.stdout.strip().replace("refs/remotes/origin/", "")

    # Fallback to checking common names
    for branch in ["main", "master"]:
        if branch_exists(branch, cwd=cwd):
            return branch
    return "main"


def get_current_branch(cwd=None):
    """Get the current branch name."""
    result = run_git("rev-parse", "--abbrev-ref", "HEAD", cwd=cwd, check=False)
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def has_uncommitted_changes(worktree_path):
    """Check if worktree has uncommitted changes."""
    result = run_git("status", "--porcelain", cwd=worktree_path, check=False)
    return bool(result.stdout.strip())


def has_unpushed_commits(worktree_path):
    """Check if worktree has unpushed commits."""
    result = run_git("log", "@{u}..", "--oneline", cwd=worktree_path, check=False)
    if result.returncode != 0:
        # No upstream set, check if there are any commits
        return False
    return bool(result.stdout.strip())


def automate_iterm(worktree_path, open_mode="new_tab", run_claude=False, task_description=None):
    """Open worktree in iTerm2 using AppleScript."""

    # Build the command to run in iTerm
    cd_cmd = f'cd "{worktree_path}"'

    if run_claude and task_description:
        # Escape quotes in task description for shell
        escaped_task = task_description.replace('"', '\\"').replace("'", "'\\''")
        full_cmd = f'{cd_cmd} && claude --allowedTools "Bash,Read,Write,Edit,Glob,Grep,WebFetch,WebSearch" "{escaped_task}"'
    else:
        full_cmd = cd_cmd

    # Escape double quotes for AppleScript embedding
    full_cmd_escaped = full_cmd.replace('\\', '\\\\').replace('"', '\\"')

    applescript = ""

    if open_mode == "new_window":
        applescript = f'''
tell application "iTerm2"
    create window with default profile
    tell current session of current window
        write text "{full_cmd_escaped}"
    end tell
    activate
end tell
'''
    elif open_mode == "new_pane_right":
        applescript = f'''
tell application "iTerm2"
    tell current session of current window
        set newSession to (split vertically with default profile)
        tell newSession
            write text "{full_cmd_escaped}"
        end tell
    end tell
    activate
end tell
'''
    elif open_mode == "new_pane_below":
        applescript = f'''
tell application "iTerm2"
    tell current session of current window
        set newSession to (split horizontally with default profile)
        tell newSession
            write text "{full_cmd_escaped}"
        end tell
    end tell
    activate
end tell
'''
    else:  # new_tab (default)
        applescript = f'''
tell application "iTerm2"
    tell current window
        create tab with default profile
        tell current session
            write text "{full_cmd_escaped}"
        end tell
    end tell
    activate
end tell
'''

    result = subprocess.run(
        ["osascript", "-e", applescript],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f"iTerm2 automation failed: {result.stderr}")

    return True


def get_iterm_tabs():
    """Get all iTerm2 tabs with their working directories."""
    applescript = '''
tell application "iTerm2"
    set tabInfo to {}
    repeat with w in windows
        set windowId to id of w
        repeat with t in tabs of w
            repeat with s in sessions of t
                try
                    set sessionPath to variable named "session.path" in s
                    set end of tabInfo to {windowId, sessionPath}
                end try
            end repeat
        end repeat
    end repeat
    return tabInfo
end tell
'''
    result = subprocess.run(
        ["osascript", "-e", applescript],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return []

    # Parse the output
    tabs = []
    output = result.stdout.strip()
    if output:
        # osascript returns nested lists as comma-separated values
        parts = output.split(", ")
        for i in range(0, len(parts), 2):
            if i + 1 < len(parts):
                try:
                    window_id = int(parts[i])
                    path = parts[i + 1]
                    tabs.append({"window_id": window_id, "path": path})
                except (ValueError, IndexError):
                    continue

    return tabs


def switch_to_tab(worktree_path):
    """Switch to an iTerm2 tab running in the specified worktree."""
    normalized_path = os.path.normpath(worktree_path)

    applescript = f'''
tell application "iTerm2"
    repeat with w in windows
        repeat with t in tabs of w
            repeat with s in sessions of t
                try
                    set sessionPath to variable named "session.path" in s
                    if sessionPath is equal to "{normalized_path}" then
                        select t
                        set frontmost of w to true
                        activate
                        return "found"
                    end if
                end try
            end repeat
        end repeat
    end repeat
    return "not_found"
end tell
'''

    result = subprocess.run(
        ["osascript", "-e", applescript],
        capture_output=True,
        text=True
    )

    return "found" in result.stdout


def cmd_create(args):
    """Create a new worktree with a feature branch."""
    repo_root = get_repo_root()
    branch_name = args.branch

    # Determine base branch
    if args.from_current:
        base_branch = get_current_branch()
        if not base_branch:
            print("Error: Could not determine current branch", file=sys.stderr)
            return 1
        print(f"Branching from current branch: {base_branch}")
    else:
        base_branch = args.base or get_default_branch()

    # Determine worktree path
    if args.path:
        worktree_path = os.path.abspath(args.path)
    else:
        # Create sibling directory with branch name
        parent_dir = os.path.dirname(repo_root)
        worktree_path = os.path.join(parent_dir, branch_name)

    # Validate
    if branch_exists(branch_name):
        print(f"Error: Branch '{branch_name}' already exists", file=sys.stderr)
        return 1

    if os.path.exists(worktree_path):
        print(f"Error: Path '{worktree_path}' already exists", file=sys.stderr)
        return 1

    # Create the worktree with new branch
    print(f"Creating worktree at {worktree_path} with branch {branch_name}...")
    run_git("worktree", "add", "-b", branch_name, worktree_path, base_branch)

    # Open in iTerm2
    if not args.no_iterm:
        print(f"Opening in iTerm2 ({args.open_mode})...")
        automate_iterm(
            worktree_path,
            open_mode=args.open_mode,
            run_claude=args.claude,
            task_description=args.task
        )

    print(f"Worktree created successfully: {worktree_path}")
    return 0


def cmd_close(args):
    """Close and remove a worktree."""
    worktrees = get_worktrees()

    # Find the worktree
    target = None
    search = args.worktree

    for wt in worktrees:
        if wt.get("branch") == search or wt.get("path") == search or wt.get("path", "").endswith(f"/{search}"):
            target = wt
            break

    if not target:
        print(f"Error: Worktree '{search}' not found", file=sys.stderr)
        return 1

    worktree_path = target["path"]
    branch = target.get("branch")

    # Check for uncommitted changes
    if has_uncommitted_changes(worktree_path):
        if not args.force:
            print(f"Error: Worktree has uncommitted changes. Use --force to override.", file=sys.stderr)
            return 1
        print("Warning: Forcing removal despite uncommitted changes")

    # Check for unpushed commits
    if has_unpushed_commits(worktree_path):
        if not args.force:
            print(f"Error: Worktree has unpushed commits. Use --force to override.", file=sys.stderr)
            return 1
        print("Warning: Forcing removal despite unpushed commits")

    # Remove the worktree
    print(f"Removing worktree at {worktree_path}...")
    run_git("worktree", "remove", worktree_path, "--force" if args.force else None)

    # Optionally delete the branch
    if args.delete_branch and branch:
        print(f"Deleting branch {branch}...")
        run_git("branch", "-D" if args.force else "-d", branch, check=False)

    print("Worktree closed successfully")
    return 0


def cmd_list(args):
    """List all active worktrees."""
    worktrees = get_worktrees()
    iterm_tabs = get_iterm_tabs() if not args.no_iterm else []

    # Create a set of paths that have iTerm tabs
    tab_paths = {os.path.normpath(t["path"]) for t in iterm_tabs if "path" in t}

    if args.json:
        output = []
        for wt in worktrees:
            wt["has_iterm_tab"] = os.path.normpath(wt.get("path", "")) in tab_paths
            output.append(wt)
        print(json.dumps(output, indent=2))
    else:
        print("Active Worktrees:")
        print("-" * 60)
        for wt in worktrees:
            path = wt.get("path", "unknown")
            branch = wt.get("branch", "detached")
            has_tab = os.path.normpath(path) in tab_paths
            tab_indicator = " [iTerm]" if has_tab else ""
            print(f"  {branch}: {path}{tab_indicator}")

    return 0


def cmd_switch(args):
    """Switch to a worktree's iTerm2 tab."""
    worktrees = get_worktrees()

    # Find the worktree
    target = None
    search = args.worktree

    for wt in worktrees:
        if wt.get("branch") == search or wt.get("path") == search or wt.get("path", "").endswith(f"/{search}"):
            target = wt
            break

    if not target:
        print(f"Error: Worktree '{search}' not found", file=sys.stderr)
        return 1

    worktree_path = target["path"]

    if switch_to_tab(worktree_path):
        print(f"Switched to worktree: {target.get('branch', worktree_path)}")
        return 0
    else:
        print(f"No iTerm2 tab found for worktree. Opening new tab...")
        automate_iterm(worktree_path, open_mode=args.open_mode)
        return 0


def cmd_open(args):
    """Open an existing worktree in iTerm2."""
    worktrees = get_worktrees()

    # Find the worktree
    target = None
    search = args.worktree

    for wt in worktrees:
        if wt.get("branch") == search or wt.get("path") == search or wt.get("path", "").endswith(f"/{search}"):
            target = wt
            break

    if not target:
        print(f"Error: Worktree '{search}' not found", file=sys.stderr)
        return 1

    worktree_path = target["path"]

    # Check if already open
    if not args.force and switch_to_tab(worktree_path):
        print(f"Worktree already open, switched to existing tab")
        return 0

    # Open new tab
    automate_iterm(
        worktree_path,
        open_mode=args.open_mode,
        run_claude=args.claude,
        task_description=args.task
    )
    print(f"Opened worktree: {target.get('branch', worktree_path)}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Git Worktree Manager with iTerm2 Integration"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new worktree")
    create_parser.add_argument("branch", help="Name for the new branch")
    create_parser.add_argument("--base", "-b", help="Base branch (default: main/master)")
    create_parser.add_argument("--from-current", "-f", action="store_true",
                               help="Branch from current branch instead of main/master")
    create_parser.add_argument("--path", "-p", help="Custom path for worktree")
    create_parser.add_argument("--open-mode", "-o",
                               choices=["new_tab", "new_window", "new_pane_right", "new_pane_below"],
                               default="new_tab", help="How to open in iTerm2")
    create_parser.add_argument("--no-iterm", action="store_true", help="Don't open in iTerm2")
    create_parser.add_argument("--claude", "-c", action="store_true", help="Run Claude in the new tab")
    create_parser.add_argument("--task", "-t", help="Task description for Claude")
    create_parser.set_defaults(func=cmd_create)

    # Close command
    close_parser = subparsers.add_parser("close", help="Close and remove a worktree")
    close_parser.add_argument("worktree", help="Branch name or path of worktree")
    close_parser.add_argument("--force", "-f", action="store_true", help="Force removal")
    close_parser.add_argument("--delete-branch", "-d", action="store_true", help="Also delete the branch")
    close_parser.set_defaults(func=cmd_close)

    # List command
    list_parser = subparsers.add_parser("list", help="List active worktrees")
    list_parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    list_parser.add_argument("--no-iterm", action="store_true", help="Don't check iTerm2 tabs")
    list_parser.set_defaults(func=cmd_list)

    # Switch command
    switch_parser = subparsers.add_parser("switch", help="Switch to a worktree's iTerm2 tab")
    switch_parser.add_argument("worktree", help="Branch name or path of worktree")
    switch_parser.add_argument("--open-mode", "-o",
                               choices=["new_tab", "new_window", "new_pane_right", "new_pane_below"],
                               default="new_tab", help="How to open if no tab exists")
    switch_parser.set_defaults(func=cmd_switch)

    # Open command
    open_parser = subparsers.add_parser("open", help="Open an existing worktree in iTerm2")
    open_parser.add_argument("worktree", help="Branch name or path of worktree")
    open_parser.add_argument("--open-mode", "-o",
                             choices=["new_tab", "new_window", "new_pane_right", "new_pane_below"],
                             default="new_tab", help="How to open in iTerm2")
    open_parser.add_argument("--force", "-f", action="store_true", help="Open new tab even if already open")
    open_parser.add_argument("--claude", "-c", action="store_true", help="Run Claude in the tab")
    open_parser.add_argument("--task", "-t", help="Task description for Claude")
    open_parser.set_defaults(func=cmd_open)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        return args.func(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
