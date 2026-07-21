# soundwake

A low-power, always-on sound-level detector breakout board that wakes a sleeping
MCU when the music starts.

`soundwake` is a discrete analog circuit built around a water- and dust-resistant
(IP57-class) analog MEMS microphone. It continuously measures the ambient sound
pressure level (SPL) in the combined **bass + voice** band and exposes the result
on two pins: an analog loudness-envelope output and an active-low wake
interrupt, plus a direct mode that turns the envelope pin into raw
band-limited audio on request. It is designed to be the always-on watchdog subsystem of a
battery-powered, sound-reactive product, drawing well under 350 µA while
everything else sleeps.

## What it does

- **Measures loudness, not audio.** The board outputs a slowly varying envelope
  voltage proportional to sound amplitude — a signal an MCU ADC can poll, not a
  raw microphone waveform. The host converts readings to dB with a `20·log10`
  lookup at 60 fps; keeping the envelope linear keeps the analog chain down to
  textbook blocks and eliminates the log junction's drift and unit spread.
- **Wakes the host on loud sound.** A coarse comparator trip (~62 dB SPL)
  drives `/WAKE` low; the host's EXTI edge-detect latches even the briefest
  pulse, and firmware enforces the true 68 dB SPL threshold plus the
  30–100 ms qualification after waking.
- **Listens to music and people, ignores the wearer.** The detection band covers
  musical bass through the human voice range. Handling noise — the enclosure
  rubbing against clothing — is an explicit rejection target.
- **Direct mode on demand.** Holding the `/RAW` pad low switches `LEVEL` from
  envelope to the raw band-limited audio (50 Hz–4 kHz, mid-rail biased), so the
  host can run FFTs, tune thresholds, or verify the whole chain in production —
  on the single ADC trace it already has.
- **Powers from a host GPIO pin.** The whole detector is powered by one MCU
  GPIO driven high, so the product is default-off and the host can cut the
  detector to zero at any time.

## Interface

Castellated-edge SMT module, five pads. Reflows onto the parent PCB like a
component; solders onto a carrier or headers for bench work.

| Pad     | Direction | Description                                                            |
| ------- | --------- | ---------------------------------------------------------------------- |
| `VDD`   | power     | Supply input, fed directly from a host GPIO pin (see power model below) |
| `GND`   | power     | Ground                                                                  |
| `LEVEL` | out       | Envelope voltage (default) or raw audio in direct mode; full scale ≈ 115 dB SPL |
| `/WAKE` | out       | Active-low comparator, coarse ~62 dB SPL trip; open-drain, host pull-up  |
| `/RAW`  | in        | Hold low for direct mode; module pull-up ⇒ floating = envelope mode      |

### Pinout / host wiring

```mermaid
flowchart LR
    subgraph MOD["soundwake module (castellated pads)"]
        VDD["VDD"]
        GND["GND"]
        LEVEL["LEVEL"]
        WAKE["/WAKE"]
        RAW["/RAW"]
    end
    subgraph MCU["CH32V203 host"]
        PWR["GPIO output<br/>power + enable"]
        MGND["GND"]
        ADC["ADC channel<br/>60 Hz envelope / ≥8 kHz raw"]
        EXTI["EXTI pin<br/>falling edge, internal pull-up"]
        RREQ["GPIO, open-drain<br/>direct-mode request"]
    end
    PWR -->|"3.3 V while driven high"| VDD
    GND --- MGND
    LEVEL -->|"envelope (default) or raw audio"| ADC
    WAKE -->|"open-drain, active low"| EXTI
    RREQ -->|"hold low = direct mode"| RAW
```

Physical pad order and module dimensions are still open (see open questions).

### Block diagram — behind the pads

```mermaid
flowchart LR
    VDDPAD(["VDD pad"]) --> FLT["RC supply filter +<br/>local decoupling"]
    FLT --> RAIL["3.3 V analog rail"]
    RAIL --> MICREG["1.65 V mic rail<br/>buffered divider"]
    MICREG --> MIC
    MIC["IM73A135V01<br/>IP57, bottom-port<br/>low-power mode, 70 µA"] --> AMP["preamp<br/>coupling caps = ~50 Hz high-pass<br/>GBW rolloff = ~4 kHz low-pass"]
    AMP --> PKD["precision peak detector<br/>rectify + hold, one op-amp<br/>attack ~1–5 ms, release ~100–300 ms"]
    AMP -->|"raw tap"| MUX["2:1 analog mux"]
    PKD --> MUX
    MUX --> LEVELPAD(["LEVEL pad<br/>envelope or raw audio"])
    PKD --> CMP["comparator<br/>coarse ~62 dB SPL trip, hysteresis"]
    CMP --> WAKEPAD(["/WAKE pad<br/>open-drain"])
    RAWPAD(["/RAW pad<br/>pull-up = envelope mode"]) -.->|"held low = raw"| MUX
```

After the cost-down pass and the linear-envelope revision (see below) the
chain is deliberately minimal: four active ICs — one of them the tiny
direct-mode mux — and no math hardware at all.
Qualification, wake stretching, startup masking, the dB conversion, and the
exact 68 dB threshold all live in host firmware — the EXTI pending flag
latches even a nanosecond comparator blip, so nothing needs to hold `/WAKE`
low in hardware, and the comparator only needs to be coarsely right.

## How the analog sound processor works

The processor is three analog stages plus a firmware tail. Sound becomes a
band-limited signal (stage 1), a single op-amp stage turns it into a loudness
envelope (stage 2), and a comparator provides a coarse wake trip (stage 3).
Everything that used to be timing or math hardware — qualification,
stretching, startup masking, and the dB conversion itself — is firmware.

### Stage 1 — Acoustic front end: sound → band-limited signal

The mic's raw output is millivolt-scale audio riding on a DC bias. The
inter-stage coupling capacitors do double duty as the ~50 Hz high-pass (two
cascaded coupling networks give a second-order corner for free), shedding
rumble and the deepest clothing-rub energy. The micropower preamp (gain ~25×
— the mic's single-ended sensitivity puts 115 dB SPL at roughly 100 mV peak)
raises the signal above the detector's noise floor, and its own gain-bandwidth
rolloff serves as the ~4 kHz low-pass. No dedicated filter stages are fitted.

```mermaid
flowchart LR
    SPL(("sound<br/>pressure")) --> MIC["IM73A135V01 mic<br/>IP57, bottom-port<br/>single-ended tap of diff output"]
    MIC -->|"raw audio<br/>mV-scale AC on DC bias"| ACC["coupling caps<br/>double as ~50 Hz high-pass"]
    ACC --> PRE["micropower preamp<br/>fixed gain<br/>GBW rolloff = ~4 kHz low-pass"]
    PRE -->|"band-limited audio<br/>(bass + voice)"| S1OUT(("to stage 2"))
```

### Stage 2 — Precision peak detector: audio → loudness envelope

A textbook block: a micropower op-amp precision rectifier (the diode sits
inside the feedback loop, so its drop and drift cancel) charges a hold
capacitor through a fast path (attack ~1–5 ms, one kick registers at full
height) while a bleed discharges it (release ~100–300 ms). Exponential decay
in the linear domain *is* constant dB-per-second decay, so the release still
falls musically between beats. The op-amp output is low-impedance and drives
the `LEVEL` pad directly. No junction log element exists anywhere — the host
computes `dB = 20·log10(reading)` from a lookup table at 60 fps, oversampling
~16× per frame to recover quiet-end resolution.

```mermaid
flowchart LR
    S2IN(("band-limited<br/>audio")) --> PR["precision rectifier<br/>op-amp, diode inside loop<br/>no drop, no drift"]
    PR -->|"fast charge<br/>attack ~1–5 ms"| HOLD["hold capacitor + bleed<br/>voltage = loudness, linear amplitude"]
    HOLD -->|"release ~100–300 ms<br/>= constant dB/s decay"| LVPAD(["LEVEL pad"])
    HOLD --> S2OUT(("to stage 3"))
```

### Stage 3 — Wake comparator: coarse trip → `/WAKE`

A nanopower comparator with hysteresis drives the open-drain `/WAKE` pad
directly. Its trip is deliberately set **coarse and low (~62 dB SPL)**: at
linear-envelope levels, 68 dB SPL is only ~15 mV, where nanopower comparator
input offset (±3–5 mV) would smear a trip point by several dB. Set ~6 dB low,
worst-case positive offset still cannot push the trip above 68 dB (a unit
that can't wake would be a field failure), and negative offset merely causes
early wakes that firmware filters. The exact 68 dB threshold is enforced in
firmware from `LEVEL`, in dB domain, to ~±0.5 dB.

```mermaid
flowchart LR
    S3IN(("envelope")) --> CMP["nanopower comparator<br/>coarse ~62 dB SPL trip + hysteresis"]
    CMP --> WK(["/WAKE pad<br/>open-drain, active low"])
```

### Direct mode — raw audio on the `LEVEL` pad

Holding `/RAW` low flips a 2:1 analog mux so `LEVEL` carries the preamp's
band-limited audio (50 Hz–4 kHz, riding the mid-rail bias) instead of the
envelope. The peak detector and wake comparator keep running — the module
still wakes the host while in direct mode. The host samples at ≥8–10 kHz and
subtracts the bias in software. Quality is voice-band monitor grade
(micropower-preamp noise floor): right for FFT/beat analysis, threshold
tuning, bring-up, and production test; wrong for recording music. Hardware
cost: one SC70 mux (<1 µA, ~$0.05–0.15) and the fifth pad.

### Firmware tail — the wake decision

The timing behavior removed from hardware, as the host now implements it:

```mermaid
stateDiagram-v2
    [*] --> Unpowered
    Unpowered --> Settling : firmware drives power GPIO high
    Settling --> Armed : ~100 ms firmware mask, then pull-up on, EXTI armed
    Armed --> Woken : comparator edge on /WAKE (EXTI latches any pulse width)
    Woken --> Qualifying : firmware samples LEVEL at 60 Hz
    Qualifying --> Armed : below 68 dB or not sustained (back to Stop)
    Qualifying --> Running : 68 dB+ sustained 30–100 ms (music confirmed)
    Running --> Armed : show over — back to Stop, EXTI re-armed
    note right of Settling : analog chain settling, nothing listening
    note right of Qualifying : the old hardware qualification window, relocated
```

## Target specifications

| Parameter              | Target                                | Notes                                                    |
| ---------------------- | ------------------------------------- | -------------------------------------------------------- |
| Total supply current   | **< 350 µA** budget; ~80–110 µA projected | Mic dominates; see current budget section            |
| Power source           | Host GPIO pin, 3.3 V nominal          | Default-off product; GPIO ~50–100 Ω source impedance     |
| Detection band         | ~50 Hz – 4 kHz (bass + voice)         | Exact corners TBD                                        |
| Wake threshold (effective) | 68 dB SPL, enforced in firmware   | ~±0.5 dB electrical + the mic's ±1–3 dB sensitivity spread |
| Hardware wake trip     | ~62 dB SPL, coarse, fixed             | Set low so comparator offset can never push it above 68 dB |
| Wake qualification     | ~30–100 ms sustained, in firmware     | Host wakes on comparator edge, samples `LEVEL`, decides  |
| Wake output            | Raw comparator with hysteresis        | No stretch needed — host EXTI latches any pulse width    |
| `LEVEL` transfer       | Linear-in-amplitude envelope          | Full scale ≈ 115 dB SPL; host does `20·log10` lookup     |
| `LEVEL` accuracy       | ~±0.5 dB above 75 dB SPL              | Quantization-limited below; 16× oversampling ⇒ ~±0.3 dB at 60 dB |
| Envelope dynamics      | Beat-tracking: ~1–5 ms attack, ~100–300 ms release | LEDs can ride individual kicks at 60 fps    |
| Envelope readout rate  | Valid at 60 Hz polling                | Fresh, settled values every ~16 ms                       |
| Direct mode            | `/RAW` low ⇒ `LEVEL` = raw audio      | 50 Hz–4 kHz, mid-rail bias; envelope + wake stay active  |
| Microphone             | Infineon IM73A135V01 (candidate)      | IP57, analog, **bottom-port**, 70 µA in low-power mode   |
| Operating environment  | 0–45 °C, mild outdoor                 | Rain resistance via mic IP rating + conformal coat       |
| Board protection       | Conformal coating                     | Coating must mask the mic port (assembly requirement)    |
| BOM cost               | < ~$4; ~$2–3 projected after cost-down | 4 active ICs + roughly a dozen passives                  |
| Assembly               | JLCPCB SMT (design to their catalog)  | *Assumed default — not yet confirmed*                    |

## Architecture decisions

Decisions from the 2026-07-21 design interview, with rationale.

### 1. Power via host GPIO, default-off

The detector's `VDD` is a CH32V203 GPIO driven high. This makes the product
default-off with zero leakage, and gives the host a free kill switch.

The trap this creates: in the CH32V203's deepest **Standby** mode, GPIOs go
high-impedance — the detector would lose power exactly when it should be
listening, and nothing could ever wake the MCU. Therefore the host **must sleep
in Stop mode**, where GPIO output states are retained.

Verified against the CH32V203 datasheet (V2.7, tables 4-8-1/4-8-2, 4-16): Stop
mode with the regulator in low-power mode draws **10.5 µA typ** vs. ~0.5–1.1 µA
in Standby — a ~10 µA penalty, about 3 % of the detector's own budget, so the
GPIO-power scheme stands and no latching load switch is needed. Stop also wakes
in ~76 µs vs. Standby's ~4.8 ms — and since the EXTI pending flag latches the
comparator edge, no wake-pulse stretching is needed anywhere. Two
firmware/part traps:

- Stop entry must select the regulator's low-power mode (`LPDS=1, PDDS=0` in
  PWR_CTLR). With the regulator left in Run mode, Stop draws 70.5 µA.
- The 128K **CH32V203RBT6 is a different die and much worse** (245.7 µA
  regulator-run Stop, 22.9 µA regulator-low-power Stop) — prefer a non-RBT6
  variant.

A side benefit: the GPIO's ~50–100 Ω source impedance plus the module's local
bulk capacitance forms a free low-pass filter against rail noise.

### 2. Linear envelope, dB in firmware (revised 2026-07-21)

`LEVEL` is a linear-amplitude envelope; the host computes
`dB = 20·log10(reading)` via lookup table at 60 fps. This **reverses** the
interview's hardware-dB choice, which was made when the log stage looked
free: in the discrete implementation it costs an op-amp *plus a junction
element*, and that junction is the riskiest, least-cookbook block in the
whole design — while removing it saves only itself, since the op-amp is
needed for precision rectification either way.

What the reversal buys and costs:

- **Error classes eliminated**: junction temperature drift (was ~±1.5–2 dB
  uncompensated) and junction unit-to-unit spread (±1–2 dB). The rectifier
  diode sits inside the op-amp loop and cancels; gain is set by 1 % resistors
  (±0.1 dB).
- **Error class added**: ADC quantization at the quiet end. With full scale at
  115 dB SPL, one 12-bit count is 0.02 dB at 95 dB, 0.2 dB at 75 dB, 1.2 dB at
  60 dB. The LED show's working range (85–115 dB) resolves *better* than the
  log stage delivered; firmware oversampling (~16 reads per frame) recovers
  ~2 effective bits at the quiet end.
- **Companion change (non-negotiable)**: the wake comparator cannot sit at
  68 dB in the linear domain — see decision 4.

### 3. Beat-tracking envelope everywhere

One fast envelope (~1–5 ms attack, ~100–300 ms release) feeds both `LEVEL` and
the wake path. LEDs can pulse with individual kick drums at 60 fps. The cost —
scratches look like kicks — is paid back by firmware time-qualification after
wake, not by slowing the envelope.

### 4. Wake path: coarse comparator, threshold and qualification in firmware

A nanopower comparator with hysteresis drives `/WAKE` directly, tripping at a
deliberately low ~62 dB SPL. At linear-envelope levels 68 dB is only ~15 mV,
where comparator input offset (±3–5 mV) would smear the trip by +2.5/−3.6 dB;
sitting ~6 dB low guarantees worst-case offset can never push the trip above
68 dB, and early trips just become cheap firmware-filtered wakes. The
CH32V203's EXTI pending flag latches a comparator pulse of any width, so
nothing needs to hold the line low, and firmware — which had to double-check
anyway — enforces the true 68 dB threshold and the 30–100 ms sustained-energy
qualification by sampling `LEVEL` after waking. A false wake costs on the
order of 0.02 µAh; even hundreds of scratches a day are noise next to the
detector's own always-on budget. This supersedes the interview's "moderate
hardware strictness" choice — same behavior, relocated to firmware for zero
parts.

### 5. Fixed threshold

No trim. One resistor divider sets the coarse hardware trip; the exact 68 dB
is a firmware constant applied to `LEVEL` in dB domain, so unit-to-unit spread
collapses to the mic's own ±1–3 dB sensitivity tolerance — tighter than the
±3–4 dB originally accepted.

### 6. Bottom-port IP57 mic on a conformal-coated board (revised)

The interview chose a top-port mic, but the only component-level IP57 analog
MEMS part on the market (see part candidates below) is bottom-port — and IP57
was the requirement that mattered, so the port orientation yields. The mic
ports through a ~Ø1 mm hole in the module PCB, and the parent PCB must provide
an aligned acoustic pass-through (~Ø1.5–2 mm hole, or module placement over a
cutout/board edge) — the one acoustic integration requirement this design
places on the parent. Conformal coating protects the electronics.
**Assembly requirements: the coat must mask the mic body and the port hole,
and the port path must stay unobstructed.**

### 7. Tolerate a noisy shared rail

The parent product PWMs LEDs hard on the same battery. The detector is designed
to meet spec fed from that environment: RC filtering and heavy local
decoupling, with the GPIO feed's ~50–100 Ω source impedance as the series
element — no ferrite is fitted (cost-down). The first prototype should carry
test points to characterize how much LED noise actually reaches the mic path.
*(Assumed default — not yet confirmed.)*

### 8. Direct mode shares the `LEVEL` pad

The host budget allows a single ADC trace, so raw audio cannot get its own
signal pad. A 2:1 analog mux (SC70, <1 µA, ~$0.05–0.15) selects what `LEVEL`
carries: the envelope by default (module pull-up on `/RAW`), or the preamp's
raw band-limited audio while the host holds `/RAW` low. The host drives
`/RAW` open-drain — pull low to request direct mode, release to return —
which also eliminates any back-feed path into an unpowered module. The
envelope detector and wake comparator keep running in direct mode, and the
raw tap gives the bench test plan a probe point into the front end that a
conformal-coated board otherwise hides.

## Cost-down pass (2026-07-21)

This is a wearable: worn on the body, its realistic temperature swing is far
narrower than the 0–45 °C ambient spec, and the LED show consuming the dB
value is an aesthetic display, not an instrument. Accuracy in the
little-to-moderate band (roughly 1–10 %) is therefore tradable for parts cost,
board area, and assembly simplicity. Eliminated:

| Eliminated                                    | Function now provided by                                   | Accuracy price                                        |
| --------------------------------------------- | ---------------------------------------------------------- | ----------------------------------------------------- |
| Temperature-compensation network              | Moot — the linear-envelope revision removed the drifting junction entirely | None remaining                          |
| Hardware qualification window + one-shot stretch | EXTI pending-flag latch + firmware qualification         | None — behavior relocated, not removed                 |
| Hardware startup mask                         | Firmware delay before arming EXTI                           | None                                                   |
| Separate rectifier and envelope stages        | Single precision peak-detector op-amp                       | ~1–2 dB program-dependent (half-wave, crest factor)    |
| Log-conversion junction (analog dB output)    | Firmware `20·log10` lookup on 60 fps ADC samples            | Quantization below ~75 dB SPL; oversampling recovers most |
| Dedicated `LEVEL` output buffer               | Log op-amp output is already low-impedance                  | Negligible at 60 Hz ADC sampling                       |
| Active bandpass filter stages                 | Coupling caps (high-pass) + preamp GBW rolloff (low-pass)   | Soft band edges; a few % level error at band extremes  |
| Ferrite bead in supply filter                 | GPIO source impedance + RC + local decoupling               | None expected; verify on first prototype               |

Resulting active BOM: the mic, one dual-or-quad micropower op-amp package
(preamp channels + peak detector), one nanopower comparator, and the
direct-mode 2:1 mux — **four ICs plus roughly a dozen passives**, projected
parts cost ~$2–3 against the $4 target. After the linear-envelope revision, electrical accuracy is ~±0.5 dB
across the loud range that matters; absolute accuracy is dominated by the
mic's ±1–3 dB sensitivity spread.

## Part candidates and current budget (2026-07-21)

### Microphone: Infineon IM73A135V01

The only component-level IP57 analog MEMS mic on the market, and it happens to
be excellent. Datasheet V2.7 figures, low-power mode unless noted:

| Parameter | Value | Note |
| --- | --- | --- |
| Supply current | **70 µA typ / 80 µA max** | Normal mode: 170/230 µA — not needed here |
| Mode selection | By VDD level: 1.52–1.8 V = low power | Normal mode = 2.3–3.0 V |
| **Absolute max VDD** | **3.0 V — must never touch the 3.3 V rail** | Drives the 1.65 V mic-rail requirement |
| SNR / noise floor | 71 dB(A) / −109 dBV(A) | 73 dB(A) in normal mode |
| Acoustic overload | 130 dB SPL | Above the 115 dB design ceiling |
| Sensitivity | −38 dBV ±1 dB @ 94 dB SPL, differential | Single-ended tap ≈ −44 dBV |
| Output | Differential, Zout 500 Ω, 0.9 V DC | AC-coupled single-ended use is fine |
| Low-freq cutoff | 20 Hz | Coupling caps still set our ~50 Hz corner |
| Start-up | 10–30 ms | Inside the 100 ms firmware mask |
| Package | LLGA-5, 4×3×1.2 mm, **bottom port**, MSL1 | Port hole through module PCB required |
| Price / sourcing | ~$1.5–2 (Digi-Key/Mouser) | LCSC listing unconfirmed — JLC global sourcing or hand-place |

### Rail plan

Everything runs on the 3.3 V GPIO-fed rail **except the mic**, which gets a
1.65 V rail that simultaneously (a) respects the 3.0 V absolute max and
(b) selects 70 µA low-power mode. Implementation: a high-value divider
buffered by the spare channel of the quad op-amp — no extra IC. (Fallback: a
fixed 1.6 V micro-LDO, IQ <1 µA, as a fifth IC.)

### Current budget

Quad op-amp channel allocation: preamp, peak detector, mic-rail buffer,
mid-rail bias buffer.

| Block | Typ (µA) | Notes |
| --- | --- | --- |
| Mic, low-power mode | 70 | 80 max |
| Quad op-amp (4 ch) | 2.4 – 40 | MCP6144-class 0.6 µA/ch ↔ TLV9044-class 10 µA/ch |
| Comparator (TLV7031-class) | 0.3 | Plus ~1 µA threshold divider |
| Analog mux (74LVC1G3157) | ~0.1 | Static |
| Dividers, bleeds, bias strings | ~5 | High-value resistors throughout |
| **Total** | **~78–116 µA typ** | **≤ ~130 µA worst-case — 3× under the 350 µA budget** |

At ~90 µA system draw the detector alone runs ~230 days on a 500 mAh cell.
Op-amp trade to settle at schematic time: MCP614x (0.6 µA/ch, 100 kHz GBW —
gain-25 puts the rolloff corner right at ~4 kHz naturally) vs TLV904x
(10 µA/ch, 350 kHz — quieter and stronger drive, needs a feedback cap for the
corner). Noise analysis says either is fine for ±0.5 dB envelope accuracy;
LCSC stock and price likely decide.

## Corner-case register

The failure modes the design must explicitly handle:

1. **Standby GPIO float** — host Standby mode unpowers the detector via the
   floating GPIO; Stop mode is mandatory in this power scheme (see decision 1).
2. **Power-on glitch on `/WAKE`** — when the GPIO snaps high, the analog
   chain's settling transient must not wake the host. Handled entirely in
   firmware (no hardware mask is fitted): the EXTI is not armed until ~100 ms
   after power-up, so the comparator may chatter while settling — nothing is
   listening.
3. **Unpowered-module `/WAKE` line** — `/WAKE` is open-drain with **no on-board
   pull-up**. The host must not pull the line to an always-on rail while the
   detector is unpowered: current would back-feed through the module's ESD
   diodes (phantom powering), and a floating line reads as a spurious
   active-low wake. Firmware sequence: power GPIO high → wait out the startup
   mask → enable the MCU's internal pull-up → arm EXTI.
4. **`LEVEL` while off** — floats when the module is unpowered; firmware knows
   it cut the power and must not interpret the ADC reading.
5. **Loudness above 115 dB** — `LEVEL` must saturate gracefully at full scale
   (no foldback, no misbehavior); the LED animation simply pegs at max.
6. **Clothing rub vs. musical bass** — rub energy overlaps the bass band, so no
   filter corner alone separates them. Defense in depth: band shaping plus the
   firmware's 30–100 ms post-wake qualification (rub is bursty, music is
   sustained).
7. **LED PWM harmonics** — hard PWM on the shared rail lands harmonics inside
   the 50 Hz–4 kHz audio band electrically. Supply filtering and layout must
   keep them below the equivalent of the quietest resolvable dB step.
8. **Conformal coat vs. mic port** — one masking mistake mutes the product;
   this is a named assembly-process requirement, not a hope.
9. **dB-scale temperature drift** — *eliminated* by the linear-envelope
   revision: the rectifier diode sits inside the op-amp's feedback loop and
   cancels, and no log junction remains to drift.
10. **Threshold tolerance stack-up** — the effective 68 dB threshold is a
    firmware constant applied to `LEVEL`, so unit spread collapses to the
    mic's ±1–3 dB sensitivity tolerance; the coarse hardware trip absorbs its
    own ±3 dB of slop harmlessly (see corner case 12).
11. **GPIO rail droop** — the detector's current transients through the GPIO's
    source impedance modulate its own rail; local bulk capacitance must be
    sized so droop never reaches the analog references.
12. **Comparator offset at millivolt trip levels** — at linear-envelope
    levels, 68 dB SPL is ~15 mV, where nanopower comparator input offset
    (±3–5 mV) smears a trip point by several dB. The hardware trip therefore
    sits ~6 dB low (~62 dB ⇒ ~7 mV): worst-case positive offset still cannot
    push the trip above 68 dB (a unit that can't wake is a field failure),
    and negative offset only causes early wakes that firmware filters.
13. **`LEVEL` quantization at the quiet end** — below ~75 dB SPL a single
    12-bit read is coarser than 0.2 dB/count (1.2 dB at 60 dB). Firmware
    oversamples ~16× per 60 fps frame for ~2 extra effective bits; the LED
    show's 85–115 dB working range is unaffected.
14. **`/RAW` drive discipline** — the host must never drive `/RAW` high: the
    module pull-up defines the idle state, so the host GPIO runs open-drain
    (low = direct mode, released = envelope mode). Driving high into an
    unpowered module would back-feed the rail through ESD diodes (the corner
    case 3 hazard again). After toggling modes, firmware discards a few ms of
    `LEVEL` samples while the mux output settles.
15. **Mic supply window** — the IM73A135V01's absolute max is 3.0 V: it must
    never touch the 3.3 V rail. Its 1.65 V rail also *selects* low-power mode
    (1.52–1.8 V window): drifting above 1.8 V enters an undefined mode
    region, and dipping below 1.2 V trips the mic's brown-out. The buffered
    divider must hold 1.52–1.8 V across resistor tolerance and the host
    rail's real-world range.

## Host MCU integration (reference: WCH CH32V203)

### System power states

GPIO power means the power pin *is* the enable, and firmware selects between
three system states with no extra hardware:

| State | MCU mode | Power GPIO | System draw | What wakes it |
| --- | --- | --- | --- | --- |
| **Listening** | Stop (`LPDS=1`) | driven high | ~10.5 µA + detector (≤350 µA) | Sound via `/WAKE` EXTI (~76 µs), or any other EXTI/RTC |
| **Detector off, MCU napping** | Stop (`LPDS=1`) | driven low | ~10.5 µA | RTC alarm or other EXTI — e.g. periodic wake to decide whether to re-arm the mic |
| **Full off / shipping** | Standby | floats (automatic) | ~0.5–1.1 µA | Only WKUP pin, RTC alarm, or reset — **not sound** |

Two firmware nuances:

1. **Standby wake is a reset, not a resume.** Stop wake continues execution
   after WFI/WFE with RAM and GPIO state intact — which is why the power pin
   stays high through the sleep. Standby wake restarts from the reset vector
   (~4.8 ms) with GPIO config lost, so Standby is a true "off" state: enter it
   on user power-down, and return via a button on WKUP (or RTC).
2. **Re-entry sequencing applies every time the detector is re-powered.** Any
   transition into Listening — from Standby wake *or* from the detector-off
   Stop state — must rerun the corner-case-3 sequence: power pin high → wait
   out the ~100 ms startup mask → enable the `/WAKE` pull-up → arm EXTI.

### Wiring and firmware

- **Power**: one GPIO drives the module's `VDD`. Sleep in **Stop mode** (not
  Standby) so the pin stays high, with the regulator in low-power mode
  (`LPDS=1, PDDS=0`) for 10.5 µA instead of 70.5 µA.
- **Wake**: `/WAKE` to a wake-capable EXTI pin, falling-edge trigger, internal
  pull-up — enabled only after the power-up sequence in corner case 3.
- **Level**: `LEVEL` to a 12-bit ADC channel, polled at 60 Hz with ~16×
  oversampling per frame; `dB = 20·log10(reading) + offset` via a small
  lookup table. No temperature correction needed.
- **Wake qualification (firmware)**: on EXTI wake, sample `LEVEL` for
  30–100 ms and apply the true 68 dB threshold in dB domain; if the loudness
  isn't sustained above it, return to Stop immediately.
- **Direct mode**: `/RAW` from any host GPIO in open-drain mode; pull low,
  then sample `LEVEL` at ≥8–10 kHz (band is ≤4 kHz) and subtract the mid-rail
  bias in software. Release to return to envelope mode, discarding the first
  few ms of samples while the mux settles.

## Planned deliverables

*Assumed defaults from the interview (not yet confirmed):*

- KiCad project: schematic, layout, fab outputs, checked into this repo.
- SPICE simulation of the mic-to-outputs chain: filter corners, envelope
  timing, envelope linearity, threshold/trip behavior.
- Bench validation test plan: reference tones at known dB SPL, rub-noise
  reproduction, supply-current measurement, threshold verification.
- Firmware integration notes with a CH32V203 example: Stop-mode config, EXTI
  wake, startup masking, pull-up sequencing, 60 fps sampling.

## Scope

This repository covers **only the discrete sound-detection breakout**: circuit
design, part selection, board layout, and validation.

The parent product — a crystal ornament lit by heavily PWM-driven LEDs that
reacts to music at events — is out of scope, as are the host MCU firmware
proper and the LED drive electronics.

## Open questions

- Exact bandpass corner frequencies for the bass + voice band.
- Mic sourcing: IM73A135V01 confirmed at Digi-Key/Mouser (~$1.5–2); LCSC/JLC
  listing unconfirmed — JLC global sourcing or hand-placement if absent.
- Op-amp family: MCP614x (0.6 µA/ch, 100 kHz) vs TLV904x (10 µA/ch, 350 kHz)
  — noise, output drive, and LCSC stock decide.
- Parent-side acoustic pass-through geometry for the bottom port.
- Peak-detector attack/release network values and the realized full-scale
  calibration constant (which SPL hits ADC full scale).
- Comparator part choice — the input-offset spec sets how low the coarse trip
  must sit.
- Analog mux part choice for direct mode (on-resistance, leakage, JLC stock).
- Firmware qualification window tuning (within 30–100 ms) and EXTI re-arm
  policy.
- Module dimensions and castellation pinout order.

## Status

Requirements fleshed out via design interview, cost-down pass, linear-envelope
revision, and direct-mode addition; mic candidate selected and current budget
drafted (2026-07-21). Next: schematic capture and SPICE validation of the
analog chain.
