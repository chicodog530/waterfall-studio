# Changelog

## 0.3.4

- Crop the full-body alien's unused side margins and expand the figure across
  the available audio-tone span, making its head and body much wider on air.
- Retain its long 20-second, 4.0-aspect factory transmission profile.

## 0.3.3

- Add a full-body alien designed to transmit about four character-heights tall.
- Add independently saved profiles for every artwork preset, covering duration,
  tone range, detail, threshold, gamma, thickening, aspect, and orientation.

## 0.3.2

- Add a Create-tab checkbox and callsign field for appending a CW station ID.
- Generate the ID at 700 Hz and 18 WPM after a short separation from the
  waterfall image, and retain the settings between runs.

## 0.3.1

- Add four high-contrast, radio-friendly artwork presets: Skull, Alien head,
  UFO, and Radio tower lightning.
- Ship the original 360 x 120 two-colour PNG files in the `artwork` folder for
  direct loading and reuse.

## 0.3.0

- Split the application into UI, DSP, image-processing, radio, and constants
  modules while preserving the original launcher.
- Add an animated scrolling FFT preview calculated from generated audio.
- Add Hamlib `rigctld` PTT for broad radio-model compatibility.
- Add isolated Windows and Linux installers and update the launch scripts.

## 0.2.10

- Document installation, operation, calibration, beaconing, and troubleshooting.
- Add developer architecture and release notes throughout the source.
- Add GitHub packaging, contribution, security, issue-template, and CI files.

## 0.2.9

- Scale punctuation airtime to its rendered geometry.
- Prevent periods and small marks from becoming long waterfall bars.

## 0.2.8

- Add unsquelched-HF noise-floor calibration and listen-before-transmit.
- Defer a busy callsign beacon by a configurable retry delay.

## 0.2.7

- Add an automatic callsign beacon with saved interval settings.

## 0.2.6

- Expand and strengthen built-in artwork presets.

## 0.2.5

- Remove hidden glyph timing margins and add a separate word-gap control.

## 0.2.0–0.2.4

- Add channel-aware preview and synthesis.
- Add sequential letters, orientation controls, calibration images, separate
  TX/RX audio selection, VOX guards, and serial/CAT PTT.
