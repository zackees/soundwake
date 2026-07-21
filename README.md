# soundwake

A low-power, always-on sound-level detector breakout board that wakes a sleeping
MCU when the music starts.

`soundwake` is a discrete analog circuit built around a water- and dust-resistant
(IP57-class) analog MEMS microphone. It continuously measures the ambient sound
pressure level (SPL) in the combined **bass + voice** band and exposes the result
on two pins: an analog dB-scaled loudness output and an active-low wake
interrupt. It is designed to be the always-on watchdog subsystem of a
battery-powered, sound-reactive product, drawing well under 350 µA while
everything else sleeps.

## What it does

- **Measures loudness, not audio.** The board outputs a slowly varying voltage
  proportional to the current **dB SPL** — a signal an MCU ADC can poll, not a
  raw microphone waveform. The dB conversion happens in hardware (log
  detection), so a linear voltage step is a linear dB step and cheap ADCs read
  it with uniform resolution across the whole loudness range.
- **Wakes the host on loud sound.** When the in-band level exceeds ~68 dB SPL
  for a short qualification window, the `/WAKE` pin drives low as a one-shot
  stretch long enough for a sleeping MCU to wake, boot, and catch the event.
- **Listens to music and people, ignores the wearer.** The detection band covers
  musical bass through the human voice range. Handling noise — the enclosure
  rubbing against clothing — is an explicit rejection target.
- **Powers from a host GPIO pin.** The whole detector is powered by one MCU
  GPIO driven high, so the product is default-off and the host can cut the
  detector to zero at any time.

## Interface

Castellated-edge SMT module, four pads. Reflows onto the parent PCB like a
component; solders onto a carrier or headers for bench work.

| Pad     | Direction | Description                                                            |
| ------- | --------- | ---------------------------------------------------------------------- |
| `VDD`   | power     | Supply input, fed directly from a host GPIO pin (see power model below) |
| `GND`   | power     | Ground                                                                  |
| `LEVEL` | out       | Analog voltage, linear-in-dB, spanning 60–115 dB SPL in-band            |
| `/WAKE` | out       | Active-low one-shot wake pulse; open-drain, host provides the pull-up   |

## Target specifications

| Parameter              | Target                                | Notes                                                    |
| ---------------------- | ------------------------------------- | -------------------------------------------------------- |
| Total supply current   | **< 350 µA**, lower is better         | Always-on while product is on; battery runtime driver    |
| Power source           | Host GPIO pin, 3.3 V nominal          | Default-off product; GPIO ~50–100 Ω source impedance     |
| Detection band         | ~50 Hz – 4 kHz (bass + voice)         | Exact corners TBD                                        |
| Wake threshold         | 68 dB SPL, fixed                      | ±3–4 dB unit-to-unit accepted (mic + resistor tolerance) |
| Wake qualification     | ~30–100 ms sustained over-threshold   | Rejects single scratches; music still wakes fast         |
| Wake stretch           | ~100 ms one-shot, retriggering        | Sized against CH32V203 wake latency with wide margin     |
| `LEVEL` transfer       | Linear-in-dB (hardware log detection) | 60–115 dB SPL mapped across the output swing (~55 dB)    |
| Envelope dynamics      | Beat-tracking: ~1–5 ms attack, ~100–300 ms release | LEDs can ride individual kicks at 60 fps    |
| Envelope readout rate  | Valid at 60 Hz polling                | Fresh, settled values every ~16 ms                       |
| Microphone             | Analog MEMS, IP57, **top-port**       | Part selection TBD                                       |
| Operating environment  | 0–45 °C, mild outdoor                 | Rain resistance via mic IP rating + conformal coat       |
| Board protection       | Conformal coating                     | Coating must mask the mic port (assembly requirement)    |
| BOM cost               | < ~$4 at small-run quantity           | *Assumed default — not yet confirmed*                    |
| Assembly               | JLCPCB SMT (design to their catalog)  | *Assumed default — not yet confirmed*                    |

## Architecture decisions

Decisions from the 2026-07-21 design interview, with rationale.

### 1. Power via host GPIO, default-off

The detector's `VDD` is a CH32V203 GPIO driven high. This makes the product
default-off with zero leakage, and gives the host a free kill switch.

The trap this creates: in the CH32V203's deepest **Standby** mode, GPIOs go
high-impedance — the detector would lose power exactly when it should be
listening, and nothing could ever wake the MCU. Therefore the host **must sleep
in Stop mode**, where GPIO output states are retained. Stop mode draws more
than Standby (tens of µA vs. a couple of µA — exact figure to be verified
against the datasheet). If measured Stop current is unacceptable, the
documented fallback is a latching load switch: the MCU pulses power on, a
discrete latch holds it, and Standby becomes usable again.

A side benefit: the GPIO's ~50–100 Ω source impedance plus the module's local
bulk capacitance forms a free low-pass filter against rail noise.

### 2. Hardware dB output (log detection)

`LEVEL` is linear-in-dB, not linear-in-amplitude. Rationale: a dB-linear signal
uses cheap, low-resolution ADCs efficiently — every dB gets the same number of
counts, whereas a linear envelope wastes resolution on the loud end and drowns
the quiet end in ADC error. The host algorithm works entirely in dB, so
firmware just applies scale and offset.

This is the hardest block to keep micro-power (commercial log amps draw mA).
The planned approach is log conversion of the *envelope* (a slow signal, so a
micropower op-amp + transistor junction suffices) rather than logging the audio
itself. The BJT-junction log scale factor drifts with temperature; over the
0–45 °C range this needs either simple compensation or a documented dB/°C
error budget firmware can correct.

### 3. Beat-tracking envelope everywhere

One fast envelope (~1–5 ms attack, ~100–300 ms release) feeds both `LEVEL` and
the wake path. LEDs can pulse with individual kick drums at 60 fps. The cost —
scratches look like kicks — is paid back in the wake path by time
qualification, not by slowing the envelope.

### 4. Wake path: threshold → qualification → stretch

Comparator with hysteresis at 68 dB SPL → ~30–100 ms sustained-energy
qualification → ~100 ms active-low one-shot stretch, retriggering while loud.
Moderate hardware strictness; the firmware completes the filter: on wake, the
MCU samples `LEVEL` briefly, and if the world is quiet it goes straight back to
sleep. A rare false wake costs milliseconds of run time.

### 5. Fixed threshold

No trim. One resistor divider sets 68 dB; ±3–4 dB unit-to-unit spread from mic
sensitivity and resistor tolerance is accepted. "About 68 dB" is the spirit of
the spec.

### 6. Top-port mic on an open, conformal-coated board

The breakout hangs in free air inside the product with a top-port mic facing
away from the PCB; the IP57 mic tolerates splash and dust, and conformal
coating protects the electronics. No gasketed enclosure port is assumed —
acoustic integration requirements on the parent product stay minimal.
**Assembly requirement: the conformal coat must mask the mic port.**

### 7. Tolerate a noisy shared rail

The parent product PWMs LEDs hard on the same battery. The detector is designed
to meet spec fed from that environment: RC/ferrite filtering, heavy local
decoupling, and the GPIO-feed low-pass. The first prototype should carry test
points to characterize how much LED noise actually reaches the mic path.
*(Assumed default — not yet confirmed.)*

## Corner-case register

The failure modes the design must explicitly handle:

1. **Standby GPIO float** — host Standby mode unpowers the detector via the
   floating GPIO; Stop mode is mandatory in this power scheme (see decision 1).
2. **Power-on glitch on `/WAKE`** — when the GPIO snaps high, the analog
   chain's settling transient must not assert `/WAKE`. Hardware startup mask of
   ~100 ms after power-up; firmware additionally ignores `/WAKE` during that
   window.
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
   filter corner alone separates them. Defense in depth: band shaping, the
   30–100 ms wake qualification (rub is bursty, music is sustained), and the
   firmware double-check.
7. **LED PWM harmonics** — hard PWM on the shared rail lands harmonics inside
   the 50 Hz–4 kHz audio band electrically. Supply filtering and layout must
   keep them below the equivalent of the quietest resolvable dB step.
8. **Conformal coat vs. mic port** — one masking mistake mutes the product;
   this is a named assembly-process requirement, not a hope.
9. **dB-scale temperature drift** — the log stage's mV/dB slope moves with
   temperature; over 0–45 °C the design must either compensate or publish a
   dB/°C figure firmware can correct.
10. **Threshold tolerance stack-up** — mic sensitivity (±1–3 dB) + divider
    tolerance ⇒ ±3–4 dB unit spread on the 68 dB trip point; accepted by
    decision 5, but the stack-up must be verified in design review.
11. **GPIO rail droop** — the detector's current transients through the GPIO's
    source impedance modulate its own rail; local bulk capacitance must be
    sized so droop never reaches the analog references.

## Host MCU integration (reference: WCH CH32V203)

- **Power**: one GPIO drives the module's `VDD`. Sleep in **Stop mode** (not
  Standby) so the pin stays high.
- **Wake**: `/WAKE` to a wake-capable EXTI pin, falling-edge trigger, internal
  pull-up — enabled only after the power-up sequence in corner case 3.
- **Level**: `LEVEL` to a 12-bit ADC channel, polled at 60 Hz;
  `dB = scale × ADC + offset` with constants from the module datasheet
  (optionally temperature-corrected per corner case 9).
- **False-wake handling**: on wake, sample `LEVEL` for a few frames; if quiet,
  return to Stop immediately.

## Planned deliverables

*Assumed defaults from the interview (not yet confirmed):*

- KiCad project: schematic, layout, fab outputs, checked into this repo.
- SPICE simulation of the mic-to-outputs chain: filter corners, envelope
  timing, dB linearity, threshold/qualification behavior.
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
- Mic part selection: analog, IP57, top-port, micro-power, JLC-availability.
- CH32V203 Stop-mode current: verify datasheet figure; decide whether the
  latching-load-switch fallback is needed.
- Log-stage topology and its temperature-compensation scheme.
- Final wake qualification and stretch time constants.
- Module dimensions and castellation pinout order.

## Status

Requirements fleshed out via design interview (2026-07-21). Next: mic part
selection and a block diagram with a stage-by-stage current budget.
