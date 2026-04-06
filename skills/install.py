#!/usr/bin/env python3
"""
api-probe skills installer

Usage:
    api-probe init
"""

import hashlib
import json
import sys
import tty
import termios
from pathlib import Path

# ── Version ───────────────────────────────────────────────────────────────────
# Bump this whenever prompt/command files are updated.
# On init, if the installed version differs, all files for that tool are
# reinstalled automatically — no manual action required from the user.

VERSION = "0.0.2"

# ── Paths ─────────────────────────────────────────────────────────────────────

WORKSPACE     = Path.cwd()
SKILLS_DIR    = Path(__file__).parent
MANIFEST_PATH = WORKSPACE / ".api-probe" / "skills-manifest.json"

# ── Console helpers ───────────────────────────────────────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
GREEN  = "\033[32m"
RED    = "\033[31m"
CYAN   = "\033[36m"
YELLOW = "\033[33m"


def _header(text: str) -> None:
    print(f"\n  {BOLD}{CYAN}{'─' * 52}{RESET}")
    print(f"  {BOLD}{CYAN}  {text}{RESET}")
    print(f"  {BOLD}{CYAN}{'─' * 52}{RESET}\n")


def _ok(text: str)   -> None: print(f"  {GREEN}✓{RESET}  {text}")
def _err(text: str)  -> None: print(f"  {RED}✗{RESET}  {text}")
def _info(text: str) -> None: print(f"  {DIM}   {text}{RESET}")
def _warn(text: str) -> None: print(f"  {YELLOW}!{RESET}  {text}")


def _select(question: str, options: list) -> str:
    """Arrow key + Enter/Space to select. Returns the selected key."""
    selected = 0
    n = len(options)

    def _draw(first: bool = False) -> None:
        if not first:
            # Move cursor back up to the first option line
            sys.stdout.write(f"\033[{n}A")
        for i, (_, label) in enumerate(options):
            marker = f"{CYAN}❯{RESET}" if i == selected else " "
            sys.stdout.write(f"\033[2K\r    {marker}  {label}\n")
        sys.stdout.flush()

    print(f"\n  {BOLD}{question}{RESET}\n")
    sys.stdout.write("\033[?25l")  # hide cursor
    sys.stdout.flush()
    _draw(first=True)

    fd  = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while True:
            ch = sys.stdin.read(1)
            if ch == "\x1b":                    # ESC — start of arrow key sequence
                ch = sys.stdin.read(1)
                if ch == "[":
                    ch = sys.stdin.read(1)
                    if ch == "A":               # Up arrow
                        selected = max(0, selected - 1)
                        _draw()
                    elif ch == "B":             # Down arrow
                        selected = min(n - 1, selected + 1)
                        _draw()
            elif ch in ("\r", "\n", " "):       # Enter or Space — confirm
                break
            elif ch == "\x03":                  # Ctrl-C
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
                print()
                sys.exit(0)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        sys.stdout.write("\033[?25h")  # restore cursor
        sys.stdout.flush()

    # Print the confirmed selection
    label = next(label for key, label in options if key == options[selected][0])
    print(f"\n  {DIM}Selected: {label}{RESET}\n")
    return options[selected][0]


# ── Project detection ─────────────────────────────────────────────────────────

SUPPORTED_PROJECTS = [
    ("Node.js",  ["package.json"]),
    ("Python",   ["pyproject.toml", "setup.py", "requirements.txt", "Pipfile"]),
    ("Java",     ["pom.xml", "build.gradle", "build.gradle.kts"]),
    ("Go",       ["go.mod"]),
    ("Rust",     ["Cargo.toml"]),
    (".NET",     ["*.csproj", "*.sln"]),
    ("Ruby",     ["Gemfile"]),
    ("PHP",      ["composer.json"]),
]


def detect_project() -> str:
    if not WORKSPACE.exists() or not any(WORKSPACE.iterdir()):
        _err("Current directory is empty.")
        _info("Run this command from the root of your project.")
        sys.exit(1)

    for project_type, signals in SUPPORTED_PROJECTS:
        for signal in signals:
            if "*" in signal:
                if any(WORKSPACE.glob(signal)):
                    return project_type
            elif (WORKSPACE / signal).exists():
                return project_type

    _err("Could not identify the project type.")
    _info("Run this command from the root of your project.")
    print(f"\n  Supported project types:\n")
    for project_type, signals in SUPPORTED_PROJECTS:
        print(f"    • {project_type:10s}  {', '.join(signals)}")
    print()
    sys.exit(1)


# ── Checksum ──────────────────────────────────────────────────────────────────

def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def _load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        try:
            return json.loads(MANIFEST_PATH.read_text())
        except Exception:
            pass
    return {}


def _save_manifest(manifest: dict) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))


# ── Tool file definitions ─────────────────────────────────────────────────────

TOOL_FILES = {
    "copilot": [
        (
            SKILLS_DIR / "copilot" / "prompts" / "api-probe-generate.prompt.md",
            WORKSPACE / ".github" / "prompts" / "api-probe-generate.prompt.md",
        ),
        (
            SKILLS_DIR / "copilot" / "prompts" / "api-probe-sync.prompt.md",
            WORKSPACE / ".github" / "prompts" / "api-probe-sync.prompt.md",
        ),
    ],
    "claude": [
        (
            SKILLS_DIR / "claude" / "commands" / "generate.md",
            WORKSPACE / ".claude" / "commands" / "api-probe" / "generate.md",
        ),
        (
            SKILLS_DIR / "claude" / "commands" / "sync.md",
            WORKSPACE / ".claude" / "commands" / "api-probe" / "sync.md",
        ),
    ],
}

TOOLS = [
    ("copilot", "GitHub Copilot"),
    ("claude",  "Claude Code"),
]


# ── Installer ─────────────────────────────────────────────────────────────────

def _version_key(tool: str) -> str:
    return f"{tool}:version"


def _needs_upgrade(tool: str, manifest: dict) -> bool:
    return manifest.get(_version_key(tool)) != VERSION


def install_file(key: str, src: Path, dest: Path, manifest: dict, force: bool = False) -> bool:
    new_content = src.read_text()
    checksum    = _sha256(new_content)

    if not force and dest.exists() and manifest.get(key) == checksum:
        _info(f"no change   {dest.relative_to(WORKSPACE)}")
        return False

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(new_content)
    manifest[key] = checksum
    _ok(str(dest.relative_to(WORKSPACE)))
    return True


def install_tool(tool: str, manifest: dict) -> None:
    upgrade           = _needs_upgrade(tool, manifest)
    installed_version = manifest.get(_version_key(tool))

    if upgrade and installed_version:
        _warn(f"Upgrading skills from v{installed_version} → v{VERSION}")
    elif upgrade:
        _info(f"Installing skills v{VERSION}")

    changed = False
    for src, dest in TOOL_FILES[tool]:
        key = f"{tool}:{src.relative_to(SKILLS_DIR)}"
        changed = changed | install_file(key, src, dest, manifest, force=upgrade)

    manifest[_version_key(tool)] = VERSION

    if not changed and not upgrade:
        print(f"\n  Already up to date (v{VERSION}).")


# ── Destroy ───────────────────────────────────────────────────────────────────

def _cleanup_empty_dirs(start: Path) -> None:
    """Walk up from start toward WORKSPACE, removing each directory if it is empty.
    Stops as soon as a non-empty directory is encountered, or when WORKSPACE is reached.
    Never removes the workspace root itself."""
    d = start
    while d != WORKSPACE and d != d.parent:
        try:
            d.rmdir()                                            # succeeds only when empty
            _info(f"Removed empty dir  {d.relative_to(WORKSPACE)}")
            d = d.parent
        except OSError:
            break                                                # not empty — stop walking up


def destroy_tool(tool: str, manifest: dict) -> None:
    """Remove exactly the files placed by install_tool, then clean up any directories
    that became empty as a result. Directories that contain other files are left alone."""
    dirs_to_check: list[Path] = []

    for src, dest in TOOL_FILES[tool]:
        if dest.exists():
            dest.unlink()
            _ok(f"Removed  {dest.relative_to(WORKSPACE)}")
        # Collect unique parent dirs in order (innermost first)
        if dest.parent not in dirs_to_check:
            dirs_to_check.append(dest.parent)

    # Walk up from each parent directory, removing empty ones
    visited: set[Path] = set()
    for d in dirs_to_check:
        if d not in visited:
            visited.add(d)
            _cleanup_empty_dirs(d)

    for key in [k for k in manifest if k.startswith(f"{tool}:")]:
        del manifest[key]


def destroy() -> None:
    _header("api-probe destroy")

    manifest = _load_manifest()

    installed = [(t, l) for t, l in TOOLS if manifest.get(_version_key(t))]
    if not installed:
        _info("No api-probe skills are installed in this project.")
        return

    print("  The following will be removed:\n")
    for tool, label in installed:
        print(f"  {BOLD}{label}{RESET}")
        for src, dest in TOOL_FILES[tool]:
            if dest.exists():
                print(f"    • {dest.relative_to(WORKSPACE)}")
    print()

    confirm = _select("Remove these files?", [
        ("yes", "Yes, remove api-probe skills"),
        ("no",  "No, cancel"),
    ])
    if confirm == "no":
        _info("Cancelled.")
        return

    print()
    for tool, _ in installed:
        destroy_tool(tool, manifest)

    _save_manifest(manifest)

    api_probe_dir = WORKSPACE / ".api-probe"
    if api_probe_dir.exists():
        remaining = list(api_probe_dir.iterdir())
        if remaining:
            print()
            confirm2 = _select(
                f"Also remove .api-probe/ ({len(remaining)} file(s) inside)?",
                [("yes", "Yes, remove .api-probe/"), ("no", "Keep .api-probe/")],
            )
            if confirm2 == "yes":
                import shutil
                shutil.rmtree(api_probe_dir)
                _ok("Removed .api-probe/")
        else:
            api_probe_dir.rmdir()
            _ok("Removed .api-probe/")

    _header("Done")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "init"

    if cmd == "destroy":
        destroy()
        return

    _header("api-probe skill installer")

    project_type = detect_project()
    _ok(f"Project detected: {BOLD}{project_type}{RESET}")

    selected = _select("Which AI tool would you like to configure?", TOOLS)

    manifest = _load_manifest()
    print(f"  Installing ...\n")
    install_tool(selected, manifest)

    _save_manifest(manifest)
    _header("Done")


if __name__ == "__main__":
    main()
