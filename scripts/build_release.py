"""Build versioned Codex marketplace ZIPs and their checksums."""

import argparse
import hashlib
import json
import posixpath
import re
import shutil
import stat
import sys
import tarfile
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from urllib.request import urlopen
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
PYTHON_VERSION = "3.12.16"
PYTHON_BUILD = "20261110"
PYTHON_REPOSITORY = "https://github.com/astral-sh/python-build-standalone"
PYTHON_RELEASE = f"{PYTHON_REPOSITORY}/releases/download/{PYTHON_BUILD}"
PYTHON_LICENSES = "https://raw.githubusercontent.com/astral-sh/python-build-standalone"
PYTHON_LICENSES_SHA256 = "e43fb936c6655d7996dba480d7ebdea492d6040ec388eb8ed9d1000f72de8cab"
PYTHON_RUNTIMES = {
    "linux-x64": (
        "x86_64-unknown-linux-gnu",
        "6a9e62dad033790aef722dbd370e0ce76ce17b73627ba3ae679f537049350b39",
    ),
    "linux-arm64": (
        "aarch64-unknown-linux-gnu",
        "b6a41defec4975d94b4ff1950236e7383e5c02ba40ea48c9ec33c66087a35aab",
    ),
    "macos-x64": (
        "x86_64-apple-darwin",
        "b78a4c479f1964ec484880bee567568266f68da102269fb93a05fe8716b45f91",
    ),
    "macos-arm64": (
        "aarch64-apple-darwin",
        "2f11b8aa3726bdbd87dd9eb76568412faddf4f47e26913fa45d6a2e424972acd",
    ),
    "windows-x64": (
        "x86_64-pc-windows-msvc",
        "355ee61b8207b91574491b1c6dc9b0ebb4408fc56bfafe498f3ef439314b52dc",
    ),
    "windows-arm64": (
        "aarch64-pc-windows-msvc",
        "c1b334c7b1db8f962b37a333d8362cab0ba7ebda1a7cce917fae56a1e0c8cbe7",
    ),
}


def read_object(path):
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path.as_posix()}")
    return value


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_verified(name, url, checksum, temporary_dir, cache_dir):
    path = cache_dir / name if cache_dir else None
    if path is None or not path.is_file():
        path = temporary_dir / name
        with urlopen(url, timeout=60) as response, path.open("wb") as destination:
            shutil.copyfileobj(response, destination)
    if sha256(path) != checksum:
        raise ValueError(f"SHA-256 mismatch for bundled Python asset {name}")
    return path


def write_zip_entry(archive, name, contents, mode=0o644):
    entry = ZipInfo(name)
    entry.create_system = 3
    entry.external_attr = (stat.S_IFREG | mode) << 16
    archive.writestr(entry, contents, compress_type=ZIP_DEFLATED, compresslevel=6)
    return entry


def runtime_member_path(name):
    path = PurePosixPath(name)
    if path.parts[:1] != ("python",) or ".." in path.parts or "\\" in name or ":" in name:
        raise ValueError(f"Unsafe Python runtime path: {name}")
    return path.as_posix()


def add_runtime(archive, archive_root, runtime_tar, executable):
    prefix = f"{archive_root}/{PLUGIN.as_posix()}/runtime"
    entries = {}
    links = {}
    with tarfile.open(runtime_tar, "r|gz") as runtime:
        for member in runtime:
            name = runtime_member_path(member.name)
            if member.isdir():
                continue
            if name == "python" or name in entries or name in links:
                raise ValueError(f"Invalid or repeated Python runtime entry: {name}")
            if member.isfile():
                mode = 0o755 if member.mode & 0o111 else 0o644
                with runtime.extractfile(member) as source:
                    entries[name] = write_zip_entry(
                        archive, f"{prefix}/{name.removeprefix('python/')}", source.read(), mode
                    )
            elif member.issym() or member.islnk():
                target = member.linkname
                if member.issym():
                    target = posixpath.join(posixpath.dirname(name), target)
                links[name] = runtime_member_path(posixpath.normpath(target))
            else:
                raise ValueError(f"Unsupported Python runtime entry: {name}")

    # Codex skips symbolic links when copying a plugin into its cache. Store
    # aliases as ordinary files, after verifying each target stays in the runtime.
    for name, destination in sorted(links.items()):
        seen = {name}
        while destination in links:
            if destination in seen:
                raise ValueError(f"Cyclic Python runtime link: {name}")
            seen.add(destination)
            destination = links[destination]
        if destination not in entries:
            raise ValueError(f"Missing target for Python runtime link: {name}")
        target = entries[destination]
        entries[name] = write_zip_entry(
            archive,
            f"{prefix}/{name.removeprefix('python/')}",
            archive.read(target),
            stat.S_IMODE(target.external_attr >> 16),
        )

    executable_entry = entries.get(f"python/{executable}")
    if executable_entry is None or not (executable_entry.external_attr >> 16) & stat.S_IXUSR:
        raise ValueError(f"Python runtime is missing an executable {executable}")


def build(output_dir, platform="source", cache_dir=None):
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
    mcp_files = {PLUGIN / name: read_object(PLUGIN / name) for name in ("mcp.json", ".mcp.json")}

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
    if platform != "source":
        archive_root += f"-{platform}"
    archive_path = output_dir / f"{archive_root}.zip"
    checksum_path = archive_path.with_suffix(".zip.sha256")
    output_dir.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output_dir) as temporary_dir:
        temporary_dir = Path(temporary_dir)
        staged_archive = temporary_dir / archive_path.name
        mcp_overrides = {}
        if platform != "source":
            executable = "python.exe" if platform.startswith("windows-") else "bin/python3"
            target, runtime_checksum = PYTHON_RUNTIMES[platform]
            runtime_name = f"cpython-{PYTHON_VERSION}+{PYTHON_BUILD}-{target}-install_only_stripped.tar.gz"
            runtime_url = f"{PYTHON_RELEASE}/{runtime_name.replace('+', '%2B')}"
            runtime_tar = fetch_verified(runtime_name, runtime_url, runtime_checksum, temporary_dir, cache_dir)
            license_text = fetch_verified(
                f"python-build-standalone-{PYTHON_BUILD}-licenses.rst",
                f"{PYTHON_LICENSES}/{PYTHON_BUILD}/python-licenses.rst",
                PYTHON_LICENSES_SHA256,
                temporary_dir,
                cache_dir,
            ).read_bytes()
            for path, mcp in mcp_files.items():
                server = mcp["mcpServers"]["cat_two_local"]
                server["command"] = f"./runtime/{executable}"
                server["args"] = ["-E", "-s", *server["args"]]
                mcp_overrides[path] = (json.dumps(mcp, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        with ZipFile(staged_archive, "w") as archive:
            for path in sorted(files, key=Path.as_posix):
                source = ROOT / path
                if not source.is_file() or source.resolve() != source:
                    raise ValueError(f"Expected a regular file at {path.as_posix()}")
                contents = mcp_overrides[path] if path in mcp_overrides else source.read_bytes()
                write_zip_entry(archive, f"{archive_root}/{path.as_posix()}", contents)
            if platform != "source":
                add_runtime(archive, archive_root, runtime_tar, executable)
                prefix = f"{archive_root}/{PLUGIN.as_posix()}/runtime"
                write_zip_entry(archive, f"{prefix}/THIRD-PARTY-LICENSES.rst", license_text)
                sources = (
                    f"CPython {PYTHON_VERSION} for {target}\n"
                    f"Original binary archive: {runtime_url}\n"
                    f"Build recipes and dependency sources: {PYTHON_REPOSITORY}/tree/{PYTHON_BUILD}\n"
                    f"CPython source: https://www.python.org/ftp/python/{PYTHON_VERSION}/Python-{PYTHON_VERSION}.tar.xz\n"
                    "Berkeley DB source: https://ftp.osuosl.org/pub/blfs/conglomeration/db/db-6.0.19.tar.gz\n"
                )
                write_zip_entry(archive, f"{prefix}/THIRD-PARTY-SOURCES.txt", sources.encode("ascii"))
        with ZipFile(staged_archive) as archive:
            if archive.testzip() is not None:
                raise ValueError("The release archive failed its integrity check")

        digest = sha256(staged_archive)
        staged_checksum = temporary_dir / checksum_path.name
        staged_checksum.write_bytes(f"{digest}  {archive_path.name}\n".encode("ascii"))
        staged_archive.replace(archive_path)
        staged_checksum.replace(checksum_path)

    return archive_path, checksum_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--platform", choices=("source", "all", *PYTHON_RUNTIMES), default="source")
    parser.add_argument("--runtime-cache", type=Path, help="Reuse verified runtime archives from this directory")
    args = parser.parse_args()
    platforms = PYTHON_RUNTIMES if args.platform == "all" else (args.platform,)
    try:
        for platform in platforms:
            for path in build(args.output_dir, platform, args.runtime_cache):
                print(path.resolve(), flush=True)
    except (OSError, ValueError, KeyError, TypeError, tarfile.TarError) as error:
        print(f"Could not build release: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
