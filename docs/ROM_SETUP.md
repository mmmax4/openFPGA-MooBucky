# Build your own ROM images

Only World parent **ver EAB** sets are qualified. Supply your own MAME
`moomesa.zip` and `bucky.zip`; the project distributes no ROMs or download links.

From the source repository, using Python 3:

```sh
mkdir -p private
python3 core/tools/mra_build.py core/moomesa.mra /path/to/moomesa.zip private/moomesa.rom
python3 scripts/bucky_rom.py /path/to/bucky.zip --output private/bucky.rom
```

The builders verify input member identities and final image mappings. Existing
outputs are not silently replaced by the Bucky builder. Use a fresh filename
or its `--verify-image` option when checking an existing image.

| Image | Bytes | SHA256 |
| --- | --- | --- |
| `moomesa.rom` | 13,893,760 | `78e98149ba7f72c2a73d3684ee0f78d820b75ef1bc04e77fb8306718edb4eecd` |
| `bucky.rom` | 15,990,912 | `313404772cfd19a298f19fe292918cdbb08cc11d377336e9611e2ce45308c195` |

Copy the completed images into `Assets/moobucky/mmmax4.moobucky/` on the SD.
The included MRA recipes describe interleaving and layout without containing
game data. CPU implementation microcode and audio lookup tables in the HDL
are hardware dependencies, distinct from these external arcade ROM images.
