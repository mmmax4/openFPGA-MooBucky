# Verification scope for 0.3.0

All 113 available qualified inputs match their recorded digests. All 116 fitted timing checks pass over four corners, worst margin +0.122 ns, with zero unconstrained paths and no unexpected ignored constraints.

Both games and the 0.4 controls/menu/banner build passed Pocket checks. Pocket OS 2.7 is the last confirmed firmware. Full-title selection/preset names were checked on Pocket. Exact installed SD bytes were not independently read back. Full game completion, every four-controller Dock action and physical high-score persistence have not been separately established.

Focused digital coverage includes 64 Moo frozen video states, three Bucky frozen states, real-memory readback for both games, 2,054 K054000 cases and the 40-second PCM comparison. The 0.4 Test/Service selectors have targeted coverage, and the direct clock decoder has 77,185-edge equivalence coverage. These do not constitute new full-game runs. The retained CPU startup run is scoped separately. Global flip/multipage layouts and some shadow approximations are not exhaustively qualified.

The original 0.3 generated build-ID output is unavailable; see BUILD.md. Preferred machine source and its generator are provided, without claiming all 114 historical output files were recovered.
