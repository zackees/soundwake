# Prototype BOM and sourcing record

This file pins the active-part choices that the module schematic must use.  It
does not pretend that a distributor search result is a production release:
prices and inventory are a **2026-07-22 USD snapshot**, before tax, freight,
reel fees, and assembly fees.  Refresh the 100-piece cart immediately before
ordering.

`Basic` and `extended` are LCSC/JLC assembly classifications.  An `External`
line is intentional and must be hand-placed or globally sourced; it may not
be replaced with a bottom-port, digital, or non-IP-rated microphone.

## Active parts

| Function | Selected MPN | LCSC number | Class | USD @ 100 | Basis / implementation constraint |
| --- | --- | --- | --- | ---: | --- |
| Top-port microphone | PUI Audio `AMM-2742-T-WP-R` | N/A — no confirmed LCSC listing | External | distributor/RFQ required | Selected top-port analog IP57 microphone (README decision 6, host environmental baseline).  200 uA maximum, 2.0 V rated, -42 dBV +/-1 dB.  Replaces the bottom-port `IM73A135V01`, which the leather construction rejects. |
| Mic-rail LDO (2.0 V) | Torex `XC6206P202MR`-class, SOT-23 | catalog lookup required | Basic expected | quote refresh required | Absolute 2.0 V mic rail + trip reference (README decision 10).  ~1 uA IQ; confirm dropout at 200 uA is millivolt-class so 2.0 V holds at the 2.5 V rail corner. |
| Quad op amp | Microchip `MCP6144T-E/SL` | catalog lookup required | Extended | quote refresh required | 0.6 uA/channel typical and 100 kHz GBW make the gain-25 / ~4 kHz-rolloff architecture viable.  One channel is freed by the mic-rail LDO; a dual + passive bias string is the schematic-time cost-down alternative — do not change the channel count silently. |
| Wake comparator | TI `TLV7041` (SOT-23-5 or SC70) | catalog lookup required | Extended | quote refresh required | Open-drain nanopower comparator, **1.6–6.5 V supply**.  Replaces the earlier `TLV3701IDBVR`: its 2.5 V minimum supply has zero margin at the host's 2.5 V battery-side rail.  Open-drain remains mandatory (`/WAKE` safe while unpowered); verify the offset spec against the README decision-4 trip margin. |
| Direct-mode mux | Tech Public `74LVC1G3157GV-TP` | `C42411031` | Basic | 0.0500 | 2:1 analog switch, SOT-23-6.  Verify on-resistance and off leakage across the 2.5–3.3 V rail range, not at a single point. |

The earlier `TLV7031` class was rejected for its push-pull output, which
conflicts with the specified unpowered-module `/WAKE` interface.  Its
open-drain sibling `TLV7041` inherits the 1.6–6.5 V supply range and is the
selected direction; the interim `TLV3701` pick (open-drain, 560 nA typical)
is retired by the dual-level host rail because its data sheet minimum supply
is 2.5 V — exactly the battery-side rail, leaving no tolerance margin.

## Procurement exceptions

The microphone does not have a confirmed LCSC/JLC catalog row.  This is not a
reason to substitute a superficially similar microphone: the leather-wrapped
construction relies on the `AMM-2742-T-WP-R`'s top port and IP57 rating, and
the calibration plan relies on its +/-1 dB sensitivity tolerance.  Procure it
through an authorized distributor, retain the manufacturer lot record, and
hand-place if the assembly source cannot place it.

The two `catalog lookup required` fields are intentionally left unnumbered
until a live LCSC cart confirms both the exact package and 100-piece price.
The public catalog did not provide a stable programmatic search result during
this sweep; a guessed C-number would be less useful than an explicit release
gate.

## Evidence and release gate

- [PUI AMM-2742-T-WP-R data sheet](https://puiaudio.com/file/specs-AMM-2742-T-WP-R.pdf)
  — sensitivity -42 dBV +/-1 dB, 200 uA max, 2.0 V rated, 0.5 dB
  sensitivity shift 3.6–1.5 V, PSR -100 dB, SNR 59 dB(A), IP57.
- [TLV7041 product page](https://www.ti.com/product/TLV7041) — open-drain
  nanopower comparator, 1.6–6.5 V supply.
- [TLV3701 data sheet](https://www.ti.com/lit/ds/symlink/tlv3701.pdf) —
  retired pick; 2.5 V minimum supply disqualifies it on the dual-level rail.
- [MCP6141/2/3/4 family data sheet](https://www.microchip.com/en-us/product/MCP6144)
  — micropower quad-op-amp family.

Before this BOM is released, a buyer must:

1. save the LCSC 100-piece cart for `MCP6144T-E/SL`, `TLV7041`, and the
   `XC6206P202` 2.0 V LDO, adding their exact C-numbers, class, and price to
   this table;
2. obtain a 100-piece quote, lot traceability, and placement path for
   `AMM-2742-T-WP-R`; and
3. have soundwave#42 validate these package choices against the KiCad
   footprints and soundwave#45 validate mic sensitivity, comparator trip
   margin at both host rail levels, mic-rail LDO dropout, and mux leakage on
   hardware.
