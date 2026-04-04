#!/usr/bin/env python3
"""
api-probe skills installer

Usage:
    api-probe init
"""

import hashlib
import json
import sys
from pathlib import Path

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


def _prompt(question: str, options: list) -> str:
    """Present a numbered list and return the selected key. Single selection only."""
    print(f"\n  {BOLD}{question}{RESET}\n")
    for i, (key, label) in enumerate(options, 1):
        print(f"    {CYAN}{i}{RESET})  {label}")
    print()
    while True:
        try:
            raw = input(f"  {BOLD}>{RESET} Enter number: ").strip()
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return options[idx][0]
        except (ValueError, EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)
        print(f"  Please enter a number between 1 and {len(options)}.")


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
#
# Each entry is: (source_path, destination_path)
# Files are owned entirely by api-probe — no section markers needed.

TOOL_FILES = {
    "copilot": [
        (
            SKILLS_DIR / "copilot" / "prompts" / "api-probe" / "generate.prompt.md",
            WORKSPACE / ".github" / "prompts" / "api-probe" / "generate.prompt.md",
        ),
        (
            SKILLS_DIR / "copilot" / "prompts" / "api-probe" / "sync.prompt.md",
            WORKSPACE / ".github" / "prompts" / "api-probe" / "sync.prompt.md",
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

def install_file(key: str, src: Path, dest: Path, manifest: dict) -> bool:
    """Copy src to dest, skipping if content is unchanged."""
    new_content = src.read_text()
    checksum    = _sha256(new_content)

    if dest.exists() and manifest.get(key) == checksum:
        _info(f"no change   {dest.relative_to(WORKSPACE)}")
        return False

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(new_content)
    manifest[key] = checksum
    _ok(str(dest.relative_to(WORKSPACE)))
    return True


def install_tool(tool: str, manifest: dict) -> None:
    changed = False

    for src, dest in TOOL_FILES[tool]:
        key = f"{tool}:{src.relative_to(SKILLS_DIR)}"
        changed = changed | install_file(key, src, dest, manifest)

    if not changed:
        print(f"\n  No changes detected.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    _header("api-probe skill installer")

    project_type = detect_project()
    _ok(f"Project detected: {BOLD}{project_type}{RESET}")

    selected = _prompt("Which AI tool would you like to configure?", TOOLS)

    manifest = _load_manifest()
    print(f"\n  Installing ...\n")
    install_tool(selected, manifest)

    _save_manifest(manifest)
    _header("Done")


if __name__ == "__main__":
    main()
