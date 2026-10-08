#!/usr/bin/env python3
"""Build an isolated LBP2900-only runtime from the verified official CAPT package."""
import argparse
import gzip
import importlib.util
import json
import os
import plistlib
import shutil
import subprocess
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), PROJECT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


source = load("capt-project")
macho = load("capt-macho")
ORIGINAL = Path("Library/Printers/Canon/CUPSCAPT2")
RUNTIME = Path("Library/Printers/Canon/LBP2900RT")
SUPPORT = Path("Library/Application Support/CanonLBP2900Standalone")
PPD = Path("Library/Printers/PPDs/Contents/Resources/LocalLBP2900CAPT.ppd.gz")
BACKEND = Path("usr/libexec/cups/backend/lb29u2")
AGENT = Path("Library/LaunchAgents/jp.co.canon.LBP2900RT.BG.plist")
BG = "BackGrounder/Canon 2900 BackGrounder.app"
UTILITY = "StatusMonitor/StatusMonitor.app"
VERSION = "27.3.3"
PACKAGE = f"Canon-LBP2900-v{VERSION}.pkg"
SIGNING_NOTICES = {
    "en": {
        "adhoc": "The package is ad-hoc signed, without Developer ID Installer/notarization.",
        "developer-id": "This package is signed with Developer ID. See the release notes for its notarization status.",
    },
    "vi": {
        "adhoc": "Gói ký ad-hoc, chưa có Developer ID Installer/notarization.",
        "developer-id": "Gói được ký bằng Developer ID. Xem ghi chú phát hành để biết trạng thái notarization.",
    },
}
BINARY_PATCHES = json.loads((PROJECT / "config/standalone-binary-patches.json").read_text())
SHARED_DIRECTORIES = (
    "Libs/",
    "cnaccm/",
    "Manual/",
    "Icons/",
    "CCPD/",
    "BackGrounder/",
)
MODEL_FILES = {
    "Bins/capdftopdl",
    "Bins/xdclfilter",
    "Profiles/CNLK.PRF",
    "Recipe/CNMC2LBP3000AUK.rcp",
    "Bidi/captmoncnab3",
    "Bidi/captemon/msgtablecnab3.xml",
}
PDE_BUNDLES = {
    "CAPTUIKit.framework",
    "FinishingPDE.plugin",
    "InputTrayPDE.plugin",
    "QualitySetPDE.plugin",
    "VersionPDE.plugin",
}


def selected(relative):
    """Only this model's entry points, plus the shared native rendering/utility code."""
    if relative.as_posix() == "usr/libexec/cups/backend/cnbma2":
        return True
    if not relative.is_relative_to(ORIGINAL):
        return False
    runtime_relative = relative.relative_to(ORIGINAL)
    name = runtime_relative.as_posix()
    if name.startswith(SHARED_DIRECTORIES):
        return name != "Libs/libcaptfilter.dylib"
    if name in MODEL_FILES:
        return True
    if name.startswith("PDEs/"):
        return runtime_relative.parts[1] in PDE_BUNDLES
    if name.startswith("StatusMonitor/"):
        if "/printdata/" in name:
            return False  # No LBP3000 data exists here in Canon's original package.
        if "/status bitmaps/" in name:
            return "/status bitmaps/Canon LBP3000/" in name
        return True
    return False


def destination(relative):
    if relative.as_posix() == "usr/libexec/cups/backend/cnbma2":
        return BACKEND
    name = (RUNTIME / relative.relative_to(ORIGINAL)).as_posix()
    name = name.replace("Canon CAPT BackGrounder", "Canon 2900 BackGrounder")
    if name.endswith("/Bidi/captmoncnab3"):
        name = name.removesuffix("captmoncnab3") + "lb29monitor"
    return Path(name)


def sign(path, identity="-"):
    options = ["--timestamp=none"] if identity == "-" else ["--options=runtime", "--timestamp"]
    source.run("codesign", "--force", "--sign", identity,
               "--preserve-metadata=entitlements,flags,runtime", *options, path,
               stdout=subprocess.DEVNULL)
    source.run("codesign", "--verify", "--strict", "--all-architectures", path,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def make_ppd(payload):
    original = payload / "Library/Printers/PPDs/Contents/Resources/CNMC2LBP3000AUK.ppd.gz"
    ppd = gzip.decompress(original.read_bytes()).decode()
    lines = []
    identity = {"ModelName": "Canon LBP2900", "NickName": "Canon LBP2900",
                "ShortNickName": "LBP2900", "PCFileName": "CNL290AK.PPD", "Product": "(lbp2900)",
                "Throughput": "12"}
    for line in ppd.splitlines(keepends=True):
        key = line.partition(":")[0].lstrip("*")
        if key in identity:
            line = f'*{key}: "{identity[key]}"\n'
        lines.append(line)
    return "".join(lines).replace("CUPSCAPT2", "LBP2900RT").replace("captmoncnab3", "lb29monitor").encode()


def build_cancel_bridge(root, identity="-"):
    directory = root / RUNTIME / "CCPD"
    common = ["xcrun", "clang", "-arch", "arm64", "-arch", "x86_64", "-mmacosx-version-min=11.0",
              "-O2", "-Wall", "-Wextra", "-Werror"]
    source.run(*common, "-dynamiclib", PROJECT / "native/cups-cancel-bridge.c",
               "-Wl,-reexport-lcups", "-Wl,-install_name,@loader_path/lb29.dylib",
               "-compatibility_version", "2.0.0", "-current_version", "2.14.0", "-o", directory / "lb29.dylib")
    source.run(*common, "-Wno-deprecated-declarations", PROJECT / "native/cups-cancel-helper.c",
               "-lcups", "-o", directory / "lb29-cancel")
    for name in ("lb29.dylib", "lb29-cancel"):
        sign(directory / name, identity)


def assemble(payload, root, identity="-"):
    source.validate_source(payload)
    root.mkdir(parents=True)
    report = {"version": VERSION, "source_dmg_sha256": source.CONFIG["sha256"], "files": {}}
    for original in sorted(payload.rglob("*")):
        relative = original.relative_to(payload)
        if not selected(relative) or not (original.is_file() or original.is_symlink()):
            continue
        target = root / destination(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        if original.is_symlink():
            target.symlink_to(os.readlink(original))
            continue
        shutil.copy2(original, target)
        data = original.read_bytes()
        entry = {"source": str(relative), "source_sha256": source.digest(original)}
        if data[:4] == b"\xca\xfe\xba\xbe":
            data, changes = macho.relocate(data, BINARY_PATCHES.get(str(relative)), original.name == "captmoncnab3")
            target.write_bytes(data)
            entry["changes"] = changes
            sign(target, identity)
        elif original.name == "Info.plist":
            info = plistlib.loads(data)
            for key, value in info.items():
                if isinstance(value, str):
                    for before, after in macho.REPLACEMENTS:
                        value = value.replace(before.decode(), after.decode())
                    info[key] = value
            if relative.as_posix().endswith("StatusMonitor.app/Contents/Info.plist"):
                info["CFBundleDisplayName"] = "Canon LBP2900 Printer Utility"
                info["CFBundleName"] = "Canon LBP2900 Utility"
            target.write_bytes(plistlib.dumps(info))
        report["files"][str(target.relative_to(root))] = entry

    build_cancel_bridge(root, identity)
    # Resign bundles inside out after resource pruning and identifier relocation.
    bundles = [p for p in root.rglob("*") if p.suffix in (".app", ".plugin", ".bundle", ".framework") and p.is_dir()]
    for bundle in sorted(bundles, key=lambda p: len(p.parts), reverse=True):
        sign(bundle, identity)
    (root / PPD).parent.mkdir(parents=True, exist_ok=True)
    (root / PPD).write_bytes(gzip.compress(make_ppd(payload), mtime=0))
    agent = plistlib.loads((payload / "Library/LaunchAgents/jp.co.canon.CUPSCAPT2.BG.plist").read_bytes())
    agent["Label"] = "jp.co.canon.LBP2900RT.BackGrounder"
    agent["ProgramArguments"] = [f"/{RUNTIME}/{BG}/Contents/MacOS/Canon 2900 BackGrounder"]
    (root / AGENT).parent.mkdir(parents=True, exist_ok=True)
    (root / AGENT).write_bytes(plistlib.dumps(agent))
    support = root / SUPPORT
    support.mkdir(parents=True)
    shutil.copy2(source.SOURCE / "LICENSE-CAPT-UK.rtf", support / "LICENSE-CAPT-UK.rtf")
    helper = "lbp2900-standalone"
    shutil.copy2(PROJECT / "package/standalone" / helper, support / helper)
    (support / helper).chmod(0o755)
    (support / "version").write_text(VERSION + "\n")
    (support / "relocation.json").write_text(json.dumps(report, indent=2) + "\n")
    paths = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() or p.is_symlink()}
    paths.update(str(SUPPORT / name) for name in ("installed.sha256", "installed-paths.txt"))
    (support / "installed-paths.txt").write_text("\n".join(sorted(paths)) + "\n")
    source.write_runtime_manifest(root, support / "installed.sha256")
    return report


def build(application_identity="-", installer_identity=None, output_directory=None):
    if (application_identity != "-") != bool(installer_identity):
        raise ValueError("Provide both Developer ID Application and Installer identities")
    output_directory = Path(output_directory or source.ARTIFACTS).resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    payload = source.prepare()
    with tempfile.TemporaryDirectory(prefix="lbp2900-package-", dir=output_directory) as temporary:
        scratch = Path(temporary)
        root = scratch / "root"
        assemble(payload, root, application_identity)
        scripts = scratch / "scripts"
        scripts.mkdir()
        for name in ("preinstall", "postinstall", "lbp2900-standalone"):
            shutil.copy2(PROJECT / "package/standalone" / name, scripts / name)
            (scripts / name).chmod(0o755)
        # Disable bundle relocation; the native PPD contains absolute paths.
        components = scratch / "components.plist"
        source.run("pkgbuild", "--analyze", "--root", root, components, stdout=subprocess.DEVNULL)
        entries = plistlib.loads(components.read_bytes())
        for entry in entries:
            entry["BundleIsRelocatable"] = False
            entry["BundleOverwriteAction"] = "upgrade"
        components.write_bytes(plistlib.dumps(entries))
        component = scratch / "runtime.pkg"
        source.run("pkgbuild", "--root", root, "--scripts", scripts, "--component-plist", components,
                   "--identifier", "local.canon-lbp2900.capt10.standalone", "--version", VERSION,
                   "--ownership", "recommended", "--install-location", "/", component)
        resources = scratch / "resources"
        resource_source = PROJECT / "package/installer-resources"
        resources.mkdir()
        # One package follows macOS language preferences. Global HTML would
        # shadow the localized resources, so keep pages only inside .lproj.
        for locale in ("en", "vi"):
            shutil.copytree(resource_source / f"{locale}.lproj", resources / f"{locale}.lproj")
            readme = resources / f"{locale}.lproj/ReadMe.html"
            content = readme.read_text()
            if content.count("@@SIGNING_NOTICE@@") != 1:
                raise ValueError(f"Missing or duplicated signing notice in {readme.name} ({locale})")
            mode = "developer-id" if installer_identity else "adhoc"
            readme.write_text(content.replace("@@SIGNING_NOTICE@@", SIGNING_NOTICES[locale][mode]))
        # Canon's agreement remains intact and in its original English in every locale.
        for directory in (resources, *resources.glob("*.lproj")):
            shutil.copy2(source.SOURCE / "LICENSE-CAPT-UK.rtf", directory / "License.rtf")
        distribution = scratch / "Distribution.xml"
        distribution.write_text(f'''<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="2">
<title>Canon LBP2900 v{VERSION}</title>
<welcome file="Welcome.html"/><readme file="ReadMe.html"/><license file="License.rtf"/>
<conclusion file="Conclusion.html"/>
<options customize="never" require-scripts="true" hostArchitectures="arm64,x86_64"/>
<domains enable_localSystem="true" enable_currentUserHome="false" enable_anywhere="false"/>
<choices-outline><line choice="runtime"/></choices-outline>
<choice id="runtime" visible="false"><pkg-ref id="local.canon-lbp2900.capt10.standalone"/></choice>
<pkg-ref id="local.canon-lbp2900.capt10.standalone" version="{VERSION}">runtime.pkg</pkg-ref>
</installer-gui-script>
''')
        output = output_directory / PACKAGE
        signing = ["--sign", installer_identity, "--timestamp"] if installer_identity else []
        source.run("productbuild", "--distribution", distribution, "--resources", resources,
                   "--package-path", scratch, *signing, output)
        if installer_identity:
            source.run("pkgutil", "--check-signature", output)
        check = scratch / "expanded"
        source.run("pkgutil", "--expand-full", output, check)
        unpacked = check / "runtime.pkg/Payload"
        if source.digest(unpacked / SUPPORT / "installed.sha256") != source.digest(root / SUPPORT / "installed.sha256"):
            raise ValueError("Packaged manifest changed")
        source.run("shasum", "-a", "256", "-c", unpacked / SUPPORT / "installed.sha256",
                   cwd=unpacked, stdout=subprocess.DEVNULL)
        # Keep this exact candidate for independent integration checks.
        candidate = output_directory / "standalone-candidate"
        if candidate.exists():
            shutil.rmtree(candidate)
        shutil.copytree(unpacked, candidate, symlinks=True)
        output.with_suffix(".sha256").write_text(f"{source.digest(output)}  {output.name}\n")
    print(f"Built experimental LBP2900 driver installer: {output} ({output.stat().st_size:,} bytes)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--application-identity", default="-", help="Developer ID Application identity (default: ad-hoc)")
    parser.add_argument("--installer-identity", help="Developer ID Installer identity; required with Application identity")
    parser.add_argument("--output-directory", type=Path, help="Package and candidate directory (default: artifacts)")
    args = parser.parse_args()
    try:
        build(args.application_identity, args.installer_identity, args.output_directory)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"LBP2900 driver: {exc}\n")
