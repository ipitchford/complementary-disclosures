#!/usr/bin/env python3
"""Check exact recursive public inventory against MANIFEST.json.

Schema: {"files": [{"path": "paper.tex", "size": 123, "sha256": "..."}, ...]}.
Additional top-level metadata is allowed. MANIFEST.json, any .git subtree and
any __pycache__ subtree are excluded. Symlinks and unsafe paths are rejected.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys


class ManifestError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise ManifestError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def excluded(parts):
    return ".git" in parts or "__pycache__" in parts or parts == ("MANIFEST.json",)


def inventory(root):
    result = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if excluded(relative.parts):
            continue
        require(not path.is_symlink(), "symlink is not a public regular file: " + relative.as_posix())
        if path.is_dir():
            continue
        require(path.is_file(), "nonregular inventory entry: " + relative.as_posix())
        result[relative.as_posix()] = {"size": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    return result


def check(root):
    document = json.loads((root / "MANIFEST.json").read_text(), object_pairs_hook=unique_object)
    require(type(document) is dict and type(document.get("files")) is list, "manifest requires files list")
    expected = {}
    for row in document["files"]:
        require(type(row) is dict and set(row) == {"path", "size", "sha256"}, "invalid manifest row schema")
        name = row["path"]
        require(type(name) is str and name and "\\" not in name, "invalid manifest path")
        path = PurePosixPath(name)
        require(not path.is_absolute() and path.as_posix() == name and all(p not in (".", "..", "") for p in name.split("/")), "unsafe or noncanonical manifest path")
        require(not excluded(path.parts), "excluded path included in manifest")
        require(name not in expected, "duplicate manifest path: " + name)
        require(type(row["size"]) is int and row["size"] >= 0, "invalid manifest size")
        digest = row["sha256"]
        require(type(digest) is str and len(digest) == 64 and all(c in "0123456789abcdef" for c in digest), "invalid SHA256")
        expected[name] = {"size": row["size"], "sha256": digest}
    actual = inventory(root)
    require(set(actual) == set(expected), "inventory mismatch; missing=" + repr(sorted(set(expected)-set(actual))) + "; extra=" + repr(sorted(set(actual)-set(expected))))
    for name in expected:
        require(actual[name] == expected[name], "hash or size mismatch: " + name)
    return len(expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    count = check(args.root.resolve())
    print(json.dumps({"status": "PASS", "files_checked": count, "optimized": sys.flags.optimize}))


if __name__ == "__main__":
    try:
        main()
    except (ManifestError, ValueError, OSError) as error:
        print(type(error).__name__ + ": " + str(error), file=sys.stderr)
        sys.exit(2)
