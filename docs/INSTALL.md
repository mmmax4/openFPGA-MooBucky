# Installation and settings

Merge `Cores`, `Platforms`, `Assets` and `Presets` from the release into your
Pocket SD root. Add your verified `moomesa.rom` and `bucky.rom` to
`Assets/moobucky/mmmax4.moobucky/`. Open **moobucky** and choose:

- `Wild West C.O.W.-Boys of Moo Mesa - EAB`
- `Bucky O'Hare - EAB`

The corresponding instance JSON and Interact Preset use the same full filename.
ROM and EEPROM filenames remain `moomesa.rom` / `moomesa.sav` and
`bucky.rom` / `bucky.sav`; changing the selectable title does not change them.
Settings belong to the primary asset filename. Existing settings saved under
`Moo Mesa EAB.json` or `Bucky EAB.json` may need reselecting after the rename.
Preserve old SD settings and saves; the release contains neither.

EEPROM paths are `Saves/moobucky/common/moomesa.sav` and
`Saves/moobucky/common/bucky.sav`. Back up existing saves before transferring
them from a previous platform namespace. Per-game Core Settings and Controls
are handled by Pocket OS; avoid replacing user Settings with bundled defaults.

Select DIP sound output, common/independent coins and 2/3/4 players separately.
Changing a DIP selection follows the existing game-reset behavior.
Test and Service assignments start Unassigned. A Test button asserts the Test
input only while held; the game's service screen decides how to exit.
Service is the separate Service 1 input. Leave the manual Test switch off when
using the momentary button. Sleep is not supported by the current core.

## High scores

The core saves each game's 128-byte cabinet EEPROM. It does not save the
separate high-score tables in main-CPU RAM. Preserving those tables requires
an additional RAM save/restore feature, which is not implemented. Save states
are not implemented.
