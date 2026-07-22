# Prototype BOM and sourcing record

This file pins the active-part choices that the module schematic must use.  It
does not pretend that a distributor search result is a production release:
prices and inventory are a **2026-07-22 USD snapshot**, before tax, freight,
reel fees, and assembly fees.  Refresh the 100-piece cart immediately before
ordering.

`Basic` and `extended` are LCSC/JLC assembly classifications.  An `External`
line is intentional and must be hand-placed or globally sourced; it may not be
replaced with a top-port or digital microphone.

## Active parts

| Function | Selected MPN | LCSC number | Class | USD @ 100 | Basis / implementation constraint |
| --- | --- | --- | --- | ---: | --- |
| Bottom-port microphone | Infineon `IM73A135V01` | N/A — no confirmed LCSC listing | External | distributor/RFQ required | IP57 analog microphone, 70 uA low-power mode.  Must be bottom-port and must be kept within its 3.0 V absolute maximum. |
| Quad op amp | Microchip `MCP6144T-E/SL` | catalog lookup required | Extended | quote refresh required | 0.6 uA/channel typical and 100 kHz GBW make the existing gain-25 / ~4 kHz-rolloff architecture viable.  Use one quad package rather than silently changing the channel count. |
| Wake comparator | TI `TLV3701IDBVR` | catalog lookup required | Extended | quote refresh required | Single open-drain nanopower comparator.  The open-drain output is mandatory: `/WAKE` must be safe while the module is unpowered and the host pull-up is present. |
| Direct-mode mux | Tech Public `74LVC1G3157GV-TP` | `C42411031` | Basic | 0.0500 | 2:1 analog switch, SOT-23-6.  Verify the selected package's on-resistance and off leakage at the actual 3.0 V rail. |

The earlier `TLV7031` class is explicitly rejected here: it has a push-pull
output, so it conflicts with the specified unpowered-module `/WAKE` interface.
The `TLV3701` family has the required open-drain output and a 560 nA typical
supply current (per TI's data sheet).

## Procurement exceptions

The microphone does not have a confirmed LCSC/JLC catalog row.  This is not a
reason to substitute a superficially similar microphone: the enclosure relies
on the `IM73A135V01` bottom port and IP rating.  Procure it through an
authorized distributor or JLC global sourcing, retain the manufacturer lot
record, and hand-place if the assembly source cannot place it.

The two `catalog lookup required` fields are intentionally left unnumbered
until a live LCSC cart confirms both the exact package and 100-piece price.
The public catalog did not provide a stable programmatic search result during
this sweep; a guessed C-number would be less useful than an explicit release
gate.

## Evidence and release gate

- [TLV3701 data sheet](https://www.ti.com/lit/ds/symlink/tlv3701.pdf) —
  open-drain option and 560 nA typical supply current.
- [MCP6141/2/3/4 family data sheet](https://www.microchip.com/en-us/product/MCP6144)
  — micropower quad-op-amp family.
- [IM73A135V01 product family](https://www.infineon.com/cms/en/product/sensor/mems-microphones/mems-microphones-for-consumer/im73a135v01/)

Before this BOM is released, a buyer must:

1. save the LCSC 100-piece cart for `MCP6144T-E/SL` and `TLV3701IDBVR`, adding
   their exact C-numbers, class, and price to this table;
2. obtain a 100-piece quote and placement path for `IM73A135V01`; and
3. have #42 validate these package choices against the KiCad footprints and
   #45 validate mic sensitivity, comparator trip margin, and mux leakage on
   hardware.
