#!/usr/bin/env python3
"""Build/check the private Bucky World EAB image; never accept EA by label.

The MRA builder is reused. An independent lane reconstruction, member length,
CRC32 and SHA1 checks gate every output. No Bucky bitstream is packaged here.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'core/tools'))
import mra_build


def select_members(parts, mapping):
    selected = {}
    for member in mapping['members']:
        matches = [data for _, _, data in parts
                   if len(data) == member['size']
                   and f'{zlib.crc32(data) & 0xffffffff:08x}' == member['crc32']
                   and hashlib.sha1(data).hexdigest() == member['sha1']]
        if not matches:
            raise ValueError(f"Missing or wrong World EAB member: {member['name']}")
        selected[member['name']] = matches[0]
    return selected


def reconstruct(selected, mapping):
    image = bytearray([0xff]) * mapping['image_size']
    for member in mapping['members']:
        data = selected[member['name']]
        base = member['image_offset']
        stride, unit = member['stride'], member['unit']
        for lane in range(unit):
            stop = base + lane + (len(data) // unit) * stride
            image[base + lane:stop:stride] = data[lane::unit]
    return bytes(image)


def validate_destination(path):
    path = path.resolve()
    if (ROOT / 'private').resolve() not in path.parents:
        raise ValueError('ROM output must stay in the ignored private/ directory')
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--verify-image', type=Path)
    parser.add_argument('--evidence', type=Path)
    args = parser.parse_args()
    mapping = json.loads((ROOT / 'evidence/bucky-rom-map.json').read_text())
    output = validate_destination(args.output) if args.output else None
    for path in (output, args.evidence):
        if path and path.exists():
            raise ValueError(f'Output already exists: {path}')
    selected = select_members(mra_build.load_parts(args.archive), mapping)
    expected = reconstruct(selected, mapping)
    image, md5 = mra_build.build(ROOT / 'core/bucky.mra', args.archive)
    if image != expected:
        raise ValueError('MRA image differs from independent MAME lane mapping')
    if args.verify_image and args.verify_image.read_bytes() != expected:
        raise ValueError('Existing image differs from verified World EAB mapping')
    report = {
        'set': 'bucky', 'revision': 'World EAB', 'passed': True,
        'mapping_sha256': hashlib.sha256((ROOT / 'evidence/bucky-rom-map.json').read_bytes()).hexdigest(),
        'recipe_sha256': hashlib.sha256((ROOT / 'core/bucky.mra').read_bytes()).hexdigest(),
        'archive_sha256': hashlib.sha256(args.archive.read_bytes()).hexdigest() if args.archive.is_file() else None,
        'members_checked': len(selected), 'image_size': len(image),
        'image_md5': md5, 'image_sha256': hashlib.sha256(image).hexdigest(),
        'regions': [dict(region, sha256=hashlib.sha256(
            image[region['offset']:region['offset'] + region['size']]).hexdigest())
            for region in mapping['regions']],
    }
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(image)
    if args.evidence:
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        raise SystemExit(str(error))
