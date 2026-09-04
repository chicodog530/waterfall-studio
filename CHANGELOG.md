# Changelog

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
