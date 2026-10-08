#!/usr/bin/env python3
"""Real-payload checks for the isolated package; never registers a queue or prints."""
import gzip
import copy
import hashlib
import importlib.util
import json
import os
import plistlib
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


standalone = load("standalone", PROJECT / "tools/capt-standalone.py")
native = load("native_tests", PROJECT / "tests/native-patch-test.py")
SOURCE = standalone.source.SOURCE / "expanded/Canon_CAPT.pkg/Payload"
ROOT = standalone.source.ARTIFACTS / "standalone-candidate"


class StandaloneTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ROOT.is_dir():
            raise RuntimeError("Build tools/capt-standalone.py before running these checks")
        cls.report = json.loads((ROOT / standalone.SUPPORT / "relocation.json").read_text())
        cls.temp = tempfile.TemporaryDirectory(prefix="lbp2900-tests-", dir=standalone.source.ARTIFACTS)
        cls.work = Path(cls.temp.name)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_queue_presence_uses_real_cups_output(self):
        helper = (PROJECT / "package/standalone/lbp2900-standalone").read_text()
        function = re.search(r"queue_exists\(\) \{.*?\n\}", helper, re.S).group(0)
        script = function + '\nQUEUE=LBP2900_missing_queue_presence_probe; queue_exists'
        result = subprocess.run(["/bin/sh", "-c", script], capture_output=True)
        self.assertEqual(result.returncode, 1)
        listed = subprocess.check_output(["/usr/bin/lpstat", "-v"], text=True)
        queues = re.findall(r"^device for ([^:]+):", listed, re.M)
        if queues:
            result = subprocess.run(["/bin/sh", "-c", function + '\nQUEUE="$1"; queue_exists', "probe", queues[0]], capture_output=True)
            self.assertEqual(result.returncode, 0)

    def test_only_one_model_and_no_official_install_path_overlap(self):
        files = {p.relative_to(ROOT) for p in ROOT.rglob("*") if p.is_file() or p.is_symlink()}
        official = {p.relative_to(SOURCE) for p in SOURCE.rglob("*") if p.is_file() or p.is_symlink()}
        self.assertFalse(files & official)
        self.assertEqual([p for p in files if p.name.endswith(".ppd.gz")], [standalone.PPD])
        runtime = ROOT / standalone.RUNTIME
        self.assertEqual(sorted(p.name for p in (runtime / "Bidi").iterdir()), ["captemon", "lb29monitor"])
        self.assertEqual([p.name for p in (runtime / "Bidi/captemon").iterdir()], ["msgtablecnab3.xml"])
        self.assertEqual([p.name for p in (runtime / "Recipe").iterdir()], ["CNMC2LBP3000AUK.rcp"])
        bitmaps = runtime / standalone.UTILITY / "Contents/Resources/status bitmaps"
        self.assertEqual([p.name for p in bitmaps.iterdir()], ["Canon LBP3000"])
        self.assertFalse((runtime / standalone.UTILITY / "Contents/Resources/printdata").exists())
        self.assertLess(sum(p.stat().st_size for p in ROOT.rglob("*") if p.is_file()), 50 * 1024**2)

    def test_guarded_changes_and_code_signatures_on_both_architectures(self):
        count = 0
        for relative, entry in self.report["files"].items():
            if "changes" not in entry:
                continue
            original = (SOURCE / entry["source"]).read_bytes()
            expected, changes = standalone.macho.relocate(
                original, standalone.BINARY_PATCHES.get(entry["source"]), entry["source"].endswith("Bidi/captmoncnab3"))
            self.assertEqual(changes, entry["changes"])
            installed = ROOT / relative
            actual = installed.read_bytes()
            # Signing can change LINKEDIT, but no machine code outside the pinned port instructions.
            self.assertEqual(native.text_sections(expected), native.text_sections(actual), relative)
            self.assertEqual(set(native.text_sections(actual)), {0x1000007, 0x100000C})
            self.assertNotIn(b"/Library/Printers/Canon/CUPSCAPT2", actual, relative)
            self.assertNotIn(b"cnbma2://", actual, relative)
            self.assertNotIn(b"localhost:59687", actual, relative)
            for change in changes:
                if change["kind"] == "port":
                    count += 1
                    # codesign may move the arm64 slice when x86 LINKEDIT shrinks.
                    start = standalone.macho.file_offset(actual, change["arch"], int(change["address"], 16))
                    after = bytes.fromhex(change["after"])
                    self.assertEqual(actual[start:start + len(after)], after)
            result = native.run("codesign", "--verify", "--strict", "--all-architectures", installed)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(count, 26)
        for relative, patch in standalone.BINARY_PATCHES.items():
            data = (SOURCE / relative).read_bytes()
            monitor = relative.endswith("Bidi/captmoncnab3")
            with self.assertRaises(ValueError):
                standalone.macho.relocate(data + b"foreign edit", patch, monitor)
            wrong_count = copy.deepcopy(patch)
            wrong_count["strings"]["CUPSCAPT2"] = wrong_count["strings"].get("CUPSCAPT2", 0) + 1
            with self.assertRaisesRegex(ValueError, "replacement count"):
                standalone.macho.relocate(data, wrong_count, monitor)
        # Even a correctly hashed but single-slice input is outside this pinned contract.
        relative, patch = next(iter(standalone.BINARY_PATCHES.items()))
        single = bytearray((SOURCE / relative).read_bytes())
        single[4:8] = (1).to_bytes(4, "big")
        patch = dict(patch, sha256=hashlib.sha256(single).hexdigest())
        with self.assertRaisesRegex(ValueError, "exactly one"):
            standalone.macho.relocate(bytes(single), patch)

    def test_dependencies_and_ppd_resources_resolve_inside_private_runtime(self):
        for relative, entry in self.report["files"].items():
            if "changes" not in entry:
                continue
            installed = ROOT / relative
            text = native.run("otool", "-L", installed).stdout
            commands = native.run("otool", "-l", installed).stdout
            identities = re.findall(r"cmd LC_ID_DYLIB\n\s+cmdsize \d+\n\s+name (.+?) \(offset", commands)
            rpaths = re.findall(r"cmd LC_RPATH\n\s+cmdsize \d+\n\s+path (.+?) \(offset", commands)
            for dependency in re.findall(r"^\s+([/@].+?) \(compatibility", text, re.M):
                if dependency in identities:
                    continue
                if dependency.startswith(("/System/", "/usr/lib/")):
                    continue
                if dependency.startswith("@rpath/"):
                    candidates = [Path(p.replace("@loader_path", str(installed.parent))) / dependency.removeprefix("@rpath/") for p in rpaths]
                    self.assertTrue(any(p.is_file() and p.resolve().is_relative_to((ROOT / standalone.RUNTIME).resolve()) for p in candidates),
                                    f"{relative}: unresolved {dependency}; searched {candidates}")
                    continue
                self.assertTrue(dependency.startswith("/" + str(standalone.RUNTIME)), dependency)
                self.assertTrue((ROOT / dependency.lstrip("/")).exists(), dependency)
        before = gzip.decompress((SOURCE / "Library/Printers/PPDs/Contents/Resources/CNMC2LBP3000AUK.ppd.gz").read_bytes()).decode()
        after = gzip.decompress((ROOT / standalone.PPD).read_bytes()).decode()
        changed = ("*ModelName:", "*NickName:", "*ShortNickName:", "*PCFileName:", "*Product:", "*Throughput:", "*opbidiPlugin:")
        self.assertEqual([line for line in before.splitlines() if not line.startswith(changed)],
                         [line.replace("LBP2900RT", "CUPSCAPT2") for line in after.splitlines() if not line.startswith(changed)])
        for key in ("APDialogExtension", "APPrinterUtilityPath", "APPrinterIconPath", "CNHelpName"):
            for value in re.findall(rf'^\*{key}: "(.+?)"', after, re.M):
                self.assertTrue((ROOT / value.lstrip("/")).exists(), value)
        agent = plistlib.loads((ROOT / standalone.AGENT).read_bytes())
        self.assertEqual(agent["Label"], "jp.co.canon.LBP2900RT.BackGrounder")
        self.assertTrue((ROOT / agent["ProgramArguments"][0].lstrip("/")).exists())

    def test_packaged_integrity_and_native_bundle_verification(self):
        helper = ROOT / standalone.SUPPORT / "lbp2900-standalone"
        result = native.run(helper, "check", ROOT, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        ppd = self.work / "standalone.ppd"
        ppd.write_bytes(gzip.decompress((ROOT / standalone.PPD).read_bytes()))
        result = native.run("cupstestppd", "-I", "filters", "-R", ROOT, ppd,
                            env=dict(os.environ, LANG="C", LC_ALL="C", SOFTWARE="StandaloneTest"))
        failures = [line.strip() for line in result.stdout.splitlines() if "**FAIL**" in line]
        self.assertEqual(failures, ["**FAIL**  Bad option Resolution choice 600"], result.stdout + result.stderr)
        self.assertEqual(result.returncode, 4)

    def test_release_language_variants_share_the_same_driver_payload(self):
        manifests = []
        for language in ("auto", "en", "vi"):
            filename = standalone.PACKAGE if language == "auto" else standalone.PACKAGE.replace(".pkg", f"-{language}.pkg")
            expanded = self.work / f"localized-{language}"
            result = native.run("pkgutil", "--expand-full", standalone.source.ARTIFACTS / filename, expanded, timeout=45)
            self.assertEqual(result.returncode, 0, result.stderr)
            resources = expanded / "Resources"
            locales = ("en", "vi") if language == "auto" else (language,)
            self.assertEqual(sorted(p.name for p in resources.glob("*.lproj")), sorted(f"{locale}.lproj" for locale in locales))
            for locale in locales:
                for page in ("Welcome", "ReadMe", "Conclusion"):
                    actual = resources / f"{locale}.lproj/{page}.html"
                    expected = PROJECT / f"package/installer-resources/{locale}.lproj/{page}.html"
                    self.assertEqual(actual.read_bytes(), expected.read_bytes())
                self.assertEqual((resources / f"{locale}.lproj/License.rtf").read_bytes(),
                                 (standalone.source.SOURCE / "LICENSE-CAPT-UK.rtf").read_bytes())
            fallback = "vi" if language == "vi" else "en"
            if language == "auto":
                for page in ("Welcome", "ReadMe", "Conclusion"):
                    self.assertFalse((resources / f"{page}.html").exists(), "Global pages override automatic localization")
            else:
                self.assertEqual((resources / "Welcome.html").read_bytes(),
                                 (resources / f"{fallback}.lproj/Welcome.html").read_bytes())
            distribution = (expanded / "Distribution").read_text()
            self.assertIn(f"<title>Canon LBP2900 v{standalone.VERSION}</title>", distribution)
            manifests.append((expanded / "runtime.pkg/Payload" / standalone.SUPPORT / "installed.sha256").read_bytes())
        self.assertEqual(manifests[0], manifests[1])
        self.assertEqual(manifests[1], manifests[2])

    def test_render_matches_original_without_loading_official_runtime(self):
        cases = (
            ("a4", 1, 595.276, 841.89, "PageSize=A4"),
            ("letter", 1, 612, 792, "PageSize=Letter"),
            ("multipage", 3, 595.276, 841.89, "PageSize=A4"),
            ("toner", 1, 595.276, 841.89, "PageSize=A4 CNTonerSaving=True CNTonerDensity=1 CNHalftone=pattern2 MediaType=HEAVY"),
            ("copies", 1, 595.276, 841.89, "PageSize=A4 Collate=True com.apple.print.PrintSettings.PMCopies..n.=2"),
        )
        output_dir = standalone.source.ARTIFACTS / "standalone-verification"
        output_dir.mkdir(exist_ok=True)
        rendered = {}
        for name, pages, width, height, options in cases:
            document = self.work / f"{name}.pdf"
            document.write_bytes(native.pdf(pages, width, height))
            outputs = []
            for root, base, ppd_path, variant in (
                (SOURCE, standalone.ORIGINAL, Path("Library/Printers/PPDs/Contents/Resources/CNMC2LBP3000AUK.ppd.gz"), "original"),
                (ROOT, standalone.RUNTIME, standalone.PPD, "standalone"),
            ):
                runtime = root / base
                ppd = self.work / f"{variant}.ppd"
                content = gzip.decompress((root / ppd_path).read_bytes()).decode()
                content = content.replace(f'*CNDriverRootPath: "/{base}"', f'*CNDriverRootPath: "{runtime}"')
                ppd.write_text(content)
                env = dict(os.environ, PPD=str(ppd), DYLD_LIBRARY_PATH=str(runtime / "Libs"), DYLD_PRINT_LIBRARIES="1")
                env.pop("PRINTER", None)
                result = subprocess.run([str(runtime / "Bins/capdftopdl"), "1", "test", "Relocation test", "1", options, str(document)],
                                        env=env, capture_output=True, timeout=30)
                (output_dir / f"{name}-{variant}.log").write_bytes(result.stderr)
                self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
                self.assertGreater(len(result.stdout), 1024)
                self.assertNotIn(b"execv() error", result.stderr)
                if variant == "standalone":
                    self.assertNotIn(b"/Canon/CUPSCAPT2/", result.stderr)
                    self.assertIn(str(runtime / "Libs/libcaptfilter2.dylib").encode(), result.stderr)
                outputs.append(result.stdout)
            self.assertEqual(outputs[0], outputs[1], name)
            rendered[name] = outputs[1]
        self.assertNotEqual(rendered["a4"], rendered["toner"])
        self.assertNotEqual(rendered["a4"], rendered["copies"])

    def test_official_payload_overlay_in_both_install_orders(self):
        # Real files, not mock installer calls. Script side-effects are reviewed separately.
        expected = {p.relative_to(ROOT): standalone.source.digest(p) for p in ROOT.rglob("*") if p.is_file()}
        for order in ((ROOT, SOURCE), (SOURCE, ROOT)):
            target = self.work / "overlay"
            for payload in order:
                shutil.copytree(payload, target, symlinks=True, dirs_exist_ok=True)
            for path, digest in expected.items():
                self.assertEqual(standalone.source.digest(target / path), digest, str(path))
            shutil.rmtree(target)
        # These are the exact broad process selectors in the pinned Canon preinstall.
        commands = [f"/{standalone.RUNTIME}/CCPD/ccpd", f"/{standalone.RUNTIME}/Bidi/lb29monitor",
                    f"/{standalone.RUNTIME}/{standalone.BG}/Contents/MacOS/Canon 2900 BackGrounder"]
        for command in commands:
            for selector in (r"CUPSCAPT.*/CCPD/ccpd", r"captmon", r"Canon CAPT BackGrounder.app"):
                self.assertIsNone(re.search(selector, command))

    def test_error_notification_channel_is_private_on_both_architectures(self):
        # These two endpoints post/observe the distributed notification that
        # auto-opens StatusMonitor. Sharing Canon's name launches its app too.
        for source_relative in (
            standalone.ORIGINAL / "Bidi/captmoncnab3",
            standalone.ORIGINAL / "BackGrounder/Canon CAPT BackGrounder.app/Contents/MacOS/Canon CAPT BackGrounder",
        ):
            for root, path, present, absent in (
                (SOURCE, source_relative, b"\0capt\0", b"\0lb29\0"),
                (ROOT, standalone.destination(source_relative), b"\0lb29\0", b"\0capt\0"),
            ):
                data = (root / path).read_bytes()
                for arch, offset, size in standalone.macho.slices(data):
                    section = data[offset:offset + size]
                    self.assertEqual(section.count(present), 1, f"{path}: {arch}")
                    self.assertNotIn(absent, section, f"{path}: {arch}")

    def test_lifecycle_guards_and_removal_preserve_official_files(self):
        helper = ROOT / standalone.SUPPORT / "lbp2900-standalone"
        target = self.work / "lifecycle root with spaces"
        shutil.copytree(SOURCE, target, symlinks=True)
        result = native.run(helper, "preflight", target)
        self.assertEqual(result.returncode, 0, result.stderr)
        shutil.copytree(ROOT, target, symlinks=True, dirs_exist_ok=True)
        result = native.run(helper, "preflight", target)
        self.assertNotEqual(result.returncode, 0, "Existing installation must not be overwritten")
        monitor = target / standalone.RUNTIME / "Bidi/lb29monitor"
        before = monitor.read_bytes()
        monitor.write_bytes(before + b"foreign change")
        result = native.run(helper, "remove", target, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(monitor.read_bytes(), before + b"foreign change")
        monitor.write_bytes(before)
        extra = target / standalone.RUNTIME / "user-file.txt"
        extra.write_text("Preserve this user-owned file")
        result = native.run(helper, "remove", target, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(extra.exists())
        extra.unlink()
        result = native.run(helper, "remove", target, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((target / standalone.RUNTIME).exists())
        for path in SOURCE.rglob("*"):
            if path.is_file():
                self.assertEqual(standalone.source.digest(path), standalone.source.digest(target / path.relative_to(SOURCE)))
        result = native.run(helper, "remove", target, timeout=30)
        self.assertNotEqual(result.returncode, 0, "Removing an absent installation must fail closed")
        # A dangling namespace symlink must be refused before package installation.
        (target / standalone.RUNTIME).symlink_to(self.work / "absent-target")
        result = native.run(helper, "preflight", target)
        self.assertNotEqual(result.returncode, 0)

    def test_process_ownership_uses_executable_when_monitor_argv_is_relative(self):
        # Real OS processes, without loading Canon code or opening a printer.
        target = self.work / "process root with spaces"
        program = self.work / "wait.c"
        program.write_text("#include <unistd.h>\nint main(void) { sleep(60); return 0; }\n")
        executable = self.work / "wait"
        subprocess.run(["xcrun", "clang", str(program), "-o", str(executable)], check=True, capture_output=True)
        paths = [target / standalone.RUNTIME / "Bidi/lb29monitor",
                 target / standalone.ORIGINAL / "Bidi/captmonlbp2900",
                 target / standalone.ORIGINAL / "Bidi/captmonother"]
        uri = "usb://Canon/LBP2900?serial=process-test"
        processes = []
        definitions = (PROJECT / "package/standalone/lbp2900-standalone").read_text().split('case "${1:-}" in', 1)[0]
        try:
            for path, device in zip(paths, (uri, uri, uri + "-other")):
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(executable, path)
                processes.append(subprocess.Popen([path.name, "--printer-uri=" + device], executable=path))
            private = native.run("/bin/sh", "-c", definitions + '\nroot=$1\nprivate_pids\n', "test", target)
            self.assertEqual(private.returncode, 0, private.stderr)
            self.assertEqual(private.stdout.split(), [str(processes[0].pid)])
            official = native.run("/bin/sh", "-c", definitions + '\nroot=$1\nofficial_monitor_pids "$2"\n', "test", target, uri)
            self.assertEqual(official.returncode, 0, official.stderr)
            self.assertEqual(official.stdout.split(), [str(processes[1].pid)])
        finally:
            for process in processes:
                process.terminate()
                process.wait(timeout=5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
