#!/usr/bin/env python3
"""
api-probe skills installer

Installs api-probe Agent Skills (SKILL.md + bundled references/) into a
project, in the format expected by each AI tool.

Usage:
    api-probe init      # detect project, choose a tool, install/upgrade skills
    api-probe update    # re-sync installed skills with the bundled source,
                        #   rewriting any file whose on-disk content has drifted
    api-probe destroy   # remove api-probe skills (only the folders we own)
"""

import hashlib
import json
import shutil
import sys
import tty
import termios
from pathlib import Path

# ── Version ───────────────────────────────────────────────────────────────────
# Bump this whenever any skill file is updated.
# On init, if the installed version differs, all files for that tool are
# reinstalled automatically — no manual action required from the user.

VERSION = "0.1.0"

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


# ── Checksum / manifest ─────────────────────────────────────────────────────--

def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


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


# ── Skill + tool definitions ────────────────────────────────────────────────--
#
# Canonical, tool-agnostic skill sources live next to this script, one folder
# per skill (each containing SKILL.md plus optional references/, scripts/,
# assets/). Every tool receives the *identical* skill folder, only the
# destination root differs.

SKILLS = ["api-probe-generate", "api-probe-sync"]

# tool key -> (label, destination root for skill folders, relative to WORKSPACE)
TOOLS = [
    ("copilot", "GitHub Copilot", Path(".github") / "skills"),
    ("claude",  "Claude Code",    Path(".claude") / "skills"),
]

TOOL_LABEL = {key: label for key, label, _ in TOOLS}
TOOL_ROOT  = {key: root  for key, _, root in TOOLS}

# Stale paths left behind by pre-0.1.0 installs (flat command / prompt files).
# Removed on upgrade so users aren't left with both the old and new layout.
LEGACY_PATHS = {
    "claude":  [Path(".claude") / "commands" / "api-probe"],
    "copilot": [
        Path(".github") / "prompts" / "api-probe-generate.prompt.md",
        Path(".github") / "prompts" / "api-probe-sync.prompt.md",
    ],
}


def _iter_skill_files(skill: str):
    """Yield (src_path, rel_path) for every file in a skill source folder."""
    src_root = SKILLS_DIR / skill
    if not src_root.is_dir():
        _err(f"Skill source missing: {src_root}")
        sys.exit(1)
    for path in sorted(src_root.rglob("*")):
        if path.is_file():
            yield path, path.relative_to(src_root)


# ── Installer ─────────────────────────────────────────────────────────────────

def _version_key(tool: str) -> str:
    return f"{tool}:version"


def _needs_upgrade(tool: str, manifest: dict) -> bool:
    return manifest.get(_version_key(tool)) != VERSION


def install_file(key: str, src: Path, dest: Path, manifest: dict, force: bool) -> bool:
    new_bytes = src.read_bytes()
    checksum  = _sha256(new_bytes)

    if not force and dest.exists() and manifest.get(key) == checksum:
        _info(f"no change   {dest.relative_to(WORKSPACE)}")
        return False

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(new_bytes)
    manifest[key] = checksum
    _ok(str(dest.relative_to(WORKSPACE)))
    return True


def _cleanup_legacy(tool: str) -> None:
    """Remove flat command/prompt files from pre-0.1.0 installs."""
    for rel in LEGACY_PATHS.get(tool, []):
        target = WORKSPACE / rel
        if target.is_dir():
            shutil.rmtree(target)
            _warn(f"Removed legacy {rel}")
        elif target.is_file():
            target.unlink()
            _warn(f"Removed legacy {rel}")


def install_tool(tool: str, manifest: dict) -> None:
    upgrade           = _needs_upgrade(tool, manifest)
    installed_version = manifest.get(_version_key(tool))

    if upgrade and installed_version:
        _warn(f"Upgrading skills from v{installed_version} → v{VERSION}")
    elif upgrade:
        _info(f"Installing skills v{VERSION}")

    if upgrade:
        _cleanup_legacy(tool)

    root = TOOL_ROOT[tool]
    changed = False
    for skill in SKILLS:
        for src, rel in _iter_skill_files(skill):
            dest = WORKSPACE / root / skill / rel
            key  = f"{tool}:{skill}/{rel.as_posix()}"
            changed = install_file(key, src, dest, manifest, force=upgrade) or changed

    manifest[_version_key(tool)] = VERSION

    if not changed and not upgrade:
        print(f"\n  Already up to date (v{VERSION}).")


# ── Update ────────────────────────────────────────────────────────────────────
#
# `init` decides whether to rewrite a file by trusting the manifest. `update`
# trusts nothing: it hashes the file actually sitting on disk and compares it to
# the bundled source, so it also repairs drift the manifest wouldn't catch — a
# hand-edited SKILL.md, a corrupted or half-written file, a reference someone
# deleted. Only files api-probe owns are touched.

def update_file(key: str, src: Path, dest: Path, manifest: dict) -> bool:
    new_bytes = src.read_bytes()
    checksum  = _sha256(new_bytes)

    # Compare against the real on-disk content, not the manifest.
    if dest.exists() and _sha256(dest.read_bytes()) == checksum:
        manifest[key] = checksum            # keep the manifest honest
        _info(f"up to date  {dest.relative_to(WORKSPACE)}")
        return False

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(new_bytes)
    manifest[key] = checksum
    _ok(f"refreshed   {dest.relative_to(WORKSPACE)}")
    return True


def update_tool(tool: str, manifest: dict) -> bool:
    """Bring every file api-probe owns for this tool back in line with the
    bundled source. Returns True if anything was rewritten."""
    _cleanup_legacy(tool)

    root = TOOL_ROOT[tool]
    source_keys: set[str] = set()
    changed = False
    for skill in SKILLS:
        for src, rel in _iter_skill_files(skill):
            dest = WORKSPACE / root / skill / rel
            key  = f"{tool}:{skill}/{rel.as_posix()}"
            source_keys.add(key)
            changed = update_file(key, src, dest, manifest) or changed

    # Prune files this tool installed in a previous version that no longer exist
    # in the source (e.g. a reference that was renamed or removed upstream).
    for key in [k for k in manifest
                if k.startswith(f"{tool}:") and not k.endswith(":version")
                and k not in source_keys]:
        rel = key.split(":", 1)[1]
        stale = WORKSPACE / root / rel
        if stale.exists():
            stale.unlink()
            _warn(f"Removed stale  {stale.relative_to(WORKSPACE)}")
            _cleanup_empty_dirs(stale.parent)
        del manifest[key]
        changed = True

    manifest[_version_key(tool)] = VERSION
    return changed


def update() -> None:
    _header("api-probe update")

    manifest  = _load_manifest()
    installed = [(t, TOOL_LABEL[t]) for t, _, _ in TOOLS if manifest.get(_version_key(t))]
    if not installed:
        _info("No api-probe skills are installed in this project.")
        _info("Run `api-probe init` first.")
        return

    any_changed = False
    for tool, label in installed:
        print(f"  {BOLD}{label}{RESET}")
        if update_tool(tool, manifest):
            any_changed = True
        print()

    _save_manifest(manifest)

    if not any_changed:
        print(f"  Everything already matches the bundled skills (v{VERSION}).")
    _header("Done")


# ── Destroy ───────────────────────────────────────────────────────────────────

def _cleanup_empty_dirs(start: Path) -> None:
    """Walk up from start toward WORKSPACE, removing each directory only if it
    is empty. Stops at the first non-empty directory and never removes the
    workspace root. This is what keeps sibling skills from other sources safe:
    the shared skills root (.claude/skills, .github/skills) is only removed if
    nothing else lives in it."""
    d = start
    while d != WORKSPACE and d != d.parent:
        try:
            d.rmdir()                                # succeeds only when empty
            _info(f"Removed empty dir  {d.relative_to(WORKSPACE)}")
            d = d.parent
        except OSError:
            break                                    # not empty — stop walking up


def destroy_tool(tool: str, manifest: dict) -> None:
    """Remove ONLY the skill folders api-probe owns, then clean up directories
    that became empty as a result. A shared skills root holding other skills is
    left untouched."""
    root = TOOL_ROOT[tool]
    for skill in SKILLS:
        skill_dir = WORKSPACE / root / skill
        if skill_dir.exists():
            shutil.rmtree(skill_dir)
            _ok(f"Removed  {skill_dir.relative_to(WORKSPACE)}")
        # Try to tidy the (possibly now-empty) shared root — no-op if other
        # skills remain inside it.
        _cleanup_empty_dirs(WORKSPACE / root)

    for key in [k for k in manifest if k.startswith(f"{tool}:")]:
        del manifest[key]


def destroy() -> None:
    _header("api-probe destroy")

    manifest = _load_manifest()

    installed = [(t, TOOL_LABEL[t]) for t, _, _ in TOOLS if manifest.get(_version_key(t))]
    if not installed:
        _info("No api-probe skills are installed in this project.")
        return

    print("  The following will be removed:\n")
    for tool, label in installed:
        print(f"  {BOLD}{label}{RESET}")
        for skill in SKILLS:
            skill_dir = WORKSPACE / TOOL_ROOT[tool] / skill
            if skill_dir.exists():
                print(f"    • {skill_dir.relative_to(WORKSPACE)}/")
    print()

    confirm = _select("Remove these skill folders?", [
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

    if cmd == "update":
        update()
        return

    _header("api-probe skill installer")

    project_type = detect_project()
    _ok(f"Project detected: {BOLD}{project_type}{RESET}")

    selected = _select(
        "Which AI tool would you like to configure?",
        [(key, label) for key, label, _ in TOOLS],
    )

    manifest = _load_manifest()
    print(f"  Installing ...\n")
    install_tool(selected, manifest)

    _save_manifest(manifest)
    _header("Done")


if __name__ == "__main__":
    main()
