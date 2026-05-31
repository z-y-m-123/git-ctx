#!/usr/bin/env python3
"""
git-ctx — Version control for AI context rules.

Track changes to your .ai-rules.json like Git.
"""

import argparse
import difflib
import json
import os
import re
import shutil
import sys
from datetime import datetime

# ═══════════════════════════════════════════════════════════════
#  Constants
# ═══════════════════════════════════════════════════════════════

RULES_FILE = ".ai-rules.json"
REPO_DIR = ".git-ctx"
INDEX_FILE = "index.json"

DEFAULT_RULES = {
    "project": "my-project",
    "techStack": [],
    "codingStandards": [],
    "architectureDecisions": [],
}

EXPORT_FORMATS = {
    "cursor":   ".cursorrules",
    "windsurf": ".windsurfrules",
    "claude":   "CLAUDE.md",
    "copilot":  ".github/copilot-instructions.md",
}

# ── Templates ──────────────────────────────────────────────────

TEMPLATES = {
    "web-backend": {
        "project": "my-api",
        "description": "REST API backend service",
        "techStack": ["Python 3.12", "FastAPI", "PostgreSQL", "Redis"],
        "codingStandards": [
            "Type hints on all function signatures",
            "Pydantic v2 for request/response schemas",
            "Repository pattern for database access",
            "One route per file",
        ],
        "architectureDecisions": [
            "Async database sessions via dependency injection",
            "Service layer between routes and repositories",
            "Structured JSON logging via structlog",
            "Config via pydantic-settings from environment",
        ],
        "testingStrategy": {
            "framework": "pytest + pytest-asyncio",
            "conventions": ["One test file per route", "httpx.AsyncClient for integration tests"],
        },
    },
    "web-frontend": {
        "project": "my-frontend",
        "description": "Web frontend application",
        "techStack": ["TypeScript 5", "React 19", "Tailwind CSS", "Vite"],
        "codingStandards": [
            "ESLint + Prettier for formatting",
            "One component per file (named export preferred)",
            "Custom hooks for shared logic",
            "TypeScript strict mode enabled",
        ],
        "architectureDecisions": [
            "State management via React Context + useReducer",
            "API calls centralized in services/ directory",
            "File-based routing with React Router",
            "Component-driven design with Storybook",
        ],
        "testingStrategy": {
            "framework": "Vitest + React Testing Library",
            "conventions": ["Component tests alongside source", "MSW for API mocking"],
        },
    },
    "cli-tool": {
        "project": "my-cli",
        "description": "Command-line interface tool",
        "techStack": ["Python 3.12", "Click / Typer", "Rich (terminal output)"],
        "codingStandards": [
            "Argparse or Click for argument parsing",
            "Rich console for colored output and tables",
            "Exit codes: 0=success, 1=error, 2=usage",
            "Single-file deployable (zero external deps preferred)",
        ],
        "architectureDecisions": [
            "Subcommand structure via argparse subparsers",
            "All I/O through stdlib (no framework lock-in)",
            "Config via environment + config file cascade",
        ],
    },
    "library": {
        "project": "my-lib",
        "description": "Reusable library / SDK package",
        "techStack": ["Python 3.10+", "setuptools / hatch"],
        "codingStandards": [
            "Public API fully typed with docstrings (Google style)",
            "Backward compatibility: no breaking changes in minor versions",
            "80%+ test coverage required",
            "Single import entry point: from mylib import ...",
        ],
        "architectureDecisions": [
            "Minimal dependencies — stdlib where possible",
            "Semantic versioning (semver)",
            "CHANGELOG.md maintained for every release",
        ],
    },
    "data-science": {
        "project": "my-ml-project",
        "description": "Data science / machine learning project",
        "techStack": ["Python 3.12", "pandas", "scikit-learn", "Jupyter", "MLflow"],
        "codingStandards": [
            "Notebooks committed as .ipynb (not .py exports)",
            "Parameterize all magic numbers via config",
            "make_dataset(), build_model(), evaluate() entry points",
        ],
        "architectureDecisions": [
            "Data pipeline: raw/ → interim/ → processed/ → results/",
            "Experiment tracking via MLflow",
            "Models versioned and reproducible via DVC or equivalent",
        ],
    },
    "minimal": {
        "project": "my-project",
        "techStack": [],
        "codingStandards": [],
        "architectureDecisions": [],
    },
}

# Files commonly found in project roots for auto-detection
AUTO_DETECT = {
    "pyproject.toml": "Python",
    "setup.py": "Python",
    "requirements.txt": "Python",
    "Pipfile": "Python",
    "package.json": "Node.js",
    "tsconfig.json": "TypeScript",
    "next.config.js": "Next.js",
    "vite.config.ts": "Vite",
    "Cargo.toml": "Rust",
    "go.mod": "Go",
    "Gemfile": "Ruby",
    "CMakeLists.txt": "C/C++",
    "Makefile": "C/C++",
    "build.gradle": "Java/Kotlin",
    "pom.xml": "Java",
    "composer.json": "PHP",
    "Dockerfile": "Docker",
    ".github/": "CI/CD (GitHub Actions)",
}

# ═══════════════════════════════════════════════════════════════
#  Repository helpers
# ═══════════════════════════════════════════════════════════════

def repo_path(*parts):
    return os.path.join(REPO_DIR, *parts)


def index_path():
    return repo_path(INDEX_FILE)


def now_iso():
    return datetime.now().replace(microsecond=0).isoformat()


def display_time(value):
    return value.replace("T", " ")


def write_default_rules(template=None):
    rules = TEMPLATES.get(template, DEFAULT_RULES) if template else DEFAULT_RULES
    with open(RULES_FILE, "w", encoding="utf-8") as f:
        json.dump(rules, f, indent=2)
        f.write("\n")


def ensure_rules_file(template=None):
    if not os.path.exists(RULES_FILE):
        write_default_rules(template)


def require_repo():
    if not os.path.isdir(REPO_DIR) or not os.path.exists(index_path()):
        print("Not a git-ctx repository. Run 'git-ctx init' first.", file=sys.stderr)
        sys.exit(1)


def read_lines(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.readlines()


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ═══════════════════════════════════════════════════════════════
#  Index management
# ═══════════════════════════════════════════════════════════════

def empty_index():
    return {
        "versions": [],
        "current": None,
        "tags": {},
        "stars": [],
        "branches": {"main": {"current": None}},
        "currentBranch": "main",
        "reviews": {},
    }


def _upgrade_index(data):
    """Upgrade older index formats to current schema."""
    if "tags" not in data:
        data["tags"] = {}
    if "stars" not in data:
        data["stars"] = []
    if "branches" not in data:
        # Migrate: create "main" branch from top-level current
        main_current = data.get("current")
        data["branches"] = {"main": {"current": main_current}}
    if "currentBranch" not in data:
        data["currentBranch"] = "main"
    if "reviews" not in data:
        data["reviews"] = {}
    # Ensure all existing versions have a branch field
    for v in data.get("versions", []):
        if "branch" not in v:
            v["branch"] = "main"
    return data


def load_index():
    if not os.path.exists(index_path()):
        return empty_index()
    with open(index_path(), "r", encoding="utf-8") as f:
        data = json.load(f)
    return _upgrade_index(data)


def save_index(index):
    with open(index_path(), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)
        f.write("\n")


# ═══════════════════════════════════════════════════════════════
#  Version helpers
# ═══════════════════════════════════════════════════════════════

def next_version_id(index):
    ids = [v["id"] for v in index["versions"]]
    return max(ids, default=0) + 1


def find_version(index, version_id):
    for v in index["versions"]:
        if v["id"] == version_id:
            return v
    return None


def version_file(index, version_id):
    v = find_version(index, version_id)
    if v is None:
        print(f"Version {version_id} not found.", file=sys.stderr)
        sys.exit(1)
    return repo_path(v["file"])


def copy_rules_to_version(version_id):
    filename = f"{version_id}.json"
    shutil.copyfile(RULES_FILE, repo_path(filename))
    return filename


def resolve_version(index, identifier):
    """Resolve a version number or tag name to a version dict.

    Accepts:
      - int / str digits: version ID
      - str: tag name → version ID → version dict

    Returns the version dict, or None if not found.
    """
    # Try as version ID first (int or numeric string)
    if isinstance(identifier, int):
        v = find_version(index, identifier)
        if v is not None:
            return v
    elif isinstance(identifier, str) and identifier.isdigit():
        v = find_version(index, int(identifier))
        if v is not None:
            return v

    # Try as tag name
    version_id = index.get("tags", {}).get(identifier)
    if version_id is not None:
        return find_version(index, version_id)
    return None


def get_current_branch(index):
    return index.get("currentBranch", "main")


def get_branch_current(index, branch_name=None):
    if branch_name is None:
        branch_name = get_current_branch(index)
    branch = index.get("branches", {}).get(branch_name)
    if branch is None:
        return None
    return branch.get("current")


def set_branch_current(index, version_id, branch_name=None):
    if branch_name is None:
        branch_name = get_current_branch(index)
    if branch_name not in index.setdefault("branches", {}):
        index["branches"][branch_name] = {"current": None}
    index["branches"][branch_name]["current"] = version_id


def create_version(index, message):
    ensure_rules_file()
    version_id = next_version_id(index)
    filename = copy_rules_to_version(version_id)
    branch = get_current_branch(index)
    index["versions"].append({
        "id": version_id,
        "timestamp": now_iso(),
        "message": message,
        "file": filename,
        "branch": branch,
    })
    index["current"] = version_id
    set_branch_current(index, version_id, branch)
    save_index(index)
    return version_id


def rules_content_equals(from_path, to_path):
    """Check if two rules files have identical content."""
    if not os.path.exists(from_path) or not os.path.exists(to_path):
        return False
    return read_lines(from_path) == read_lines(to_path)


# ═══════════════════════════════════════════════════════════════
#  Backup helpers
# ═══════════════════════════════════════════════════════════════

def backup_current_rules():
    """Backup current .ai-rules.json if it exists, return backup path or None."""
    if not os.path.exists(RULES_FILE):
        return None
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_name = f"backup-{timestamp}.json"
    backup_path = repo_path(backup_name)
    shutil.copyfile(RULES_FILE, backup_path)
    return backup_path


# ═══════════════════════════════════════════════════════════════
#  Diff helpers
# ═══════════════════════════════════════════════════════════════

def print_diff(from_path, to_path, from_label, to_label):
    from_lines = read_lines(from_path)
    to_lines = read_lines(to_path)
    diff = difflib.unified_diff(
        from_lines, to_lines, fromfile=from_label, tofile=to_label, lineterm="",
    )
    output = list(diff)
    if not output:
        print("No differences.")
        return
    for line in output:
        print(line)


# ═══════════════════════════════════════════════════════════════
#  Export helpers
# ═══════════════════════════════════════════════════════════════

def _fmt_title(key):
    """camelCase or PascalCase → Title Case.

    Handles acronyms better by not splitting runs of uppercase letters.
    e.g. 'apiConventions' → 'API Conventions'
         'codingStandards' → 'Coding Standards'
         'CSSFramework' → 'CSS Framework'
    """
    # Insert space before capital letters that are followed by lowercase,
    # or after a run of capitals that is followed by a capital+lowercase
    with_spaces = re.sub(r'(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])', ' ', key)
    return with_spaces.strip().title()


def _render_value(value, indent=""):
    """Render a JSON value (str, list, dict, number) to Markdown lines."""
    lines = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                for k, v in item.items():
                    title = _fmt_title(k)
                    lines.append(f"{indent}- **{title}:** {v}")
            elif isinstance(item, str):
                lines.append(f"{indent}- {item}")
            else:
                lines.append(f"{indent}- {item}")
    elif isinstance(value, dict):
        for k, v in value.items():
            title = _fmt_title(k)
            if isinstance(v, list):
                lines.append(f"{indent}- **{title}:**")
                for item in v:
                    lines.append(f"{indent}  - {item}")
            elif isinstance(v, (int, float)):
                lines.append(f"{indent}- **{title}:** {v}")
            elif isinstance(v, str):
                lines.append(f"{indent}- **{title}:** {v}")
            elif v is None:
                lines.append(f"{indent}- **{title}**")
    elif isinstance(value, str):
        lines.append(f"{indent}{value}")
    elif isinstance(value, (int, float)):
        lines.append(f"{indent}{value}")
    return lines


def convert_rules_to_text(rules):
    """Convert .ai-rules.json dict to readable text for AI context files."""
    parts = []

    project = rules.get("project", "")
    if project:
        parts.append(f"# {project}\n")

    if rules.get("description"):
        parts.append(f"{rules['description']}\n")

    # Preamble for AI assistants
    tech = rules.get("techStack", [])
    if tech:
        parts.append("You are working on a project with the following tech stack:")
        for t in tech:
            parts.append(f"- {t}")
        parts.append("")

    # Remaining sections
    for key, value in rules.items():
        if key in ("project", "description", "techStack"):
            continue
        if not value and value != 0:
            continue

        title = _fmt_title(key)
        parts.append(f"## {title}\n")
        for line in _render_value(value):
            parts.append(line)
        parts.append("")

    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════
#  Validation
# ═══════════════════════════════════════════════════════════════

RECOMMENDED_FIELDS = [
    "project",
    "description",
    "techStack",
    "codingStandards",
    "architectureDecisions",
    "testingStrategy",
]


def validate_rules(rules):
    """Validate .ai-rules.json content. Returns list of (level, message) tuples."""
    issues = []

    # Check for recommended fields
    for field in RECOMMENDED_FIELDS:
        if field not in rules:
            issues.append(("warning", f"Missing recommended field: '{field}'"))

    # Check project name
    project = rules.get("project", "")
    if project == "my-project" or project == "":
        issues.append(("info", "Project name is still the default. Consider setting it."))

    # Check techStack
    tech = rules.get("techStack", [])
    if isinstance(tech, list) and len(tech) == 0:
        issues.append(("info", "techStack is empty. Add your technologies for better AI guidance."))

    # Check codingStandards
    standards = rules.get("codingStandards", [])
    if isinstance(standards, list) and len(standards) == 0:
        issues.append(("info", "codingStandards is empty. Add conventions for consistent AI output."))

    # Check for unknown top-level keys that might be typos
    known_keys = {
        "project", "description", "techStack", "codingStandards",
        "architectureDecisions", "testingStrategy", "apiConventions",
        "deployNotes", "securityGuidelines", "documentationStandards",
        "performanceGuidelines", "dependencyManagement",
    }
    for key in rules:
        if key not in known_keys and not key[0].isupper():
            pass  # Allow custom fields, just don't flag them

    # Check that list fields are actually lists
    list_fields = ["techStack", "codingStandards", "architectureDecisions"]
    for field in list_fields:
        if field in rules and not isinstance(rules[field], list):
            issues.append(("error", f"'{field}' should be a list, got {type(rules[field]).__name__}"))

    return issues


# ═══════════════════════════════════════════════════════════════
#  Auto-detect
# ═══════════════════════════════════════════════════════════════

def auto_detect_project():
    """Detect project type and technologies from files in the current directory."""
    detected = {"techStack": [], "type": "unknown"}

    for filename, tech in AUTO_DETECT.items():
        path = filename.rstrip("/")
        if os.path.exists(path) or (filename.endswith("/") and os.path.isdir(path)):
            if tech not in detected["techStack"]:
                detected["techStack"].append(tech)

    # Determine best template match
    techs = set(detected["techStack"])
    if "Python" in techs or "FastAPI" in techs:
        if "Docker" in techs or "Flask" in techs or "FastAPI" in techs:
            detected["type"] = "web-backend"
        else:
            detected["type"] = "library"
    elif "TypeScript" in techs or "Node.js" in techs or "Next.js" in techs or "Vite" in techs:
        detected["type"] = "web-frontend"
    elif "Rust" in techs:
        detected["type"] = "cli-tool"
    elif "Go" in techs:
        detected["type"] = "cli-tool"

    return detected


# ═══════════════════════════════════════════════════════════════
#  Commands
# ═══════════════════════════════════════════════════════════════

# ── init ───────────────────────────────────────────────────────

def cmd_init(args):
    os.makedirs(REPO_DIR, exist_ok=True)

    if args.auto:
        detected = auto_detect_project()
        template = args.template or detected.get("type", "minimal")
        ensure_rules_file(template)
        # If auto-detected, enhance the template with detected tech
        if detected["techStack"]:
            with open(RULES_FILE, "r", encoding="utf-8") as f:
                rules = json.load(f)
            existing = set(rules.get("techStack", []))
            # Avoid adding generic tech if a more specific version already exists
            existing_prefixes = {x.lower().split()[0] for x in existing}
            for t in detected["techStack"]:
                t_prefix = t.lower().split()[0]
                if t_prefix not in existing_prefixes and t not in existing:
                    rules.setdefault("techStack", []).append(t)
            with open(RULES_FILE, "w", encoding="utf-8") as f:
                json.dump(rules, f, indent=2)
                f.write("\n")
        print(f"Auto-detected project type: {detected['type']}")
        print(f"Detected technologies: {', '.join(detected['techStack']) or 'none'}")
    elif args.template:
        ensure_rules_file(args.template)
        print(f"Initialized with template: {args.template}")
    else:
        ensure_rules_file()

    if not os.path.exists(index_path()):
        index = empty_index()
        create_version(index, "init")

    print("Initialized empty context repository in .git-ctx/")


# ── commit ─────────────────────────────────────────────────────

def cmd_commit(args):
    require_repo()
    index = load_index()

    # Check for duplicate content
    current_id = index.get("current")
    if current_id is not None:
        current_v = find_version(index, current_id)
        if current_v is not None:
            snapshot_path = repo_path(current_v["file"])
            if os.path.exists(RULES_FILE) and os.path.exists(snapshot_path):
                if rules_content_equals(RULES_FILE, snapshot_path):
                    print(
                        "Nothing to commit. Working rules match the current version "
                        f"({current_id}).",
                        file=sys.stderr,
                    )
                    sys.exit(1)

    version_id = create_version(index, args.message)
    branch = get_current_branch(index)
    print(f"Committed as version {version_id} [{branch}]: {args.message}")


# ── log ────────────────────────────────────────────────────────

def cmd_log(args):
    require_repo()
    index = load_index()

    stars = set(index.get("stars", []))
    current_branch = get_current_branch(index)

    # Build reverse tag lookup: version_id → [tag_names]
    tag_names = {}
    for name, vid in index.get("tags", {}).items():
        tag_names.setdefault(vid, []).append(name)

    versions = index["versions"]
    if args.branch:
        versions = [v for v in versions if v.get("branch") == args.branch]

    if args.n is not None:
        versions = versions[-args.n:]

    for v in versions:
        vid = v["id"]
        tags = tag_names.get(vid, [])
        star_mark = " [*]" if vid in stars else ""
        tag_str = f"  [{', '.join(tags)}]" if tags else ""
        branch_mark = f"  [{v.get('branch', 'main')}]" if not args.branch else ""
        print(
            f"version {vid}: "
            f"{display_time(v['timestamp'])} - {v['message']}"
            f"{tag_str}{branch_mark}{star_mark}"
        )


# ── show ───────────────────────────────────────────────────────

def cmd_show(args):
    require_repo()
    index = load_index()

    v = resolve_version(index, args.version)
    if v is None:
        print(f"Version '{args.version}' not found.", file=sys.stderr)
        sys.exit(1)

    path = repo_path(v["file"])
    if not os.path.exists(path):
        print(f"Snapshot file missing: {v['file']}", file=sys.stderr)
        sys.exit(1)

    print(f"version {v['id']}: {v['timestamp']} - {v['message']}")
    print(f"branch: {v.get('branch', 'main')}")
    print("-" * 40)

    if args.json:
        with open(path, "r", encoding="utf-8") as f:
            print(f.read())
    else:
        rules = read_json(path)
        text = convert_rules_to_text(rules)
        print(text)


# ── diff ───────────────────────────────────────────────────────

def cmd_diff(args):
    require_repo()
    index = load_index()

    if args.version1 is None and args.version2 is None:
        # Working file vs HEAD
        if not os.path.exists(RULES_FILE):
            print(f"{RULES_FILE} not found. Nothing to diff.", file=sys.stderr)
            sys.exit(1)
        current_id = index.get("current")
        if current_id is None:
            print("No versions to compare.", file=sys.stderr)
            sys.exit(1)
        latest = version_file(index, current_id)
        print_diff(latest, RULES_FILE, f"version {current_id}", RULES_FILE)
        return

    if args.version2 is None:
        # Working file vs specified version
        if not os.path.exists(RULES_FILE):
            print(f"{RULES_FILE} not found. Nothing to diff.", file=sys.stderr)
            sys.exit(1)
        v1 = resolve_version(index, args.version1)
        if v1 is None:
            print(f"Version '{args.version1}' not found.", file=sys.stderr)
            sys.exit(1)
        left = version_file(index, v1["id"])
        label = args.version1 if isinstance(args.version1, str) else str(v1["id"])
        print_diff(left, RULES_FILE, f"version {v1['id']}", RULES_FILE)
        return

    # Two specific versions
    v1 = resolve_version(index, args.version1)
    v2 = resolve_version(index, args.version2)
    if v1 is None:
        print(f"Version '{args.version1}' not found.", file=sys.stderr)
        sys.exit(1)
    if v2 is None:
        print(f"Version '{args.version2}' not found.", file=sys.stderr)
        sys.exit(1)

    left = version_file(index, v1["id"])
    right = version_file(index, v2["id"])
    print_diff(left, right, f"version {v1['id']}", f"version {v2['id']}")


# ── checkout ───────────────────────────────────────────────────

def cmd_checkout(args):
    require_repo()
    index = load_index()

    # Use unified resolve_version
    if args.tag:
        identifier = args.tag
    else:
        identifier = args.version

    v = resolve_version(index, identifier)
    if v is None:
        print(f"Version '{identifier}' not found.", file=sys.stderr)
        sys.exit(1)

    label = args.tag if args.tag else str(v["id"])

    if not args.force:
        answer = input(f"Overwrite {RULES_FILE} with version {label}? (y/N) ")
        if answer.strip().lower() not in ("y", "yes"):
            print("Checkout canceled.")
            return

    backup_path = backup_current_rules()
    shutil.copyfile(repo_path(v["file"]), RULES_FILE)
    index["current"] = v["id"]
    set_branch_current(index, v["id"])
    save_index(index)

    if backup_path:
        print(f"Backup saved to {backup_path}")
    print(f"Switched to version {label}")


# ── status ─────────────────────────────────────────────────────

def cmd_status(args):
    require_repo()
    index = load_index()
    current_id = index.get("current")
    if current_id is None:
        print("No versions committed yet.", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(RULES_FILE):
        print(f"{RULES_FILE} is missing. Run 'git-ctx checkout {current_id}' to restore it.")
        return

    snapshot_path = version_file(index, current_id)

    if rules_content_equals(snapshot_path, RULES_FILE):
        branch = get_current_branch(index)
        print(f"Nothing to commit. Working rules match version {current_id} [{branch}].")
    else:
        print(f"Working rules differ from version {current_id}.")
        print(
            "Run 'git-ctx diff' to see changes, "
            "or 'git-ctx commit -m <message>' to save."
        )


# ── tag ────────────────────────────────────────────────────────

def cmd_tag(args):
    require_repo()
    index = load_index()

    if args.action == "list":
        if not index["tags"]:
            print("No tags.")
            return
        width = max(len(name) for name in index["tags"])
        for name, version_id in sorted(index["tags"].items()):
            v = find_version(index, version_id)
            msg = v["message"] if v else "???"
            print(f"{name:<{width}}  -> version {version_id}  ({msg})")
        return

    if args.action == "delete":
        if args.name not in index["tags"]:
            print(f"Tag '{args.name}' not found.", file=sys.stderr)
            sys.exit(1)
        del index["tags"][args.name]
        save_index(index)
        print(f"Deleted tag '{args.name}'")
        return

    # action == "add"
    v = resolve_version(index, args.version)
    if v is None:
        print(f"Version '{args.version}' not found.", file=sys.stderr)
        sys.exit(1)

    if args.name in index["tags"]:
        old_v = index["tags"][args.name]
        print(f"Tag '{args.name}' moved from version {old_v} to {v['id']}.")
    index["tags"][args.name] = v["id"]
    save_index(index)
    print(f"Tagged version {v['id']} as '{args.name}'")


# ── star / unstar / stars ──────────────────────────────────────

def cmd_star(args):
    require_repo()
    index = load_index()

    v = resolve_version(index, args.version)
    if v is None:
        print(f"Version '{args.version}' not found.", file=sys.stderr)
        sys.exit(1)

    if v["id"] in index.get("stars", []):
        print(f"Version {v['id']} is already starred.")
        return

    index.setdefault("stars", []).append(v["id"])
    save_index(index)
    print(f"[*] Starred version {v['id']} ({v['message']})")


def cmd_unstar(args):
    require_repo()
    index = load_index()

    v = resolve_version(index, args.version)
    if v is None:
        print(f"Version '{args.version}' not found.", file=sys.stderr)
        sys.exit(1)

    stars = index.get("stars", [])
    if v["id"] not in stars:
        print(f"Version {v['id']} is not starred.", file=sys.stderr)
        sys.exit(1)

    stars.remove(v["id"])
    save_index(index)
    print(f"Removed star from version {v['id']}")


def cmd_stars(args):
    require_repo()
    index = load_index()

    stars = index.get("stars", [])
    if not stars:
        print("No starred versions.")
        return

    print("Starred versions:")
    for vid in stars:
        v = find_version(index, vid)
        if v:
            tags = [n for n, tid in index.get("tags", {}).items() if tid == vid]
            tag_str = f"  [{', '.join(tags)}]" if tags else ""
            print(f"  [*] version {vid}: {display_time(v['timestamp'])} - {v['message']}{tag_str}")
        else:
            print(f"  [*] version {vid}: (missing)")


# ── branch ─────────────────────────────────────────────────────

def cmd_branch(args):
    require_repo()
    index = load_index()

    if args.name is None:
        # List branches
        current = get_current_branch(index)
        for name, info in sorted(index.get("branches", {}).items()):
            marker = "*" if name == current else " "
            cur = info.get("current")
            cur_str = f"(version {cur})" if cur else "(empty)"
            print(f"{marker} {name} {cur_str}")
        return

    # Create a new branch
    name = args.name
    if name in index.get("branches", {}):
        print(f"Branch '{name}' already exists.", file=sys.stderr)
        sys.exit(1)

    # New branch starts at current version
    cur = index.get("current")
    index.setdefault("branches", {})[name] = {"current": cur}
    save_index(index)

    if cur:
        print(f"Created branch '{name}' at version {cur}.")
    else:
        print(f"Created branch '{name}' (no versions yet).")


# ── switch ─────────────────────────────────────────────────────

def cmd_switch(args):
    require_repo()
    index = load_index()

    name = args.branch
    if name not in index.get("branches", {}):
        print(f"Branch '{name}' not found. Use 'git-ctx branch {name}' to create it.",
              file=sys.stderr)
        sys.exit(1)

    # Check for uncommitted changes
    current_id = index.get("current")
    if current_id is not None and os.path.exists(RULES_FILE):
        current_v = find_version(index, current_id)
        if current_v is not None:
            snapshot_path = repo_path(current_v["file"])
            if os.path.exists(snapshot_path):
                if not rules_content_equals(RULES_FILE, snapshot_path):
                    print(
                        "Warning: You have uncommitted changes. "
                        "Commit them first or they will be lost on switch.",
                        file=sys.stderr,
                    )
                    if not args.force:
                        answer = input("Switch anyway? (y/N) ")
                        if answer.strip().lower() not in ("y", "yes"):
                            print("Switch canceled.")
                            return

    old_branch = get_current_branch(index)
    index["currentBranch"] = name
    new_current = get_branch_current(index, name)
    index["current"] = new_current

    # Restore the new branch's current version to working file
    if new_current is not None:
        v = find_version(index, new_current)
        if v is not None:
            backup_path = backup_current_rules()
            shutil.copyfile(repo_path(v["file"]), RULES_FILE)
            if backup_path:
                print(f"Backup saved to {backup_path}")
    save_index(index)

    print(f"Switched from '{old_branch}' to '{name}'")
    if new_current:
        print(f"HEAD is now version {new_current}")
    else:
        print("Branch is empty. Make your first commit.")


# ── merge ──────────────────────────────────────────────────────

def cmd_merge(args):
    require_repo()
    index = load_index()

    other = args.branch
    current_br = get_current_branch(index)

    if other not in index.get("branches", {}):
        print(f"Branch '{other}' not found.", file=sys.stderr)
        sys.exit(1)
    if other == current_br:
        print(f"Cannot merge '{other}' into itself.", file=sys.stderr)
        sys.exit(1)

    other_current = get_branch_current(index, other)
    if other_current is None:
        print(f"Branch '{other}' has no versions to merge.", file=sys.stderr)
        sys.exit(1)

    our_current = get_branch_current(index, current_br)

    # Simple fast-forward check
    if our_current is None:
        # We're empty, just adopt their current
        set_branch_current(index, other_current, current_br)
        index["current"] = other_current
        save_index(index)
        print(f"Fast-forward merged '{other}' into '{current_br}' at version {other_current}")
        return

    if our_current == other_current:
        print(f"Already up to date. '{current_br}' and '{other}' are at the same version.")
        return

    # Check for content conflict between the two branch heads
    our_v = find_version(index, our_current)
    other_v = find_version(index, other_current)

    if our_v and other_v:
        our_path = repo_path(our_v["file"])
        other_path = repo_path(other_v["file"])
        if os.path.exists(our_path) and os.path.exists(other_path):
            if rules_content_equals(our_path, other_path):
                # Same content, just update pointer
                set_branch_current(index, other_current, current_br)
                index["current"] = other_current
                save_index(index)
                print(f"Merged '{other}' into '{current_br}' at version {other_current}")
                return

        # Show diff
        print(f"Merging '{other}' (version {other_current}) into '{current_br}' "
              f"(version {our_current})...")
        print()
        print_diff(our_path, other_path, f"{current_br} (v{our_current})",
                   f"{other} (v{other_current})")
        print()

    if not args.force:
        answer = input(
            f"Accept changes from '{other}' and advance '{current_br}' "
            f"to version {other_current}? (y/N) "
        )
        if answer.strip().lower() not in ("y", "yes"):
            print("Merge canceled.")
            return

    # Advance current branch to other's version
    backup_path = backup_current_rules()
    if other_v:
        shutil.copyfile(repo_path(other_v["file"]), RULES_FILE)
        if backup_path:
            print(f"Backup saved to {backup_path}")

    set_branch_current(index, other_current, current_br)
    index["current"] = other_current
    save_index(index)
    print(f"Merged '{other}' into '{current_br}' at version {other_current}")


# ── delete ─────────────────────────────────────────────────────

def cmd_delete(args):
    require_repo()
    index = load_index()

    v = resolve_version(index, args.version)
    if v is None:
        print(f"Version '{args.version}' not found.", file=sys.stderr)
        sys.exit(1)

    vid = v["id"]

    # Check if it's the only version
    if len(index["versions"]) <= 1:
        print("Cannot delete the only version.", file=sys.stderr)
        sys.exit(1)

    if not args.force:
        answer = input(f"Delete version {vid} ({v['message']})? This cannot be undone. (y/N) ")
        if answer.strip().lower() not in ("y", "yes"):
            print("Delete canceled.")
            return

    # Remove from versions list
    index["versions"] = [x for x in index["versions"] if x["id"] != vid]

    # Remove from tags
    removed_tags = [n for n, tid in index.get("tags", {}).items() if tid == vid]
    for tag in removed_tags:
        del index["tags"][tag]

    # Remove from stars
    stars = index.get("stars", [])
    if vid in stars:
        stars.remove(vid)

    # Update branch pointers
    for br_name, br_info in index.get("branches", {}).items():
        if br_info.get("current") == vid:
            # Find the latest version for this branch
            branch_versions = [
                x["id"] for x in index["versions"]
                if x.get("branch") == br_name
            ]
            br_info["current"] = max(branch_versions) if branch_versions else None

    # If current points to deleted version, update
    if index["current"] == vid:
        latest = max((x["id"] for x in index["versions"]), default=None)
        index["current"] = latest

    # Delete the snapshot file
    snapshot_path = repo_path(v["file"])
    if os.path.exists(snapshot_path):
        os.remove(snapshot_path)

    save_index(index)
    print(f"Deleted version {vid} ({v['message']})")
    if removed_tags:
        print(f"Removed tags: {', '.join(removed_tags)}")


# ── validate ───────────────────────────────────────────────────

def cmd_validate(args):
    require_repo()

    if not os.path.exists(RULES_FILE):
        print(f"{RULES_FILE} not found. Run 'git-ctx init' first.", file=sys.stderr)
        sys.exit(1)

    rules = read_json(RULES_FILE)
    issues = validate_rules(rules)

    if not issues:
        print("[OK] No issues found.")
        return

    error_count = sum(1 for level, _ in issues if level == "error")
    warning_count = sum(1 for level, _ in issues if level == "warning")
    info_count = sum(1 for level, _ in issues if level == "info")

    for level, msg in issues:
        prefix = {"error": "[ERR]", "warning": "[WARN]", "info": "[INFO]"}.get(level, "  ")
        print(f"  {prefix} [{level}] {msg}")

    print()
    summary_parts = []
    if error_count:
        summary_parts.append(f"{error_count} error(s)")
    if warning_count:
        summary_parts.append(f"{warning_count} warning(s)")
    if info_count:
        summary_parts.append(f"{info_count} info(s)")
    print(f"Found {', '.join(summary_parts)}.")

    if error_count > 0:
        sys.exit(1)


# ── export ─────────────────────────────────────────────────────

def cmd_export(args):
    require_repo()
    index = load_index()

    # Determine source: working file or a specific version
    if args.version is not None:
        v = resolve_version(index, args.version)
        if v is None:
            print(f"Version '{args.version}' not found.", file=sys.stderr)
            sys.exit(1)
        source_path = repo_path(v["file"])
        source_label = f"version {v['id']}"
        if not os.path.exists(source_path):
            print(f"Snapshot file missing: {v['file']}", file=sys.stderr)
            sys.exit(1)
    else:
        if not os.path.exists(RULES_FILE):
            print(f"{RULES_FILE} not found.", file=sys.stderr)
            sys.exit(1)
        source_path = RULES_FILE
        source_label = RULES_FILE

    rules = read_json(source_path)
    text = convert_rules_to_text(rules)

    if args.stdout:
        print(text)
        return

    formats = list(EXPORT_FORMATS) if args.format == "all" else [args.format]
    written = []
    for fmt in formats:
        filename = EXPORT_FORMATS[fmt]
        dirname = os.path.dirname(filename)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(text)
            f.write("\n")
        written.append(filename)

    print(f"Exported {source_label} -> {', '.join(written)}")


# ── wizard ─────────────────────────────────────────────────────

def cmd_wizard(args):
    """Interactive wizard to build/update .ai-rules.json."""
    print("+====================================+")
    print("|   git-ctx Interactive Setup Wizard |")
    print("+====================================+")
    print()
    print("Let's build your .ai-rules.json step by step.")
    print("(Press Enter to skip optional fields)")
    print()

    # Load existing rules if any
    if os.path.exists(RULES_FILE):
        rules = read_json(RULES_FILE)
        print(f"Editing existing {RULES_FILE}")
    else:
        rules = {"project": "my-project", "techStack": [],
                  "codingStandards": [], "architectureDecisions": []}
        print("Creating new .ai-rules.json")

    print()

    # 1. Project name
    current = rules.get("project", "")
    prompt = f"Project name" + (f" [{current}]" if current else "")
    val = input(f"{prompt}: ").strip()
    if val:
        rules["project"] = val

    # 2. Description
    current = rules.get("description", "")
    prompt = f"Short description" + (f" [{current}]" if current else "")
    val = input(f"{prompt}: ").strip()
    if val:
        rules["description"] = val

    # 3. Tech stack
    print()
    print("Tech stack (enter one technology per line, blank to finish):")
    current = rules.get("techStack", [])
    if current:
        print(f"  Current: {', '.join(current)}")
        val = input("  Replace? (y/N) ").strip().lower()
        if val in ("y", "yes"):
            current = []
    else:
        current = []
    while True:
        val = input("  > ").strip()
        if not val:
            break
        current.append(val)
    if current:
        rules["techStack"] = current

    # 4. Coding standards
    print()
    print("Coding standards (enter one per line, blank to finish):")
    current = rules.get("codingStandards", [])
    if current:
        print(f"  Current:")
        for s in current:
            print(f"    - {s}")
        val = input("  Replace? (y/N) ").strip().lower()
        if val in ("y", "yes"):
            current = []
    else:
        current = []
    while True:
        val = input("  > ").strip()
        if not val:
            break
        current.append(val)
    if current:
        rules["codingStandards"] = current

    # 5. Architecture decisions
    print()
    print("Architecture decisions (enter one per line, blank to finish):")
    current = rules.get("architectureDecisions", [])
    if current:
        print(f"  Current:")
        for s in current:
            print(f"    - {s}")
        val = input("  Replace? (y/N) ").strip().lower()
        if val in ("y", "yes"):
            current = []
    else:
        current = []
    while True:
        val = input("  > ").strip()
        if not val:
            break
        current.append(val)
    if current:
        rules["architectureDecisions"] = current

    # 6. Testing strategy
    print()
    print("Testing strategy:")
    ts = rules.get("testingStrategy", {})
    framework = input(f"  Test framework [{ts.get('framework', '')}]: ").strip()
    coverage = input(f"  Coverage target % [{ts.get('coverageTarget', '')}]: ").strip()
    conventions = []
    if ts.get("conventions"):
        print(f"  Current conventions:")
        for c in ts["conventions"]:
            print(f"    - {c}")
        val = input("  Replace? (y/N) ").strip().lower()
        if val not in ("y", "yes"):
            conventions = ts["conventions"]

    if not conventions:
        print("  Test conventions (one per line, blank to finish):")
        while True:
            val = input("    > ").strip()
            if not val:
                break
            conventions.append(val)

    new_ts = {}
    if framework:
        new_ts["framework"] = framework
    if coverage:
        try:
            new_ts["coverageTarget"] = int(coverage)
        except ValueError:
            new_ts["coverageTarget"] = coverage
    if conventions:
        new_ts["conventions"] = conventions
    if new_ts:
        rules["testingStrategy"] = new_ts

    # Save
    print()
    with open(RULES_FILE, "w", encoding="utf-8") as f:
        json.dump(rules, f, indent=2)
        f.write("\n")

    print(f"Saved to {RULES_FILE}")
    print()
    print("Next steps:")
    print(f"  git-ctx status          # see what changed")
    print(f"  git-ctx diff            # review the diff")
    print(f"  git-ctx commit -m '...' # save this version")
    print(f"  git-ctx export          # export to AI tool formats")


# ═══════════════════════════════════════════════════════════════
#  CLI Parser
# ═══════════════════════════════════════════════════════════════

def build_parser():
    parser = argparse.ArgumentParser(
        prog="git-ctx",
        description="Version control for AI context rules — "
                    "track changes to your .ai-rules.json like Git.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ── init ──
    p_init = subparsers.add_parser("init", help="Create a new context repository")
    p_init.add_argument(
        "-t", "--template",
        choices=list(TEMPLATES.keys()),
        help="Initialize with a project template",
    )
    p_init.add_argument(
        "--auto", action="store_true",
        help="Auto-detect project type and technologies",
    )
    p_init.set_defaults(func=cmd_init)

    # ── commit ──
    p_commit = subparsers.add_parser("commit", help="Snapshot .ai-rules.json")
    p_commit.add_argument("-m", "--message", required=True, help="Commit message")
    p_commit.set_defaults(func=cmd_commit)

    # ── log ──
    p_log = subparsers.add_parser("log", help="Show version history")
    p_log.add_argument("-n", type=int, help="Show only the last N versions")
    p_log.add_argument("-b", "--branch", help="Show only versions from this branch")
    p_log.set_defaults(func=cmd_log)

    # ── show ──
    p_show = subparsers.add_parser("show", help="Display the content of a version")
    p_show.add_argument(
        "version",
        help="Version ID or tag name to show",
    )
    p_show.add_argument(
        "--json", action="store_true",
        help="Show raw JSON instead of rendered Markdown",
    )
    p_show.set_defaults(func=cmd_show)

    # ── diff ──
    p_diff = subparsers.add_parser("diff", help="Show changes between versions")
    p_diff.add_argument(
        "version1", nargs="?", type=str,
        help="First version (ID or tag); defaults to HEAD",
    )
    p_diff.add_argument(
        "version2", nargs="?", type=str,
        help="Second version (ID or tag); defaults to working file",
    )
    p_diff.set_defaults(func=cmd_diff)

    # ── checkout ──
    p_checkout = subparsers.add_parser("checkout", help="Restore a version")
    checkout_group = p_checkout.add_mutually_exclusive_group(required=True)
    checkout_group.add_argument(
        "version", nargs="?", type=str,
        help="Version ID or tag to restore",
    )
    checkout_group.add_argument(
        "-t", "--tag",
        help="Tag name to restore",
    )
    p_checkout.add_argument(
        "-f", "--force", action="store_true",
        help="Skip confirmation prompt",
    )
    p_checkout.set_defaults(func=cmd_checkout)

    # ── status ──
    p_status = subparsers.add_parser("status", help="Show working rules vs HEAD")
    p_status.set_defaults(func=cmd_status)

    # ── tag ──
    p_tag = subparsers.add_parser("tag", help="Manage version tags")
    tag_sub = p_tag.add_subparsers(dest="action", required=True)

    p_tag_add = tag_sub.add_parser("add", help="Tag a version")
    p_tag_add.add_argument("version", help="Version ID or tag to tag")
    p_tag_add.add_argument("name", help="Tag name")
    p_tag_add.set_defaults(func=cmd_tag)

    p_tag_list = tag_sub.add_parser("list", help="List all tags")
    p_tag_list.set_defaults(func=cmd_tag, action="list")

    p_tag_del = tag_sub.add_parser("delete", help="Delete a tag")
    p_tag_del.add_argument("name", help="Tag name to delete")
    p_tag_del.set_defaults(func=cmd_tag, action="delete")

    # ── star ──
    p_star = subparsers.add_parser("star", help="Star (bookmark) a version")
    p_star.add_argument("version", help="Version ID or tag to star")
    p_star.set_defaults(func=cmd_star)

    # ── unstar ──
    p_unstar = subparsers.add_parser("unstar", help="Remove a star from a version")
    p_unstar.add_argument("version", help="Version ID or tag to unstar")
    p_unstar.set_defaults(func=cmd_unstar)

    # ── stars ──
    p_stars = subparsers.add_parser("stars", help="List starred versions")
    p_stars.set_defaults(func=cmd_stars)

    # ── branch ──
    p_branch = subparsers.add_parser("branch", help="List or create branches")
    p_branch.add_argument("name", nargs="?", help="Branch name to create")
    p_branch.set_defaults(func=cmd_branch)

    # ── switch ──
    p_switch = subparsers.add_parser("switch", help="Switch to a different branch")
    p_switch.add_argument("branch", help="Branch name to switch to")
    p_switch.add_argument(
        "-f", "--force", action="store_true",
        help="Skip uncommitted changes warning",
    )
    p_switch.set_defaults(func=cmd_switch)

    # ── merge ──
    p_merge = subparsers.add_parser("merge", help="Merge another branch into current")
    p_merge.add_argument("branch", help="Branch to merge from")
    p_merge.add_argument(
        "-f", "--force", action="store_true",
        help="Skip confirmation prompt",
    )
    p_merge.set_defaults(func=cmd_merge)

    # ── delete ──
    p_delete = subparsers.add_parser("delete", help="Delete a version")
    p_delete.add_argument("version", help="Version ID or tag to delete")
    p_delete.add_argument(
        "-f", "--force", action="store_true",
        help="Skip confirmation prompt",
    )
    p_delete.set_defaults(func=cmd_delete)

    # ── validate ──
    p_validate = subparsers.add_parser("validate", help="Validate .ai-rules.json")
    p_validate.set_defaults(func=cmd_validate)

    # ── export ──
    p_export = subparsers.add_parser("export", help="Export rules to AI tool formats")
    p_export.add_argument(
        "-f", "--format", default="all",
        choices=["all", "cursor", "windsurf", "claude", "copilot"],
        help="Target format (default: all)",
    )
    p_export.add_argument(
        "-v", "--version",
        help="Export a specific version instead of working file",
    )
    p_export.add_argument(
        "--stdout", action="store_true",
        help="Print to stdout instead of writing files",
    )
    p_export.set_defaults(func=cmd_export)

    # ── wizard ──
    p_wizard = subparsers.add_parser("wizard", help="Interactive setup wizard")
    p_wizard.set_defaults(func=cmd_wizard)

    return parser


# ═══════════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════════

def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        args.func(args)
    except FileNotFoundError as exc:
        print(f"File not found: {exc}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        sys.exit(1)
    except PermissionError as exc:
        print(f"Permission denied: {exc}", file=sys.stderr)
        sys.exit(1)
    except OSError as exc:
        print(f"I/O error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
