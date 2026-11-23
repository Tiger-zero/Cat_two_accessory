"""Build the versioned Codex marketplace ZIP and its checksum."""

import argparse
import hashlib
import json
import re
import stat
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parent.parent
PLUGIN_NAME = "cat-two-notes"
PLUGIN = Path("plugins") / PLUGIN_NAME
MARKETPLACE = Path(".agents/plugins/marketplace.json")
FILES = (
    "plugin.json",
    "mcp.json",
    ".codex-plugin/plugin.json",
    ".mcp.json",
    "scripts/server.py",
    "scripts/settings.py",
    "scripts/setup_web.py",
    "skills/cat-two-setup/SKILL.md",
    "skills/organize-notes/SKILL.md",
)
ASSET_FIELDS = ("logo", "logoDark", "composerIcon", "composerIconDark")


def read_object(path):
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path.as_posix()}")
    return value


def build(output_dir):
    manifest = read_object(PLUGIN / "plugin.json")
    legacy_manifest = read_object(PLUGIN / ".codex-plugin/plugin.json")
    marketplace = read_object(MARKETPLACE)
    version = manifest.get("version")
    if not isinstance(version, str) or not re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*)){2}", version):
        raise ValueError("The portable manifest must declare a three-part release version")
    for entry in (manifest, legacy_manifest):
        if entry.get("name") != PLUGIN_NAME or entry.get("version") != version:
            raise ValueError("The two plugin manifests must agree on plugin name and version")
    if not any(
        entry.get("name") == PLUGIN_NAME
        and entry.get("source") == {"source": "local", "path": f"./{PLUGIN.as_posix()}"}
        for entry in marketplace["plugins"]
    ):
        raise ValueError("The marketplace must point to the packaged plugin directory")
    for mcp_name in ("mcp.json", ".mcp.json"):
        read_object(PLUGIN / mcp_name)

    files = {Path("README.md"), MARKETPLACE, *(PLUGIN / path for path in FILES)}
    interfaces = (
        manifest["extensions"]["com.openai"]["interface"],
        legacy_manifest["interface"],
    )
    for interface in interfaces:
        for field in ASSET_FIELDS:
            if field in interface:
                asset = Path(interface[field])
                if asset.parts[:1] != ("assets",) or ".." in asset.parts:
                    raise ValueError(f"{field} must refer to a file in the plugin assets directory")
                files.add(PLUGIN / asset)

    archive_root = f"{PLUGIN_NAME}-{version}"
    archive_path = output_dir / f"{archive_root}.zip"
    checksum_path = archive_path.with_suffix(".zip.sha256")
    output_dir.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output_dir) as temporary_dir:
        staged_archive = Path(temporary_dir) / archive_path.name
        with ZipFile(staged_archive, "w") as archive:
            for path in sorted(files, key=Path.as_posix):
                source = ROOT / path
                if not source.is_file() or source.resolve() != source:
                    raise ValueError(f"Expected a regular file at {path.as_posix()}")
                info = ZipInfo(f"{archive_root}/{path.as_posix()}")
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                archive.writestr(info, source.read_bytes(), compress_type=ZIP_DEFLATED, compresslevel=9)
        with ZipFile(staged_archive) as archive:
            if archive.testzip() is not None:
                raise ValueError("The release archive failed its integrity check")

        digest = hashlib.sha256(staged_archive.read_bytes()).hexdigest()
        staged_checksum = Path(temporary_dir) / checksum_path.name
        staged_checksum.write_bytes(f"{digest}  {archive_path.name}\n".encode("ascii"))
        staged_archive.replace(archive_path)
        staged_checksum.replace(checksum_path)

    return archive_path, checksum_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    try:
        for path in build(args.output_dir):
            print(path.resolve())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Could not build release: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
