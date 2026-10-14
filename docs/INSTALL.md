# Installation and settings

Merge `Cores`, `Platforms`, `Assets` and `Presets` from the release into your
Pocket SD root. Add your verified `moomesa.rom` and `bucky.rom` to
`Assets/moobucky/mmmax4.moobucky/`. Open **moobucky** and choose:

- `Moo Mesa EAB`
- `Bucky EAB`

Instance JSONs and per-game presets use the same filename.
ROM images are moomesa.rom and bucky.rom, with separate moomesa.sav
and bucky.sav EEPROM files. Preserve existing settings and saves.

EEPROM paths are `Saves/moobucky/common/moomesa.sav` and
`Saves/moobucky/common/bucky.sav`. Back up existing saves before transferring
them from a previous platform namespace. Per-game Core Settings and Controls
are handled by Pocket OS; avoid replacing user Settings with bundled defaults.

Select DIP sound output, common/independent coins and 2/3/4 players separately.
Changing a DIP selection follows the existing game-reset behavior.
Use the manual Test switch in Core Settings for the original service menu.
Sleep is not supported by the current core.


## High scores

The core saves each game's 128-byte cabinet EEPROM. It does not save the
separate high-score tables in main-CPU RAM. Preserving those tables requires
an additional RAM save/restore feature, which is not implemented. Save states
are not implemented.
