# Gain-split analogue-chain validation

This is the pre-schematic transfer-function check for soundwave #54. It makes
the rail/headroom invariant reviewable before a KiCad symbol or SPICE
macro-model is chosen. The final schematic simulation must use the selected
op-amp model and load network, but it must preserve these limits.

## Frozen topology

| Stage | Transfer / component values | Purpose |
| --- | --- | --- |
| Preamp | non-inverting, `Rg = 100 kOhm`, `Rf = 698 kOhm`, `Cf = 56 pF`; `Av = 1 + Rf/Rg = 7.98` | Keep the AC output inside the 2.8 V battery rail while setting the audio low-pass deliberately. |
| Preamp corner | `1 / (2 pi Rf Cf) = 4.07 kHz` | Replaces the accidental gain-25 / 100 kHz-GBW corner. |
| Rectifier | ground-referenced precision rectifier, `Av = 3.05` | Supply the rest of the gain after rectification, where output is unipolar. |
| Envelope scale | `7.98 x 3.05 = 24.34` | 90 mV peak at 112 dB SPL becomes 2.19 V peak. |

The original 1.25 V preamp bias example was based on a 2.5 V host rail. The
host's current contract is 2.8 V on battery and 3.3 V on USB; the executable
front-end contract evaluates both rails and the documented microphone
sensitivity corners. The absolute-bias work in soundwave #58 changes the source
of that node; it does not change the gain or headroom budget here.

## 2.8 V battery-rail corner checks

| Input condition | Mic peak | Preamp output | Rectified envelope | Result |
| --- | ---: | ---: | ---: | --- |
| Full scale, 112 dB SPL | 90.0 mV | `1.40 +/- 0.718 V` = 0.682-2.118 V | 2.19 V | Passes: preamp has >=0.682 V from either rail; envelope is below 2.8 V. |
| Coarse trip, 62 dB SPL | `90 mV x 10^(-50/20)` = 0.285 mV | 2.27 mV peak | 6.93 mV | Preserves the approximately 7 mV trip budget. |
| 115 dB SPL | 127 mV | 1.01 V peak | 3.09 V requested | Envelope clips; this is the explicit soft ceiling, not hidden preamp clipping. |

The prior all-preamp allocation requested a 2.19 V peak swing about the bias
node at 112 dB SPL. On a 2.8 V rail no possible bias can provide that 4.38 Vpp
excursion. The split above removes the contradiction: the only intentional
clipping point is the documented unipolar envelope ceiling.

## KiCad / SPICE sign-off requirements

The physical schematic must instantiate the selected MCP6144 (or approved
replacement) macro-model, final diode, envelope hold capacitor, bleed, and
ADC/mux loads. Its transient and AC plots must show all of the following:

1. 90 mV peak, 50 Hz-4 kHz input gives a non-clipped preamp waveform and a
   <=2.2 V envelope at the 2.8 V rail corner.
2. The preamp -3 dB point remains 4 kHz plus/minus component tolerance after
   the selected op-amp's open-loop response is included.
3. A 62 dB-equivalent input produces approximately 6.9 mV before comparator
   offset and hysteresis; trip margin is then re-evaluated against the final
   comparator's over-temperature offset specification.
4. Inputs above 112 dB clip only at the envelope limit; they do not cause a
   phase reversal, comparator ambiguity, or preamp saturation below full
   scale.
