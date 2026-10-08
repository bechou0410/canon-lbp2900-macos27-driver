#!/usr/bin/env python3
"""Integration checks against the verified, real Canon payload. Never installs it."""
import gzip
import importlib.util
import os
import shutil
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("capt_project", PROJECT / "tools/capt-project.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)
SOURCE = build.SOURCE / "expanded/Canon_CAPT.pkg/Payload"
BASE = Path("Library/Printers/Canon/CUPSCAPT2")
PPDS = Path("Library/Printers/PPDs/Contents/Resources")


def run(*args, **kwargs):
    return subprocess.run([str(a) for a in args], capture_output=True, text=True, **kwargs)


def text_sections(data):
    """Extract machine instructions from every 64-bit slice, excluding signatures."""
    result = {}
    for i in range(struct.unpack_from(">I", data, 4)[0]):
        cpu, _, offset, _, _ = struct.unpack_from(">IIIII", data, 8 + 20 * i)
        ncmds = struct.unpack_from("<I", data, offset + 16)[0]
        cursor = offset + 32
        for _ in range(ncmds):
            cmd, size = struct.unpack_from("<II", data, cursor)
            if cmd == 0x19:  # LC_SEGMENT_64
                nsects = struct.unpack_from("<I", data, cursor + 64)[0]
                for section in range(nsects):
                    pos = cursor + 72 + section * 80
                    name = data[pos:pos + 16].rstrip(b"\0")
                    if name == b"__text":
                        _, length, start = struct.unpack_from("<QQI", data, pos + 32)
                        result[cpu] = data[offset + start:offset + start + length]
            cursor += size
    return result


def pdf(pages, width, height):
    """Generate real vector PDF pages, with unique visible page labels."""
    objects = [b"", b""]
    kids = []
    for page in range(pages):
        number = len(objects) + 1
        kids.append(f"{number} 0 R")
        text = f"BT /F1 24 Tf 50 {height - 65} Td (CAPT native test - page {page + 1}) Tj ET\n".encode()
        objects.extend([
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /Contents {number + 1} 0 R >>".encode(),
            f"<< /Length {len(text)} >>\nstream\n".encode() + text + b"endstream",
        ])
    objects[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {pages} >>".encode()
    data, offsets = b"%PDF-1.4\n", [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(data)
    data += f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode()
    data += b"".join(f"{n:010d} 00000 n \n".encode() for n in offsets[1:])
    return data + f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()


class NativePatchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build.validate_source(SOURCE)
        cls.temp = tempfile.TemporaryDirectory(prefix="capt-integration-", dir=build.ARTIFACTS)
        cls.work = Path(cls.temp.name)
        cls.root = cls.work / "root with spaces"
        shutil.copytree(SOURCE, cls.root, symlinks=True)
        cls.helper = cls.work / "capt-patch"
        shutil.copy2(PROJECT / "package/capt-patch", cls.helper)
        build.write_runtime_manifest(SOURCE, cls.work / "runtime.sha256")
        cls.initial_hashes = {p.relative_to(SOURCE): build.digest(p) for p in SOURCE.rglob("*") if p.is_file()}
        result = run(cls.helper, "apply", cls.root, timeout=60)
        if result.returncode:
            cls.temp.cleanup()
            raise RuntimeError(result.stdout + result.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_only_device_match_changes_and_instructions_preserved(self):
        original = (SOURCE / BASE / "Bidi/captmoncnab3").read_bytes()
        patched = (self.root / BASE / "Bidi/captmonlbp2900").read_bytes()
        self.assertEqual(original.count(b"\0MDL:LBP3000;\0"), 2)
        self.assertEqual(patched.count(b"\0MDL:LBP2900;\0"), 2)
        self.assertNotIn(b"\0MDL:LBP3000;\0", patched)
        self.assertEqual(patched.count(b"Canon LBP3000\0"), original.count(b"Canon LBP3000\0"))
        before, after = text_sections(original), text_sections(patched)
        self.assertEqual(set(before), {0x1000007, 0x100000C})
        self.assertEqual(before, after)
        self.assertEqual(run("codesign", "--verify", "--strict", "--all-architectures", self.root / BASE / "Bidi/captmonlbp2900").returncode, 0)

    def test_original_runtime_and_utility_are_byte_identical(self):
        for relative, expected in self.initial_hashes.items():
            self.assertEqual(build.digest(self.root / relative), expected, str(relative))

    def test_print_options_and_canon_utility_contract_preserved(self):
        before = gzip.decompress((SOURCE / PPDS / "CNMC2LBP3000AUK.ppd.gz").read_bytes()).decode()
        after = gzip.decompress((self.root / PPDS / "CNMC2LBP2900AUK.ppd.gz").read_bytes()).decode()
        changed = ("*ModelName:", "*NickName:", "*ShortNickName:", "*PCFileName:", "*Product:", "*Throughput:", "*opbidiPlugin:")
        self.assertEqual([s for s in before.splitlines() if not s.startswith(changed)],
                         [s for s in after.splitlines() if not s.startswith(changed)])
        for contract in ("*APPrinterUtilityPath:", "*APDialogExtension:", "*ccpdReady:", '*CNPrinterName: "Canon LBP3000"'):
            self.assertIn(contract, after)

    def test_real_native_filter_a4_letter_and_multipage(self):
        # Canon's launcher splits CNDriverRootPath on spaces. Its installed path
        # has none; render from the pristine extraction, while patch apply/remove
        # are independently exercised in a root containing spaces.
        base = SOURCE / BASE
        output_dir = build.ARTIFACTS / "verification"
        output_dir.mkdir(exist_ok=True)
        cases = (
            ("a4-1-page", 1, 595.276, 841.89, 1, "PageSize=A4"),
            ("letter-1-page", 1, 612, 792, 1, "PageSize=Letter"),
            ("a4-3-page", 3, 595.276, 841.89, 1, "PageSize=A4"),
            ("a4-toner-options", 1, 595.276, 841.89, 1,
             "PageSize=A4 CNTonerSaving=True CNTonerDensity=1 CNHalftone=pattern2 MediaType=HEAVY"),
            # Canon reads the macOS print-ticket copy count, not argv[4] alone.
            ("a4-copies-2", 1, 595.276, 841.89, 2,
             "PageSize=A4 Collate=True com.apple.print.PrintSettings.PMCopies..n.=2"),
        )
        rendered = {}
        for key, pages, width, height, copies, options in cases:
            document = output_dir / f"{key}.pdf"
            document.write_bytes(pdf(pages, width, height))
            outputs = []
            for variant in ("3000", "2900"):
                content = gzip.decompress((self.root / PPDS / f"CNMC2LBP{variant}AUK.ppd.gz").read_bytes())
                content = content.replace(b'*CNDriverRootPath: "/Library/Printers/Canon/CUPSCAPT2"', f'*CNDriverRootPath: "{base}"'.encode())
                ppd = self.work / f"{variant}.ppd"
                ppd.write_bytes(content)
                env = dict(os.environ, PPD=str(ppd), DYLD_LIBRARY_PATH=str(base / "Libs"))
                env.pop("PRINTER", None)  # Standalone render; no daemon or printer connection.
                result = subprocess.run([str(base / "Bins/capdftopdl"), "1", "test", "Native CAPT test", str(copies), options, str(document)], env=env, capture_output=True, timeout=30)
                (output_dir / f"{key}-{variant}.log").write_bytes(result.stderr)
                self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
                self.assertGreater(len(result.stdout), 1024)
                self.assertNotIn(b"execv() error", result.stderr)
                self.assertNotIn(b"STATE: +com.canon.unsupportedsize-error", result.stderr)
                outputs.append(result.stdout)
            self.assertEqual(outputs[0], outputs[1], f"Native rendered output changed for {key}")
            rendered[key] = outputs[1]
        for key in ("a4-toner-options", "a4-copies-2"):
            self.assertTrue(rendered[key] != rendered["a4-1-page"], f"Options had no effect: {key}")

    def test_unknown_canon_source_is_rejected_before_mutation(self):
        source = self.root / BASE / "Bidi/captmoncnab3"
        original = source.read_bytes()
        installed = build.digest(self.root / BASE / "Bidi/captmonlbp2900")
        try:
            source.write_bytes(original + b"changed")
            result = run(self.helper, "apply", self.root, timeout=30)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(build.digest(self.root / BASE / "Bidi/captmonlbp2900"), installed)
        finally:
            source.write_bytes(original)

    def test_modified_patch_is_not_overwritten_or_removed(self):
        monitor = self.root / BASE / "Bidi/captmonlbp2900"
        original = monitor.read_bytes()
        foreign = original + b"user change"
        try:
            monitor.write_bytes(foreign)
            for command in ("apply", "remove"):
                result = run(self.helper, command, self.root, timeout=30)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(monitor.read_bytes(), foreign)
        finally:
            monitor.write_bytes(original)

    @unittest.skipIf(os.geteuid() == 0, "Permission-failure check requires an unprivileged user")
    def test_failed_publish_restores_previous_pair(self):
        directory = self.root / PPDS
        paths = (self.root / BASE / "Bidi/captmonlbp2900", directory / "CNMC2LBP2900AUK.ppd.gz",
                 self.root / build.SUPPORT / "installed.sha256")
        before = [p.read_bytes() for p in paths]
        mode = directory.stat().st_mode & 0o777
        try:
            directory.chmod(0o555)
            result = run(self.helper, "apply", self.root, timeout=60)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual([p.read_bytes() for p in paths], before)
        finally:
            directory.chmod(mode)
        self.assertFalse((self.root / build.SUPPORT / "apply.lock").exists())

    def test_missing_native_source_does_not_create_output(self):
        missing = self.work / "no-driver"
        missing.mkdir()
        result = run(self.helper, "apply", missing, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(missing.iterdir()), [])

    def test_reapply_and_remove_preserve_originals(self):
        result = run(self.helper, "apply", self.root, timeout=60,
                     env=dict(os.environ, LANG="vi_VN.UTF-8", LC_ALL="vi_VN.UTF-8"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = run(self.helper, "remove", self.root, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.root / BASE / "Bidi/captmonlbp2900").exists())
        self.assertFalse((self.root / PPDS / "CNMC2LBP2900AUK.ppd.gz").exists())
        for relative, expected in self.initial_hashes.items():
            self.assertEqual(build.digest(self.root / relative), expected)
        # Leave the shared test root installed for the remaining tests.
        result = run(self.helper, "apply", self.root, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
