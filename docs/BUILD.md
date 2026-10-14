# Build the FPGA source

The release bitstream was built with **Quartus Lite 21.1.1 Build 850** for
**Cyclone V 5CEBA4F23C8**. The `core/` layout is unchanged, including vendored
modules and their license notices. The snapshot retains the actual build-ID
MIF used by the qualified bitstream. No game ROM is needed for compilation.
The preflow generates a new timestamp/random build ID on each compilation;
this is a source snapshot, not a promise of byte-identical rebuilt output.
QIP references to optional wizard metadata (`.ppf`/`.cmp`) and the generated
postflow `.cdf` do not supply HDL and are not included in the source snapshot.

```sh
bash scripts/build.sh compile
```

Set `QUARTUS_BIN` when Quartus is installed outside the default
`/opt/intelFPGA_lite/21.1/quartus/bin` location. The project uses one CPU and
one Quartus flow. New RTL requires synthesis; fitter-only settings may use
`bash scripts/build.sh refit` after a successful map.

Review setup, hold, recovery, removal and minimum pulse width at every reported
corner, plus unconstrained paths and ignored constraints, before packaging.
The qualified build has 274/308 M10Ks, 9,376/18,480 ALMs and 18/66 DSPs.
All 116 timing checks pass; worst slack is +0.088 ns. The reset LUT duplication
is explicitly confirmed in the fitter report. Clocks and functional reset
latency are unchanged.

Raw Quartus RBF bytes must be bit-reversed individually to obtain Pocket's
`.rbf_r` format. The maximum bitstream filename is 15 characters, including
the extension. SD definitions are under `pkg/`; merge the rebuilt
bitstream and those definitions into an SD tree for a private hardware test.
`python3 scripts/package_release.py` checks fresh all-corner qualification and
creates a local ROM-free ZIP under `build/` using the public `pkg/` definitions.
