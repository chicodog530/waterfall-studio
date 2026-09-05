# Developer guide

## Architecture

Waterfall Studio is split into focused modules:

- `constants.py`: version and shared option lists.
- `image_processing.py`: orientation, trimming, sizing, and channel simulation.
- `dsp.py`: synthesis, HF activity measurement, VOX guards, and FFT analysis.
- `radio.py`: direct serial/CAT, Hamlib rigctld, and background playback.
- `ui.py`: widgets, state, previews, beacon scheduling, and settings.
- `waterfall_studio.py`: stable, backward-compatible launcher.

## Signal model

For a processed image with `R` rows and `C` columns, rows are linearly mapped
between the selected low and high audio tones. Each column occupies an equal
time slice. Pixel intensity controls tone amplitude. Adjacent columns are
interpolated, while oscillator phase continues across boundaries to avoid
broadband clicks.

The mixed signal is normalized by approximately the square root of the active
tone count before final peak normalization. This reduces large loudness changes
between sparse and dense columns, but the operator must still set safe drive.

`channel_image()` first applies threshold and gamma, resamples to the selected
frequency-row count, then optionally applies a maximum filter for line
thickening. The predicted preview reverses the transmit transformation so it
resembles a conventional received waterfall.

## Sequential text

Each non-space character is rendered independently, stripped of vertical font
whitespace, oriented, channel-processed, and synthesized. Consequently, adding
characters increases total time instead of squeezing their frequency span.

The trimmed glyph height determines airtime relative to a rendered capital H.
This preserves punctuation geometry: a period receives only a fraction of the
full letter duration. Spaces are represented separately by the word-gap value.

## Listen-before-transmit

The selected RX endpoint is sampled at 48 kHz. Audio is divided into 100 ms
blocks and RMS is calculated for each. The 90th percentile is used as the
activity level, which responds to sustained or intermittent signals but is less
sensitive to a single impulse. The channel is considered busy when:

```text
measured_activity_dBFS >= calibrated_noise_dBFS + busy_margin_dB
```

This is intentionally user-calibrated because receiver AGC, bandwidth, volume,
and sound interfaces make an absolute threshold unreliable on HF.

## Beacon state

The beacon uses a single-shot `QTimer`. Starting sends immediately. Successful
worker completion schedules the remaining time in the requested start-to-start
period. A busy-channel result schedules the shorter retry interval instead.
Only one audio worker is allowed at a time.

## FFT preview

`audio_spectrogram()` uses a Hann-windowed 4096-point real FFT with 1024-sample
hop size. It keeps bins inside the selected transmit tone range, converts them
to log magnitude, and normalizes between the 25th and 99.7th percentiles. Rows
represent successive time frames and columns represent frequency. The UI timer
reveals those rows in a fixed-height scrolling window without re-running FFTs.

## Radio backends

Direct FT-710 CAT remains available for a zero-dependency common path. Hamlib
support connects to `rigctld` over TCP and uses its `T 1`/`T 0` PTT commands.
This keeps manufacturer/model protocol handling outside Waterfall Studio and
allows remote rig control. RTS, DTR, and VOX remain model-independent options.

## Settings

`QSettings("KE0CGB", "WaterfallStudio")` stores a JSON profile. New keys must
have defaults in `restore_settings()` so older profiles remain compatible.
Never automatically restore an actively transmitting or beacon-running state.

## Adding a preset

1. Add its label to `PRESETS`.
2. Draw a high-contrast monochrome shape in `make_preset()`.
3. Use thick, separated features; fine detail will not survive a narrow channel.
4. Return through `expand_preset_art()` so empty margins do not waste bandwidth.

Complex presets may instead be stored as 360 x 120 black-and-white PNG files in
`artwork/` and mapped by name in `MainWindow.make_preset()`. Keep silhouettes
bold and detail sparse: thin lines and small isolated marks rarely survive a
narrow HF audio passband.
5. Check both previews and make a low-power controlled RF test.

## Release checklist

1. Update `APP_VERSION` in `constants.py`, `pyproject.toml`, README, and CHANGELOG.
2. Run `python -m py_compile *.py`.
3. Test text, punctuation, art, WAV saving, manual play, every supported PTT
   method available to you, channel calibration, busy deferral, and beacon stop.
4. Verify a clean installation on Windows and Linux.
5. Never commit generated WAV files, local virtual environments, or station
   configuration.

Core regression tests run without Qt or radio hardware:

```bash
PYTHONPATH=. python -m unittest discover -s tests -v
```
