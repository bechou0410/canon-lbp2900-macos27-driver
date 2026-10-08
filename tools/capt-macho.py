"""Length-preserving, preimage-guarded relocation of the pinned Canon binaries."""
import hashlib
import struct

PORTS = {59687: 59290, 59787: 59390}
REPLACEMENTS = (
    (b"CUPSCAPT2", b"LBP2900RT"),
    # BackGrounder compares the older folder prefix when choosing its ports/cache.
    (b"/Canon/CUPSCAPT", b"/Canon/LBP2900R"),
    (b"cnbma2", b"lb29u2"),
    (b"localhost:59687", b"localhost:59290"),
    (b"Canon CAPT BackGrounder", b"Canon 2900 BackGrounder"),
    (b"jp.co.canon.ColorGearCMMC", b"jp.co.canon.Color2900CMMC"),
    (b"/var/ccpd/fifo0", b"/var/lb29/fifo0"),
    # Native error auto-open notifications must not reach Canon's BackGrounder.
    (b"\0capt\0", b"\0lb29\0"),
)


def slices(data):
    if data[:4] != b"\xca\xfe\xba\xbe":
        raise ValueError("Expected a universal Mach-O")
    for i in range(struct.unpack_from(">I", data, 4)[0]):
        cpu, _, offset, size, _ = struct.unpack_from(">IIIII", data, 8 + i * 20)
        yield {0x1000007: "x86_64", 0x100000C: "arm64"}[cpu], offset, size


def segments(data, offset):
    cursor = offset + 32
    for _ in range(struct.unpack_from("<I", data, offset + 16)[0]):
        cmd, size = struct.unpack_from("<II", data, cursor)
        if cmd == 0x19:
            name = data[cursor + 8:cursor + 24].rstrip(b"\0")
            address, _, start, length = struct.unpack_from("<QQQQ", data, cursor + 24)
            yield name, address, offset + start, length
        cursor += size


def file_offset(data, arch, address):
    for name, offset, _ in slices(data):
        if name == arch:
            for _, base, start, length in segments(data, offset):
                if base <= address < base + length:
                    return start + address - base
    raise ValueError(f"Unmapped {arch} address {address:x}")


def text_sections(data):
    result = {}
    for arch, offset, _ in slices(data):
        cursor = offset + 32
        for _ in range(struct.unpack_from("<I", data, offset + 16)[0]):
            cmd, size = struct.unpack_from("<II", data, cursor)
            if cmd == 0x19:
                for i in range(struct.unpack_from("<I", data, cursor + 64)[0]):
                    section = cursor + 72 + i * 80
                    if data[section:section + 16].rstrip(b"\0") == b"__text":
                        _, length, start = struct.unpack_from("<QQI", data, section + 32)
                        result[arch] = data[offset + start:offset + start + length]
            cursor += size
    return result


def redirect_dependencies(data, replacements):
    """Change only existing LC_LOAD_DYLIB names, within their allocated space."""
    mutable = bytearray(data)
    changes = []
    for arch, offset, _ in slices(data):
        found = set()
        cursor = offset + 32
        for _ in range(struct.unpack_from("<I", data, offset + 16)[0]):
            command, size = struct.unpack_from("<II", data, cursor)
            if command == 0xc:
                start = cursor + struct.unpack_from("<I", data, cursor + 8)[0]
                end = data.index(b"\0", start, cursor + size)
                name = data[start:end].decode()
                if name in replacements:
                    if name in found:
                        raise ValueError("Duplicate dependency to redirect")
                    after = replacements[name].encode() + b"\0"
                    before = data[start:cursor + size]
                    if len(after) > len(before) or any(data[end:cursor + size]):
                        raise ValueError("Dependency does not fit existing load command")
                    after = after.ljust(len(before), b"\0")
                    mutable[start:cursor + size] = after
                    changes.append({"offset": start, "before": before.hex(), "after": after.hex(),
                                    "kind": "dependency", "arch": arch})
                    found.add(name)
            cursor += size
        if found != set(replacements):
            raise ValueError(f"Missing dependency in {arch}")
    return bytes(mutable), changes


def relocate(data, patch, monitor=False):
    original = data
    changes = []
    if not patch or hashlib.sha256(data).hexdigest() != patch["sha256"]:
        raise ValueError("Unexpected Canon binary for relocation")
    if sorted(arch for arch, _, _ in slices(data)) != ["arm64", "x86_64"]:
        raise ValueError("Expected exactly one arm64 and one x86_64 slice")
    if patch["instructions"]:
        mutable = bytearray(data)
        for instruction in patch["instructions"]:
            arch = instruction["arch"]
            start = file_offset(data, arch, int(instruction["address"], 16))
            before = bytes.fromhex(instruction["before"])
            if data[start:start + len(before)] != before:
                raise ValueError(f"Instruction preimage mismatch at {start:x}")
            old = instruction["port"]
            if arch == "arm64":
                opcode = int.from_bytes(before, "little")
                if (opcode >> 5) & 0xffff != old:
                    raise ValueError("Unexpected ARM immediate")
                after = ((opcode & ~(0xffff << 5)) | PORTS[old] << 5).to_bytes(4, "little")
            else:
                if before[-4:] != old.to_bytes(4, "little"):
                    raise ValueError("Unexpected x86 immediate")
                after = before[:-4] + PORTS[old].to_bytes(4, "little")
            mutable[start:start + len(before)] = after
            changes.append({"offset": start, "before": before.hex(), "after": after.hex(), "kind": "port",
                            "arch": arch, "address": instruction["address"]})
        data = bytes(mutable)
    data, dependencies = redirect_dependencies(data, patch.get("dependencies", {}))
    changes.extend(dependencies)
    expected_code = text_sections(data)
    if monitor:
        if data.count(b"\0MDL:LBP3000;\0") != 2:
            raise ValueError("Unexpected device matcher count")
        replacements = REPLACEMENTS + ((b"\0MDL:LBP3000;\0", b"\0MDL:LBP2900;\0"),)
    else:
        replacements = REPLACEMENTS
    counts = {}
    for before, after in replacements:
        if len(before) != len(after):
            raise ValueError("Relocation must preserve string length")
        count = data.count(before)
        if count:
            counts[before.decode()] = count
        if count != patch["strings"].get(before.decode(), 0):
            raise ValueError(f"Unexpected replacement count for {before!r}")
        start = 0
        while (start := data.find(before, start)) >= 0:
            changes.append({"offset": start, "before": before.hex(), "after": after.hex(), "kind": "string"})
            start += len(before)
        data = data.replace(before, after)
    if counts != patch["strings"]:
        raise ValueError("Declared string replacements were not all applied")
    if len(data) != len(original):
        raise ValueError("Relocation changed executable size")
    if text_sections(data) != expected_code:
        raise ValueError("A string replacement unexpectedly touched machine instructions")
    return data, changes
