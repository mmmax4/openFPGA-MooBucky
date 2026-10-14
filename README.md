# moobucky — Analogue Pocket openFPGA

One arcade core for **Wild West C.O.W.-Boys of Moo Mesa** and **Bucky O'Hare**,
maintained by **mmmax4**, based on plasticbugs' Moo Mesa implementation.

![Moo Mesa and Bucky O'Hare](docs/images/marquee.png)

## Supported games

| Selection | ROM set | Image filename |
| --- | --- | --- |
| Moo Mesa EAB | MAME World parent `moomesa`, ver EAB | `moomesa.rom` |
| Bucky EAB | MAME World parent `bucky`, ver EAB | `bucky.rom` |

The core includes complete audio and independent ROM, EEPROM and per-game
settings. Both games have passed Pocket tests. Other
revisions are not qualified. A boot screen saying VERSION EA does not identify
the EAB ROM image; use the verified image hashes in [ROM setup](docs/ROM_SETUP.md).

## Installation

Requires Pocket OS **2.0 or later**; last confirmed test firmware is **2.7**.
Merge the release's `Cores`, `Platforms`, `Assets` and `Presets` into the SD root.
Supply your own ROM images in `Assets/moobucky/mmmax4.moobucky/`, then select
**moobucky** and the full game title. Game ROMs and saves are not included.

See [installation and saves](docs/INSTALL.md), [ROM setup](docs/ROM_SETUP.md),
[release history](CHANGELOG.md) and [credits](CREDITS.md).

## Controls

| Input | Action |
| --- | --- |
| D-pad | Move |
| A / Y | Jump |
| B | Shoot |
| X | Bucky button 3 / Moo alternate shoot |
| Select | Coin |
| Start | Start |

`DIP: Sound`, `DIP: Coins` and `DIP: Players` have independent choices.
`Test Button` and `Service Button` initially show **Unassigned**. Choose a P1
key in Core Settings to use either momentary input. The existing manual
`Test Switch (hold)` is also available. Assigning a gameplay key retains its
gameplay action. Difficulty and lives are configured in the game's service menu.

Existing Dock connections support four players; P3/P4 use digital D-pads.
A dedicated four-controller hardware test is not separately documented.

## Development and verification

The source retains its existing layout in `core/`; SD definitions
are in `pkg/`. [Build instructions](docs/BUILD.md) cover the pinned Quartus flow.
All 116 fitted timing checks across four corners pass, with 34 free M10Ks. See [verification scope](docs/VERIFICATION.md).

Report reproducible issues using the bug template. Include game revision,
core version, firmware, and the stage/action involved; do not attach ROMs or saves.
Licensing is documented in [LICENSING.md](LICENSING.md).

## High scores

The core saves each game's 128-byte cabinet EEPROM. It does not save the
separate high-score tables in main-CPU RAM. Preserving those tables requires
an additional RAM save/restore feature, which is not implemented. Save states
are not implemented.
