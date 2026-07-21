# soundwake

A low-power, always-on sound-level detector breakout board that wakes a sleeping
MCU when the music starts.

`soundwake` is a discrete analog circuit built around a water- and dust-resistant
(IP57-class) analog MEMS microphone. It continuously measures the ambient sound
pressure level (SPL) in the combined **bass + voice** band and exposes the result
on two pins: an analog loudness output and an active-low wake interrupt. It is
designed to be the always-on watchdog subsystem of a battery-powered,
sound-reactive product, drawing well under 350 µA while everything else sleeps.

## What it does

- **Measures loudness, not audio.** The board outputs a slowly varying envelope
  voltage proportional to the current dB SPL — a signal an MCU ADC can poll,
  not a raw microphone waveform.
- **Wakes the host on loud sound.** When the level in the detection band exceeds
  ~68 dB SPL, the `/WAKE` pin drives low and holds long enough for a sleeping
  MCU to wake, boot, and catch the event.
- **Listens to music and people, ignores the wearer.** The detection band covers
  musical bass through the human voice range. Handling noise — the enclosure
  rubbing against clothing — is an explicit rejection target.

## Interface

| Pin     | Direction | Description                                                        |
| ------- | --------- | ------------------------------------------------------------------ |
| `VDD`   | power     | Supply input                                                       |
| `GND`   | power     | Ground                                                             |
| `LEVEL` | out       | Analog voltage proportional to current dB SPL in the detection band |
| `/WAKE` | out       | Active-low wake interrupt; asserts when SPL > ~68 dB, with hold     |

## Target specifications

All values are design targets; the project is in the design phase.

| Parameter             | Target                          | Notes                                          |
| --------------------- | ------------------------------- | ---------------------------------------------- |
| Total supply current  | **< 350 µA**, lower is better   | Always-on; battery runtime is a primary driver |
| Supply voltage        | 3.3 V nominal (range TBD)       | Must coexist with the host MCU rail            |
| Detection band        | ~50 Hz – 4 kHz (bass + voice)   | Exact corners TBD                              |
| Wake threshold        | ~68 dB SPL                      | Adjustability TBD                              |
| Wake hold time        | TBD                             | ≥ host wake latency with margin                |
| Envelope readout rate | Valid at 60 Hz polling          | Envelope settles within a ~16 ms window        |
| `LEVEL` scaling       | Linear-in-dB preferred (TBD)    | Sized for a 12-bit ADC over the supply rail    |
| Microphone            | Analog MEMS, IP57 water/dust    | Part selection TBD                             |

## Detection band and filtering

The detector responds to both the kick/bassline of event music and to people
talking, singing, or shouting near the device — roughly the 50 Hz – 4 kHz
region. Both the `LEVEL` output and the wake threshold operate on this combined
band, implemented as an analog bandpass in the signal chain.

### Handling-noise rejection

The device is worn or carried, so the microphone will pick up scratching and
rubbing of the enclosure against clothing. That contact noise must neither
inflate `LEVEL` nor false-trigger `/WAKE`.

This is the central design tension of the project: clothing-rub noise carries
significant energy in the same low-frequency region as musical bass, so a
high-pass corner alone cannot separate them. The planned mitigations are a
combination of:

- **Filter shaping** — placing the low corner to keep kick-drum energy while
  shedding the deepest rumble.
- **Acoustic/mechanical design** — mic port placement and isolating the mic
  from the enclosure so rub energy couples in weakly.
- **Temporal character** — music above the threshold is sustained; rubbing is
  bursty. Envelope attack/release time constants discriminate between them.

## Wake behavior

`/WAKE` is an active-low digital output. When the in-band SPL crosses the
threshold, the pin asserts and is held asserted long enough for the host to wake
from deep sleep and reach code that can observe it. The exact hold time (or
whether a latch cleared by the host is preferable) is an open question, sized
against the host MCU's wake latency.

## Host MCU integration (reference: WCH CH32V203)

The reference host is the WCH CH32V203 (RISC-V, CH32V family):

- `LEVEL` feeds a 12-bit ADC channel, polled at 60 Hz to drive LED animation
  at frame rate.
- `/WAKE` connects to a wake-capable EXTI pin to bring the MCU out of
  standby/deep sleep.
- The CH32V203's wake latency is short (sub-millisecond to low milliseconds),
  so the hold-time requirement is modest — but hold/latch behavior must make
  the event impossible to miss.

## Scope

This repository covers **only the discrete sound-detection breakout**: circuit
design, part selection, board layout, and validation.

The parent product — a crystal ornament lit by heavily PWM-driven LEDs that
reacts to music at events — is out of scope, as are the host MCU firmware and
LED drive electronics.

## Open questions

- Exact bandpass corner frequencies for the bass + voice band.
- `/WAKE` hold time value, and hold vs. latch-until-cleared behavior.
- Whether the 68 dB SPL threshold should be field-adjustable (trim resistor /
  solder-jumper options).
- `LEVEL` transfer function (linear-in-dB vs. linear-in-amplitude) and output
  voltage range.
- Supply voltage range and brown-out behavior.
- Connector / form factor of the breakout.

## Status

Design phase. No schematic or layout yet; this README is the working design
specification.
