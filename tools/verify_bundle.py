import plistlib
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

DEFAULT_BUNDLE = Path("dist/Discogs.alfredworkflow")
JUNK_PATTERNS = ("__pycache__", ".DS_Store", ".pyc", ".git")
UUID_PATTERN = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
TOKEN_VARIABLE = "DISCOGS_API_TOKEN"  # noqa: S105
SOURCE_DIR = "src/dgapi"


def _text_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        try:
            path.read_text(encoding="utf-8")
        except ValueError:
            continue
        files.append(path)
    return files


def check_no_local_paths(root: Path) -> list[str]:
    return [
        f"local path in {path.relative_to(root)}"
        for path in _text_files(root)
        if "/Users/" in path.read_text(encoding="utf-8")
    ]


def check_no_token_literals(root: Path) -> list[str]:
    return [
        f"UUID-shaped literal in {path.relative_to(root)}"
        for path in sorted((root / SOURCE_DIR).glob("*.py"))
        if UUID_PATTERN.search(path.read_text(encoding="utf-8"))
    ]


def check_no_junk_files(root: Path) -> list[str]:
    return [
        f"junk file {path.relative_to(root)}"
        for path in sorted(root.rglob("*"))
        if any(pattern in path.name for pattern in JUNK_PATTERNS)
    ]


def check_token_not_baked_in(plist: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if plist.get("variables"):
        failures.append("plist carries workflow-level variables (may hold a token)")
    for entry in plist.get("userconfigurationconfig", []):
        if entry.get("variable") != TOKEN_VARIABLE:
            continue
        if entry.get("config", {}).get("default"):
            failures.append(f"{TOKEN_VARIABLE} ships with a non-empty default")
    return failures


def check_script_references_resolve(plist: dict[str, Any], root: Path) -> list[str]:
    return [
        f"missing script {token} referenced by {obj['uid']}"
        for obj in plist["objects"]
        for token in obj["config"].get("script", "").split()
        if token.endswith(".py") and not (root / token).is_file()
    ]


def check_modules_import(root: Path) -> list[str]:
    modules = sorted(path.stem for path in (root / SOURCE_DIR).glob("*.py"))
    program = "import " + ", ".join(modules)
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", program],
        cwd=root,
        env={
            "PYTHONPATH": SOURCE_DIR,
            "PATH": "/usr/bin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return [f"import failed: {result.stderr.strip().splitlines()[-1]}"]
    return []


def verify(bundle: Path) -> int:
    if not bundle.is_file():
        sys.stderr.write(f"bundle not found: {bundle} (run `make build` first)\n")
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        with zipfile.ZipFile(bundle) as archive:
            archive.extractall(root)

        plist = plistlib.loads((root / "info.plist").read_bytes())

        failures = [
            *check_no_local_paths(root),
            *check_no_token_literals(root),
            *check_no_junk_files(root),
            *check_token_not_baked_in(plist),
            *check_script_references_resolve(plist, root),
            *check_modules_import(root),
        ]

        file_count = sum(1 for path in root.rglob("*") if path.is_file())

    if failures:
        for failure in failures:
            sys.stderr.write(f"FAIL {failure}\n")
        return 1

    size_mb = bundle.stat().st_size / 1024 / 1024
    sys.stdout.write(f"verified {bundle} - {file_count} files, {size_mb:.1f} MB\n")
    return 0


def main(argv: list[str]) -> int:
    bundle = Path(argv[0]) if argv else DEFAULT_BUNDLE
    return verify(bundle)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
