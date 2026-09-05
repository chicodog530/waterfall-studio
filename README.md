# Waterfall Studio 0.3.4

Waterfall Studio converts text, drawings, presets, and imported artwork into
multitone audio for experimental waterfall-image transmission.

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python checks](https://github.com/chicodog530/Waterfall-Studio/actions/workflows/python-checks.yml/badge.svg)](https://github.com/chicodog530/Waterfall-Studio/actions/workflows/python-checks.yml)

> **Alpha software:** Waterfall Studio can key connected radio equipment. Begin
> with PTT disabled or a low-power controlled test path and monitor every test.

## Features

- Full-bandwidth sequential letters that stack clearly down a waterfall.
- Correctly timed punctuation and independent letter/word gaps.
- Imported artwork, freehand drawing, radio-friendly presets, and calibration
  patterns.
- Per-preset transmission profiles for independently tuning duration and channel
  processing, including a tall full-body alien preset.
- Channel-aware detail, threshold, gamma, line thickness, aspect, mirroring,
  and orientation controls with predicted received preview.
- Separate TX and RX audio-device selection.
- VOX, serial RTS/DTR, and Yaesu FT-710 CAT PTT.
- Timed callsign beacon with unsquelched-HF listen-before-transmit and automatic
  busy-channel retry.
- Optional 700 Hz, 18 WPM CW callsign identification appended after each
  waterfall transmission.
- Animated FFT waterfall built from the generated audio—not just the source
  artwork—at 1x, 4x, or 10x preview speed.
- Hamlib `rigctld` PTT support for a broad range of radio models.
- WAV export for testing or use with another audio application.

## Documentation

- [Complete operating instructions](docs/USER_GUIDE.md)
- [Developer architecture and release guide](docs/DEVELOPMENT.md)
- [Hamlib radio setup](docs/HAMLIB.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)
- [Security and operating safety](SECURITY.md)

## Windows 11

Install Python 3.11 or newer from python.org and enable **Add Python to PATH**.
Extract the complete folder and double-click `installer.bat` once. It creates a
local `.venv`, installs and verifies every Python dependency inside it, and
reports whether optional Hamlib is available. Afterwards, use `run_windows.bat`.

## Linux

Install Python 3.11+, `python3-venv`, and PortAudio using your distribution's
package manager. Run `chmod +x installer.sh run_linux.sh`, then run
`./installer.sh` once and `./run_linux.sh` to launch.

## Workflow

1. **Create:** Enter text, select whole-artwork or sequential-letter layout,
   import an image, choose an RF-safe preset, or load a calibration pattern.
2. **Optimize:** Set the passband, duration, resolvable frequency rows,
   threshold, line thickness, aspect correction, and received orientation.
3. **Radio:** Select separate TX-output and RX-input audio endpoints. Configure
   VOX, RTS, DTR, or FT-710 CAT PTT.
4. **Preview:** Compare the source, processed prediction, and FFT of the actual
   generated audio. Replay the scrolling FFT at 1x, 4x, or 10x.
5. Generate audio, save a WAV, or transmit/play it.

The Radio tab also includes a callsign beacon. Enter the callsign and interval,
then start the beacon to send once immediately and automatically repeat at the
selected start-to-start interval. Intervals as short as 0.1 minute are available
for testing; choose an interval appropriate for normal operation and identification.

Optional listen-before-transmit samples the selected radio RX audio input before
manual or beacon transmissions. It is designed for unsquelched HF audio: first
use **Calibrate clear-channel noise** while the frequency is clear. The app saves
that noise baseline and considers the channel busy when the 90th-percentile
100 ms audio level exceeds it by the selected margin. A manual transmission is
cancelled; a beacon is deferred by the configured retry delay. A 4–6 dB margin
is a useful starting point, but AGC behavior and local noise require testing.

Long text uses a dynamically expanding canvas and is not clipped. **One letter
at a time** is the default text layout. In that mode, Duration means seconds
per letter: every glyph receives the full selected time and full frequency
width, followed by the independently adjustable inter-letter gap. Adding more
letters therefore increases total transmission time instead of compressing the
letters side by side.

Sequential text preserves each glyph's time geometry. Full-height letters use
the selected seconds-per-letter value, while punctuation such as periods,
commas, apostrophes, quotation marks, dashes, and asterisks is automatically
shortened in proportion to its printed height. This prevents a period from
being stretched into a long waterfall bar.

Built-in picture presets are tightly cropped, expanded across the usable
bandwidth, and drawn with stronger details that survive radio filtering.
The Skull, Alien head, UFO, and Radio tower lightning presets are also supplied
as standalone 360 x 120, two-colour PNG files in the `artwork` folder.

## Radio and PTT

- FT-710 CAT PTT sends `TX1;` to key and `TX0;` to release.
- Hamlib-supported radios use a running `rigctld` server, normally at
  `127.0.0.1:4532`. Select **Hamlib rigctld** as the PTT method.
- For a G90, select VOX, RTS, or DTR according to the interface wiring.
- PTT lead and tail delays prevent clipping at the start and end.
- When VOX is selected, an adjustable low-level guard tone is automatically
  placed before the first image and after the last. This lets the transmitter
  key and settle before the first letter, and keeps it keyed until the final
  letter is complete. Set the radio's VOX delay longer than the inter-letter
  gap so it does not drop between characters.
- The selected RX-input endpoint is used for HF noise-floor calibration,
  listen-before-transmit, and busy-channel beacon deferral.

## Calibration

Start with **Square** and adjust **Waterfall aspect** until it arrives square.
Frequency Bars reveal lost or merged detail. Timing Bars reveal waterfall
scroll and time-resolution behavior.

The Create tab shows the actual stacked transmit sequence whenever one-letter
mode is active. Normal and bold font weights are available; Normal usually
leaves more open space inside curved letters on a weak waterfall. Orientation,
aspect, timing, processing, radio, and audio selections persist between runs.

Freehand drawing is disabled while the stacked-letter result is being shown,
so accidental clicks cannot corrupt text frames. In artwork mode, every mouse
drag is stored as a separate stroke; independent clicks and strokes are never
joined by unwanted diagonal lines.

**Flip each letter vertically (Q-tail fix)** compensates for the reversed time
axis of a conventional scrolling waterfall. It is enabled by default and is
independent of Reverse letter order: one fixes each glyph, while the other
changes the order of the stacked characters.

Sequential glyphs are cropped to their visible top and bottom before rotation,
removing hidden font margins that previously created delay even when Letter gap
was zero. A typed space is no longer synthesized as a full-duration blank
letter; it uses the separate **Gap for a typed space** value. Consequently,
Letter gap 0.00 begins the next visible character immediately.

The **Resolvable detail** setting is deliberately more important than source
resolution. Hundreds of adjacent tones squeezed into a 3 kHz channel merge.
Start around 64–80 rows, line thickening 1, and modest audio drive. Disable
speech processing and compression.

Observe applicable frequency, emission, bandwidth, identification, power, and
interference rules. Test at low power into a suitable load or controlled path.
