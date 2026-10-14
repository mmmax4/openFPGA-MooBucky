#!/usr/bin/env python3
"""Create a local ROM-free SD ZIP after all-corner qualification; no upload."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile

from check_apf_package import audit

ROOT = Path(__file__).resolve().parents[1]
CORE_ID = 'mmmax4.moobucky'
TITLES = ['Bucky EAB.json', 'Moo Mesa EAB.json']


def validate(files, bitstream_filename, bitstream_sha256):
    base = f'Cores/{CORE_ID}/'
    assets = f'Assets/moobucky/{CORE_ID}/'
    presets = f'Presets/{CORE_ID}/Interact/moobucky/{CORE_ID}/'
    expected = {base + name for name in ['core.json', 'audio.json', 'data.json',
        'input.json', 'interact.json', 'variants.json', 'video.json', 'info.txt',
        'icon.bin', bitstream_filename]}
    expected |= {'Platforms/moobucky.json', 'Platforms/_images/moobucky.bin'}
    expected |= {prefix + title for prefix in [assets, presets] for title in TITLES}
    if set(files) != expected:
        raise SystemExit('Unexpected SD payload/dependency: ' + repr(sorted(set(files) ^ expected)))
    contract = {'layout': 'dual_eab_instances', 'core_id': CORE_ID,
        'platform_id': 'moobucky', 'firmware_minimum': '2.0',
        'dip_menu_layout': 'independent_fields', 
        'marquee_sha256': '323c67ed8eb5dfeb92be99c3ed23eacdb92a769e727dfe95629788db2082c471',
        'pocket_bitstream_sha256': bitstream_sha256,
        'private_only': True, 'hardware_gameplay_verified': False}
    # Validation flags describe this local check, not a hardware certificate.
    with tempfile.TemporaryDirectory(prefix='release-audit-', dir=ROOT / 'build') as directory:
        tree = Path(directory)
        for name, data in files.items():
            target = tree / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        result = audit(tree, rom_free_manifest=contract)
    if not result['passed']:
        raise SystemExit('APF contract failure: ' + '; '.join(result['issues']))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('build/mmmax4.moobucky.zip'))
    args = parser.parse_args()
    destination = (ROOT / args.output).resolve()
    if (ROOT / 'build').resolve() not in destination.parents or destination.exists():
        raise SystemExit('Choose a fresh output inside build/')
    report = 'build/release-qualification.json'
    subprocess.run(['python3', 'scripts/qualify_build.py', '--report', report], cwd=ROOT, check=True)
    qualification = json.loads((ROOT / report).read_text())
    raw = ROOT / 'core/projects/output_files/moomesa_pocket.rbf'
    if hashlib.sha256(raw.read_bytes()).hexdigest() != qualification['rbf_sha256']:
        raise SystemExit('Qualified RBF changed')
    files = {path.relative_to(ROOT / 'pkg').as_posix(): path.read_bytes()
             for path in (ROOT / 'pkg').rglob('*') if path.is_file()}
    if any(path.is_symlink() for path in (ROOT / 'pkg').rglob('*')):
        raise SystemExit('Symlink package dependency')
    core = json.loads(files['Cores/mmmax4.moobucky/core.json'])['core']
    if core['metadata']['author'] != 'mmmax4' or core['metadata']['shortname'] != 'moobucky':
        raise SystemExit('Unexpected core identity')
    filename = core['cores'][0]['filename']
    if len(filename) > 15 or Path(filename).name != filename or not filename.endswith('.rbf_r'):
        raise SystemExit('Invalid Pocket bitstream filename')
    reversed_bits = bytes(int(f'{value:08b}'[::-1], 2) for value in range(256))
    files['Cores/mmmax4.moobucky/' + filename] = raw.read_bytes().translate(reversed_bits)
    destination.parent.mkdir(parents=True, exist_ok=True)
    validate(files, filename, hashlib.sha256(files['Cores/mmmax4.moobucky/' + filename]).hexdigest())
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            archive.writestr(name, data)
    print(hashlib.sha256(destination.read_bytes()).hexdigest() + '  ' + str(destination))
    print('See LICENSING.md for applicable terms.')


if __name__ == '__main__':
    main()
