# MooBucky 0.4.1

MooBucky 0.4.1 for Analogue Pocket openFPGA.

## Changes

- Full game-title selection names with matching per-game presets.

## High scores

The core saves each game's 128-byte cabinet EEPROM. It does not save the
separate high-score tables in main-CPU RAM. Preserving those tables requires
an additional RAM save/restore feature, which is not implemented. Save states
are not implemented.

## Installation

Download **mmmax4.moobucky-v0.4.1.zip**.
Copy Cores, Platforms, Assets and Presets to the SD root. Supply your own
World EAB `moomesa.zip` and `bucky.zip`; the included builders create the
two ROM images. See the repository README for setup and controls.
No game ROM or save is bundled.
