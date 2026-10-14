# High-score storage

The core saves each game's 128-byte cabinet EEPROM. It does not save the
separate high-score tables in main-CPU RAM. Preserving those tables requires
an additional RAM save/restore feature, which is not implemented. Save states
are not implemented.

The save adapter exports the seven-bit-address EEPROM port. No instantiated
high-score helper connects main RAM to APF saving. The pinned official MAME
hiscore definition lists Bucky main-CPU RAM at 0x0801E0 (80 bytes) and Moo Mesa
at 0x1801E0 (151 bytes):
https://github.com/mamedev/mame/blob/ca0a9a15998ffff1112389ddaa57a283beafb66e/plugins/hiscore/hiscore.dat

This identifies separate RAM tables; it does not claim a fresh Pocket power-cycle
test or a complete disassembly of either program's startup/save behavior.
