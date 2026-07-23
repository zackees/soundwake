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
| Mic-rail LDO (2.0 V) | Torex `XC6206P202MR-G`, SOT-23 | `C2891260` | Basic | 0.1563 | Absolute 2.0 V mic rail + trip reference (README decision 10).  1 uA typical IQ and 120 mA rating; LCSC snapshot showed 955 in stock.  Confirm dropout at 200 uA is millivolt-class so 2.0 V holds at the host's true low-rail corner. |
| Quad op amp | Microchip `MCP6144T-E/SL` | catalog lookup required | Extended | quote refresh required | 0.6 uA/channel typical and 100 kHz GBW make the gain-25 / ~4 kHz-rolloff architecture viable.  One channel is freed by the mic-rail LDO; a dual + passive bias string is the schematic-time cost-down alternative — do not change the channel count silently. |
| Wake comparator | TI `TLV9021DCKR`, SC-70-5 | `C22433207` | Extended | 1.4879 | Open-drain precision comparator, **1.65–5.5 V supply**, 16 uA typical.  Its guaranteed +/-2 mV offset across -40 to +125 C protects the coarse wake-trip margin; the host's specified 2.4 V VDD floor leaves >=750 mV supply margin.  Open-drain remains mandatory (`/WAKE` safe while unpowered).  LCSC snapshot showed 10 in stock. |
| Direct-mode mux | Tech Public `74LVC1G3157GV-TP` | `C42411031` | Basic | 0.0500 | 2:1 analog switch, SOT-23-6.  Verify on-resistance and off leakage across the 2.5–3.3 V rail range, not at a single point. |

The earlier `TLV7031` class was rejected for its push-pull output, which
conflicts with the specified unpowered-module `/WAKE` interface.  Its
open-drain sibling `TLV7041` meets the supply requirement but has an 8 mV
maximum offset and therefore cannot protect the millivolt-scale wake-trip
margin.  The selected `TLV9021` trades 16 uA of detector current for a
guaranteed +/-2 mV offset and still has >=750 mV supply margin at the host's
2.4 V VDD floor.  The interim `TLV3701` pick (open-drain, 560 nA typical) is
retired because its 2.5 V minimum supply leaves no tolerance margin.

## Procurement exceptions

The microphone does not have a confirmed LCSC/JLC catalog row.  This is not a
reason to substitute a superficially similar microphone: the leather-wrapped
construction relies on the `AMM-2742-T-WP-R`'s top port and IP57 rating, and
the calibration plan relies on its +/-1 dB sensitivity tolerance.  Procure it
through an authorized distributor, retain the manufacturer lot record, and
hand-place if the assembly source cannot place it.

The remaining `catalog lookup required` field is intentionally left
unnumbered until a live LCSC cart confirms the exact package and 100-piece
price.  A guessed C-number would be less useful than an explicit release
gate.

## Evidence and release gate

- [PUI AMM-2742-T-WP-R data sheet](https://puiaudio.com/file/specs-AMM-2742-T-WP-R.pdf)
  — sensitivity -42 dBV +/-1 dB, 200 uA max, 2.0 V rated, 0.5 dB
  sensitivity shift 3.6–1.5 V, PSR -100 dB, SNR 59 dB(A), IP57.
- [TLV9021 data sheet](https://www.ti.com/lit/ds/symlink/tlv9021.pdf) —
  open-drain output, 1.65–5.5 V supply, and +/-2 mV maximum offset across
  -40 to +125 C.
- [LCSC TLV9021DCKR listing](https://www.lcsc.com/product-detail/C22433207.html)
  — `C22433207`, USD 1.4879 at 100 in the sourcing snapshot.
- [TLV3701 data sheet](https://www.ti.com/lit/ds/symlink/tlv3701.pdf) —
  retired pick; 2.5 V minimum supply disqualifies it on the dual-level rail.
- [MCP6141/2/3/4 family data sheet](https://www.microchip.com/en-us/product/MCP6144)
  — micropower quad-op-amp family.

Before this BOM is released, a buyer must:

1. save the LCSC 100-piece cart for `MCP6144T-E/SL`, `TLV9021DCKR`, and
   `XC6206P202MR-G`, refreshing this table's stock and price snapshot;
2. obtain a 100-piece quote, lot traceability, and placement path for
   `AMM-2742-T-WP-R`; and
3. have soundwave#42 validate these package choices against the KiCad
   footprints and soundwave#45 validate mic sensitivity, comparator trip
   margin at both host rail levels, mic-rail LDO dropout, and mux leakage on
   hardware.
