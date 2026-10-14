#!/usr/bin/env python3
"""Check the private Moo Mesa SD tree or ZIP against APF packaging contracts.

Scope: identities, required definition files/field limits, referenced files,
loader slots, firmware floor, case-sensitive paths, integrity and manifest.
This is not a firmware emulator and cannot establish hardware gameplay.
"""
import argparse
import hashlib
import itertools
import json
import pathlib
import re
import zipfile

from apf_packaging import validate_bitstream_filename, validate_core_folder_identity


def audit(path, *, rom_free_manifest=None):
    issues, files, names = [], {}, []
    if path.is_file():
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if archive.testzip() is not None:
                issues.append('ZIP CRC failure')
            for entry in archive.infolist():
                if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                    issues.append(f'Symlink ZIP entry: {entry.filename}')
                if not entry.is_dir():
                    files[entry.filename] = archive.read(entry)
    else:
        for entry in sorted(path.rglob('*')):
            name = entry.relative_to(path).as_posix()
            names.append(name)
            if entry.is_symlink():
                issues.append(f'Symlink SD entry: {name}')
            elif entry.is_file():
                files[name] = entry.read_bytes()
    if len(names) != len(set(names)):
        issues.append('Duplicate archive paths')
    if len(names) != len({name.rstrip('/').casefold() for name in names}):
        issues.append('Case-insensitive duplicate paths')
    for name in names:
        pure = pathlib.PurePosixPath(name)
        if pure.is_absolute() or '..' in pure.parts or '\\' in name:
            issues.append(f'Unsafe package path: {name}')
        if len(pure.parts) > 1 or name.endswith('/'):
            if pure.parts[0] not in {'Cores', 'Platforms', 'Assets', 'Presets'}:
                issues.append(f'Unexpected SD root directory: {pure.parts[0]}')
    for root in ['Cores', 'Platforms', 'Assets']:
        if not any(name.startswith(root+'/') for name in files):
            issues.append(f'Missing exact-case SD root: {root}')

    def require(condition, message):
        if not condition:
            issues.append(message)

    def guard(function, *args):
        try:
            function(*args)
        except SystemExit as exc:
            issues.append(str(exc))

    def document(name, top):
        if name not in files:
            issues.append(f'Missing exact-case dependency: {name}')
            return {}
        value = json.loads(files[name])
        require(set(value) == {top}, f'{name}: expected {top} root')
        return value[top]

    def number(value):
        return int(value, 0) if isinstance(value, str) else int(value)

    core_paths = [name for name in files if re.fullmatch(r'Cores/[^/]+/core.json', name)]
    require(len(core_paths) == 1, 'Expected exactly one directly installed core')
    if len(core_paths) != 1:
        return {'passed': False, 'issues': sorted(set(issues))}
    core_path = core_paths[0]
    core_id = core_path.split('/')[1]
    base = f'Cores/{core_id}/'
    definitions = {}
    for top in ['core', 'audio', 'data', 'input', 'interact', 'variants', 'video']:
        definitions[top] = document(base+top+'.json', top)
        require(definitions[top].get('magic') == 'APF_VER_1', f'{top}.json: invalid magic')
    core = definitions['core']
    metadata = core['metadata']
    guard(validate_core_folder_identity, core_id, {'core': core})
    for key, maximum in [('author', 31), ('shortname', 31), ('description', 63),
                         ('url', 63), ('version', 31), ('date_release', 10)]:
        value = metadata[key]
        require(isinstance(value, str) and len(value) <= maximum,
                f'core.metadata.{key}: field exceeds {maximum} characters')
    require(bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}', metadata['date_release'])), 'Invalid release date')
    platform_ids = metadata['platform_ids']
    require(platform_ids in [['moomesa_test'], ['moo_bucky_test'], ['moobucky']], 'Unexpected private platform IDs')
    for platform_id in platform_ids:
        require(bool(re.fullmatch(r'[a-z0-9][a-z0-9_]{0,14}', platform_id)), 'Invalid platform identifier')
        platform = document(f'Platforms/{platform_id}.json', 'platform')
        for key in ['category', 'name', 'manufacturer']:
            require(isinstance(platform[key], str) and len(platform[key]) <= 31,
                    f'platform.{key}: field exceeds 31 characters')
        require(isinstance(platform['year'], int), 'Platform year must be an integer')
        require(f'Platforms/_images/{platform_id}.bin' in files, 'Missing exact-case platform image')
    framework = core['framework']
    require(framework['target_product'] == 'Analogue Pocket', 'Incorrect target product')
    require(framework['dock']['supported'] is True, 'Dock supported must be true')
    minimum = tuple(map(int, framework['version_required'].split('.')))
    if definitions['video'].get('display_modes'):
        require(minimum >= (2, 0), 'video.display_modes requires declared firmware >=2.0')
    if framework.get('chip32_vm'):
        vm = framework['chip32_vm']
        require(len(vm) <= 15 and pathlib.PurePosixPath(vm).name == vm and base+vm in files,
                'Missing or invalid Chip32 dependency')
    bitstreams = core['cores']
    require(1 <= len(bitstreams) <= 8, 'Invalid bitstream count')
    require(len({number(item['id']) for item in bitstreams}) == len(bitstreams), 'Duplicate bitstream IDs')
    for item in bitstreams:
        guard(validate_bitstream_filename, item['filename'])
        require(base+item['filename'] in files and bool(files.get(base+item['filename'])),
                'Missing/empty exact-case bitstream reference')
        require(len(item.get('name', '')) <= 15, 'Bitstream name exceeds 15 characters')
    require({name for name in files if name.endswith('.rbf_r')} ==
            {base+item['filename'] for item in bitstreams}, 'Unreferenced bitstream file')
    slots = definitions['data']['data_slots']
    if platform_ids in [['moo_bucky_test'], ['moobucky']]:
        if platform_ids == ['moobucky']:
            require(core_id == 'mmmax4.moobucky', 'Unexpected moobucky author/core identity')
        require([number(slot['id']) for slot in slots] == [0, 1, 2], 'Expected selector/ROM/EEPROM slots 0/1/2')
        selector, rom_slot, save_slot = slots
        require(selector['required'] is True and number(selector['parameters']) == 0x113 and
                selector['extensions'] == ['json'] and selector['address'] == '', 'Invalid game selector')
        require(rom_slot['required'] is True and number(rom_slot['parameters']) == 0x10a and
                number(rom_slot['address']) == 0 and rom_slot['extensions'] == ['rom'], 'Invalid ROM slot')
        require(save_slot['required'] is False and save_slot['nonvolatile'] is True and
                number(save_slot['parameters']) == 32 and number(save_slot['address']) == 0x20000000 and
                number(save_slot['size_maximum']) == 128 and save_slot['extensions'] == ['sav'], 'Invalid EEPROM slot')
        # A ROM-free release supplies its external-ROM contract in memory;
        # private packages retain their original embedded manifest and hashes.
        manifest = rom_free_manifest if rom_free_manifest is not None else json.loads(files['TEST_MANIFEST.json'])
        require(manifest['layout'] == 'dual_eab_instances' and manifest['core_id'] == core_id and
                manifest['platform_id'] == platform_ids[0], 'Manifest identity mismatch')
        require(manifest['firmware_minimum'] == framework['version_required'], 'Manifest firmware mismatch')
        if 'marquee_sha256' in manifest:
            marquee = files[f'Platforms/_images/{platform_ids[0]}.bin']
            require(len(marquee) == 521 * 165 * 2 and not any(marquee[1::2]),
                    'Invalid Pocket platform marquee format')
            require(hashlib.sha256(marquee).hexdigest() == manifest['marquee_sha256'],
                    'Manifest marquee hash mismatch')
        require(len(bitstreams) == 1, 'Both games must use one bitstream')
        bitstream_path = base + bitstreams[0]['filename']
        require(hashlib.sha256(files[bitstream_path]).hexdigest() == manifest['pocket_bitstream_sha256'],
                'Manifest bitstream hash mismatch')
        instances = [name for name in files if name.startswith(f'Assets/{platform_ids[0]}/{core_id}/') and name.endswith('.json')]
        require(len(instances) == 2, 'Expected exactly two game instances')
        seen_games, seen_saves = set(), set()
        for name in instances:
            instance = document(name, 'instance')
            require(instance['magic'] == 'APF_VER_1' and instance['data_path'] == '', 'Invalid instance root/path')
            require(instance['core_select'] == {'id': 0, 'select': False}, 'Invalid instance core selection')
            require(instance.get('memory_writes', []) == [], 'Unexpected game memory writes')
            instance_slots = instance['data_slots']
            require([number(slot['id']) for slot in instance_slots] == [1, 2], 'Invalid instance ROM/save slots')
            rom_name, save_name = [slot['filename'] for slot in instance_slots]
            require(all(pathlib.PurePosixPath(filename).name == filename and len(filename) <= 31
                        for filename in [rom_name, save_name]), 'Invalid instance filenames')
            game = pathlib.PurePosixPath(rom_name).stem
            require(game in {'moomesa', 'bucky'} and save_name == game+'.sav', 'Wrong game/save pairing')
            seen_games.add(game); seen_saves.add(save_name)
            rom_path = f'Assets/{platform_ids[0]}/{core_id}/{rom_name}'
            if rom_free_manifest is not None:
                require(rom_path not in files, 'ROM-free release contains game ROM: ' + game)
            else:
                require(hashlib.sha256(files[rom_path]).hexdigest() == manifest['games'][game]['rom_sha256'],
                        f'Manifest ROM hash mismatch: {game}')
                require(len(files[rom_path]) == manifest['games'][game]['rom_bytes'], 'ROM size mismatch')
            preset_path = f'Presets/{core_id}/Interact/' + name[len('Assets/'):]
            preset = document(preset_path, 'interact')
            require(preset == definitions['interact'], 'Per-game DIP menu differs from core menu')
        require(seen_games == {'moomesa', 'bucky'} and len(seen_saves) == 2, 'Game assets/saves must be separate')
        require(not any(name.endswith('.sav') for name in files), 'Package must not install saves')
        variables = definitions['interact']['variables']
        require(len({item['id'] for item in variables}) == len(variables), 'Duplicate menu IDs')
        dips = [item for item in variables if number(item.get('address', 0)) == 0xf1000000]
        dip_layout = manifest.get('dip_menu_layout', 'packed_combinations')
        if dip_layout == 'independent_fields':
            expected = [
                ('DIP: Sound', 10, 0xfffffffe, [('Stereo', 0), ('Mono', 1)]),
                ('DIP: Coins', 11, 0xfffffffd, [('Common', 0), ('Independent', 2)]),
                ('DIP: Players', 12, 0xfffffff3, [('4 Players', 0), ('2 Players', 4), ('3 Players', 12)]),
            ]
            require(len(dips) == 3, 'Expected three independent DIP fields')
            for item, (name, ident, mask, options) in zip(dips, expected):
                require(item.get('name') == name and item.get('id') == ident and
                        item.get('type') == 'list' and item.get('enabled') is True and
                        item.get('persist') is True and item.get('defaultval') == 0 and
                        number(item.get('mask', 0)) == mask and
                        [(option['name'], number(option['value'])) for option in item['options']] == options,
                        f'Invalid independent DIP field: {name}')
            # Exercise field updates from every old/new hardware combination,
            # in every write order, while retaining the upper register bits.
            if len(dips) == 3:
                masks = [number(item['mask']) for item in dips]
                choices = [[number(option['value']) for option in item['options']] for item in dips]
                combinations = list(itertools.product(*choices))
                encoded = {sound | coins | players for sound, coins, players in combinations}
                require(encoded == {0, 1, 2, 3, 4, 5, 6, 7, 12, 13, 14, 15},
                        'Independent DIP choices do not cover the 12 hardware combinations')
                for old in encoded:
                    for values in combinations:
                        for order in itertools.permutations(range(3)):
                            register = 0xa5a5a5a0 | old
                            for index in order:
                                register = (register & masks[index]) | values[index]
                            require(register == (0xa5a5a5a0 | values[0] | values[1] | values[2]),
                                    'DIP field writes corrupt another setting or depend on write order')
        else:
            require(dip_layout == 'packed_combinations', 'Unknown DIP menu layout')
            require(len(dips) == 1 and dips[0].get('name') == 'DIP Switches' and
                    len(dips[0]['options']) == 12 and number(dips[0]['mask']) == 0xfffffff0 and
                    {number(option['value']) for option in dips[0]['options']} ==
                    {0, 1, 2, 3, 4, 5, 6, 7, 12, 13, 14, 15}, 'Missing packed DIP menu')
        cabinet_layout = manifest.get('cabinet_buttons_layout')
        if cabinet_layout is not None:
            require(cabinet_layout == 'optional_p1_selectors', 'Unknown cabinet button layout')
            controllers = definitions['input']['controllers']
            require(len(controllers) == 1 and controllers[0].get('type') == 'default',
                    'Unexpected controller declaration')
            mappings = controllers[0]['mappings']
            require(len(mappings) == 6 and len({item['id'] for item in mappings}) == 6,
                    'Expected six original gameplay control mappings')
            require(mappings == [
                {'id': 200, 'name': 'Jump', 'key': 'pad_btn_a'},
                {'id': 201, 'name': 'Shoot', 'key': 'pad_btn_b'},
                {'id': 202, 'name': 'Jump (alt)', 'key': 'pad_btn_y'},
                {'id': 203, 'name': 'Bucky B3 / Moo alt', 'key': 'pad_btn_x'},
                {'id': 204, 'name': 'Coin', 'key': 'pad_btn_select'},
                {'id': 205, 'name': 'Start', 'key': 'pad_btn_start'},
            ], 'Changed original gameplay controls')
            require(not any(name.startswith(f'Presets/{core_id}/Input/') for name in files),
                    'Unexpected per-asset Input override')
            labels = ['Unassigned', 'A', 'B', 'X', 'Y', 'L', 'R', 'Select', 'Start']
            for name, ident, shift in [('Test Button', 41, 16), ('Service Button', 42, 20)]:
                fields = [item for item in variables if item.get('id') == ident]
                require(len(fields) == 1, f'Missing optional {name}')
                if len(fields) == 1:
                    item = fields[0]
                    require(item.get('name') == name and item.get('type') == 'list' and
                            item.get('enabled') is True and item.get('persist') is True and
                            item.get('defaultval') == 0 and number(item.get('address', 0)) == 0xf2000000 and
                            number(item.get('mask', 0)) == (0xffffffff ^ (15 << shift)) and
                            [(option['name'], number(option['value'])) for option in item['options']] ==
                            [(label, index << shift) for index, label in enumerate(labels)],
                            f'Invalid optional {name}: defaults, keys or preserve mask')
            manual = [item for item in variables if item.get('id') == 40]
            require(len(manual) == 1 and manual[0].get('name') == 'Test Switch (hold)' and
                    manual[0].get('persist') is False and manual[0].get('defaultval') == 0 and
                    number(manual[0].get('address', 0)) == 0xf2000000 and
                    number(manual[0].get('mask', 0)) == 0xfffffeff and
                    number(manual[0].get('value', 0)) == 0x100, 'Incorrect manual Test fallback')
        require(manifest['private_only'] is True and manifest['hardware_gameplay_verified'] is False,
                'Incorrect private/hardware status')
        return {'passed': not issues, 'issues': sorted(set(issues)), 'core_id': core_id,
                'platform_id': platform_ids[0], 'firmware_minimum': framework['version_required'],
                'bitstream_filename': bitstreams[0]['filename'], 'games': sorted(seen_games),
                'bitstream_filename_characters': len(bitstreams[0]['filename']), 'files': len(files),
                'dip_menu_layout': dip_layout,
                'cabinet_buttons_layout': cabinet_layout,
                'scope': 'Static dual-game APF contracts and hashes; no hardware gameplay assertion'}
    require([number(slot['id']) for slot in slots] == [0, 1], 'Expected ROM slot 0 and EEPROM slot 1')
    rom_slot, save_slot = slots
    for slot in slots:
        require(len(slot['name']) <= 15 and len(slot['filename']) <= 31, 'Data slot field too long')
        require(pathlib.PurePosixPath(slot['filename']).name == slot['filename'], 'Data slot filename must be plain')
    require(rom_slot['required'] is True and number(rom_slot['parameters']) == 8 and
            number(rom_slot['address']) == 0 and rom_slot['filename'] == 'moomesa.rom' and
            rom_slot['extensions'] == ['rom'],
            'ROM slot differs from upstream loader contract')
    require(save_slot['required'] is False and save_slot['nonvolatile'] is True and
            number(save_slot['parameters']) == 32 and number(save_slot['address']) == 0x20000000 and
            number(save_slot['size_maximum']) == 128 and save_slot['filename'] == 'moomesa_test.sav' and
            save_slot['extensions'] == ['sav'],
            'EEPROM slot differs from upstream save contract')
    rom_path = f'Assets/{platform_ids[0]}/common/{rom_slot["filename"]}'
    manifest = json.loads(files['TEST_MANIFEST.json'])
    require(manifest['core_id'] == core_id and manifest['platform_id'] == platform_ids[0], 'Manifest identity mismatch')
    if 'firmware_minimum' in manifest:
        require(manifest['firmware_minimum'] == framework['version_required'], 'Manifest firmware mismatch')
    for filename, field in [(base+bitstreams[0]['filename'], 'pocket_bitstream_sha256'), (rom_path, 'rom_sha256')]:
        require(hashlib.sha256(files[filename]).hexdigest() == manifest[field], f'Manifest hash mismatch: {filename}')
    require(manifest['private_only'] is True and manifest['hardware_gameplay_verified'] is False,
            'Incorrect private/hardware verification status')
    return {'passed': not issues, 'issues': sorted(set(issues)), 'core_id': core_id,
            'platform_id': platform_ids[0], 'firmware_minimum': framework['version_required'],
            'bitstream_filename': bitstreams[0]['filename'],
            'bitstream_filename_characters': len(bitstreams[0]['filename']), 'files': len(files),
            'scope': 'Static APF packaging contracts and integrity; physical load/gameplay pending'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=pathlib.Path)
    parser.add_argument('--report', type=pathlib.Path)
    args = parser.parse_args()
    try:
        result = audit(args.package)
    except (KeyError, TypeError, ValueError, OSError, zipfile.BadZipFile) as exc:
        result = {'passed': False, 'issues': [f'Malformed or missing package dependency: {exc}']}
    if args.report:
        args.report.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['passed'] else 1)
