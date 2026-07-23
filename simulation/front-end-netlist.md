# Front-end electrical netlist contract

This is the pre-KiCad analog netlist contract for FastLED/soundwave#92. The
soundwake schematic PR must use these names verbatim and replace every review
TODO with a KiCad reference; it does not replace that schematic.

| Net | Connected function | Required test point |
| --- | --- | --- |
| `MODULE_VDD` | Host GPIO power, local decoupling, XC6206P202 input, MCP6144 supply | `TP_MODULE_VDD` |
| `MIC_2V0` | XC6206P202 output, post-LDO 330 Ohm/10 uF filter, PUI microphone, TLV9021 reference divider | `TP_MIC_2V0` |
| `MIC_OUT` | PUI microphone output and first coupling capacitor | `TP_MIC_OUT` |
| `PREAMP_BIAS` | MCP6144 non-inverting bias network | `TP_PREAMP_BIAS` |
| `PREAMP_OUT` | MCP6144 preamp output, 50 Hz-4 kHz raw tap, precision-rectifier input | `TP_PREAMP_OUT` |
| `LEVEL_ENVELOPE` | Precision rectifier hold/release output | `TP_LEVEL_ENVELOPE` |
| `LEVEL` | Downstream mux output to host ADC | `TP_LEVEL` |

## Frozen calculation values

- Preamp: `Rg=100 kOhm`, `Rf=698 kOhm`, `Cf=56 pF`, nominal gain 7.98,
  nominal low-pass 4.07 kHz.
- Coupling high-pass: each `33 kOhm` / `100 nF` stage, nominal 48.2 Hz.
  Exact loading and second-order response remain `TODO(#92-review)` until the
  KiCad schematic and selected MCP6144 macro-model are reviewed.
- Mic rail: `XC6206P202` target 2.0 V, followed by 330 Ohm and 10 uF at the
  microphone. The contract budgets the 200 uA maximum microphone current and
  therefore a 66 mV DC post-filter drop.

Run `python simulation/check_front_end.py` before changing any value. The
checker validates rail feasibility, passive corners, preamp headroom, and the
required named nodes. It is an electrical calculation, not a microphone SPL or
coating qualification; those are bench exits in FastLED/soundwave#45.
