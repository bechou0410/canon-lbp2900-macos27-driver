#!/usr/bin/env python3
"""Prepare verified Canon input and build a patch-only macOS installer."""

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
ARTIFACTS = PROJECT / "artifacts"
SOURCE = ARTIFACTS / "canon-source"
CONFIG = json.loads((PROJECT / "config/canon-capt-10.0.10.json").read_text())
SUPPORT = Path("Library/Application Support/CanonLBP2900CAPTPatch")
PACKAGE_NAME = "Canon-LBP2900-CAPT-10.0.10-patch-0.1.0.pkg"


def run(*args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, **kwargs)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def validate_source(payload):
    for name, expected in CONFIG["runtime_sha256"].items():
        if digest(payload / name) != expected:
            raise ValueError(f"Unexpected original Canon file: {name}")


def prepare():
    SOURCE.mkdir(parents=True, exist_ok=True)
    dmg = SOURCE / "mac-capt-v10010-uken.dmg"
    if not dmg.exists():
        partial = dmg.with_suffix(".download")
        run("curl", "--fail", "--location", "--proto", "=https", "--proto-redir", "=https",
            "--tlsv1.2", "--output", partial, CONFIG["url"])
        if digest(partial) != CONFIG["sha256"]:
            raise ValueError("Downloaded Canon DMG checksum mismatch")
        partial.replace(dmg)
    if digest(dmg) != CONFIG["sha256"]:
        raise ValueError("Canon DMG checksum mismatch; refusing the cached input")

    with tempfile.TemporaryDirectory(prefix="capt-mount-") as mount:
        run("hdiutil", "attach", "-readonly", "-nobrowse", "-noautoopen", "-mountpoint", mount, dmg,
            stdout=subprocess.DEVNULL)
        try:
            pkg = Path(mount) / "MacOSX/Canon_CAPT_Installer.pkg"
            signature = run("pkgutil", "--check-signature", pkg, capture_output=True, text=True).stdout
            if CONFIG["signer"] not in signature:
                raise ValueError("Expected Canon Developer ID Installer signer")
            assessment = run("spctl", "--assess", "--type", "install", "--verbose=2", pkg,
                             capture_output=True, text=True)
            if "Notarized Developer ID" not in assessment.stderr:
                raise ValueError("Canon package is not assessed as notarized")
            # Keep Canon's installer and license intact for user-initiated installation.
            shutil.copytree(Path(mount) / "MacOSX", SOURCE / "MacOSX", dirs_exist_ok=True)
            for name in ("LICENSE-CAPT-UK.rtf", "README-CAPT-UK.rtf"):
                shutil.copy2(Path(mount) / "Documents" / name, SOURCE / name)
            with tempfile.TemporaryDirectory(prefix="capt-extract-", dir=ARTIFACTS) as scratch:
                expanded = Path(scratch) / "expanded"
                run("pkgutil", "--expand-full", pkg, expanded)
                validate_source(expanded / "Canon_CAPT.pkg/Payload")
                destination = SOURCE / "expanded"
                if destination.exists():
                    shutil.rmtree(destination)
                expanded.replace(destination)
            (SOURCE / "verification.txt").write_text(signature + "\n" + assessment.stderr)
        finally:
            run("hdiutil", "detach", mount, stdout=subprocess.DEVNULL)
    print("Verified official Canon CAPT V10.0.10; no system files changed.")
    return SOURCE / "expanded/Canon_CAPT.pkg/Payload"


def write_runtime_manifest(payload, destination):
    # Include the entire native runtime, PPDs, backend and launch agent. Follow no
    # directory symlinks; file symlinks are resolved just as shasum resolves them.
    paths = sorted(p for p in payload.rglob("*") if p.is_file())
    destination.write_text("".join(f"{digest(p)}  {p.relative_to(payload)}\n" for p in paths))


def build():
    payload = prepare()
    with tempfile.TemporaryDirectory(prefix="capt-package-", dir=ARTIFACTS) as scratch_directory:
        scratch = Path(scratch_directory)
        root, scripts = scratch / "root", scratch / "scripts"
        support = root / SUPPORT
        support.mkdir(parents=True)
        scripts.mkdir()
        write_runtime_manifest(payload, support / "runtime.sha256")
        for destination in (support, scripts):
            shutil.copy2(PROJECT / "package/capt-patch", destination / "capt-patch")
            (destination / "capt-patch").chmod(0o755)
        shutil.copy2(support / "runtime.sha256", scripts / "runtime.sha256")
        shutil.copy2(PROJECT / "tools/configure-native-queue.sh", support / "configure-native-queue")
        (support / "configure-native-queue").chmod(0o755)
        for name in ("preinstall", "postinstall"):
            shutil.copy2(PROJECT / "package" / name, scripts / name)
            (scripts / name).chmod(0o755)
        output = ARTIFACTS / PACKAGE_NAME
        run("pkgbuild", "--root", root, "--scripts", scripts, "--identifier",
            "local.canon-lbp2900.capt10.patch", "--version", "0.1.0", "--ownership",
            "recommended", "--install-location", "/", output)
        run("pkgutil", "--expand-full", output, scratch / "package-check")
        installed = scratch / "package-check/Payload" / SUPPORT
        if not (installed / "capt-patch").is_file():
            raise ValueError("Built package is missing its patch helper")
        if any(p.suffix in (".dylib", ".gz") or p.name == "captmoncnab3"
               for p in (scratch / "package-check/Payload").rglob("*")):
            raise ValueError("Proprietary payload unexpectedly included")
        (ARTIFACTS / "SHA256SUMS").write_text(f"{digest(output)}  {output.name}\n")
    print(f"Built patch-only installer: {output}")
    print("Experimental: physical printing and Canon StatusMonitor acceptance are still required.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "build"))
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            prepare()
        else:
            build()
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"CAPT project: {exc}\n")


if __name__ == "__main__":
    main()
