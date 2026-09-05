# Waterfall Studio user guide

## What it does

Waterfall Studio converts text or monochrome artwork into multitone audio. When
that audio passes through an SSB transmitter, each audio tone appears at a
different position across a receiver's waterfall. The image is painted over
time as the waterfall scrolls.

This is experimental image audio, not a weak-signal modem. Results depend on
transmit filtering, receiver filtering, AGC, waterfall speed, noise, propagation,
and audio drive.

## Installation

### Windows 11

1. Install 64-bit Python 3.11 or newer from python.org.
2. Enable **Add Python to PATH** in the installer.
3. Extract the complete Waterfall Studio folder.
4. Double-click `installer.bat` once.
5. Double-click `run_windows.bat` for normal use.

### Linux

PortAudio and Qt system packages may be required. On Ubuntu/Debian:

```bash
sudo apt install python3-venv libportaudio2
chmod +x installer.sh run_linux.sh
./installer.sh
./run_linux.sh
```

## First controlled test

1. Use minimum practical RF power and a dummy load, attenuated monitor path, or
   other controlled arrangement.
2. Connect the computer's selected output to the radio data or microphone input.
3. Disable speech compression, equalization, noise reduction, and transmit audio
   processing.
4. Select USB and a transmit passband that contains the chosen audio tones.
5. In **Create**, enter one large letter.
6. In **Optimize**, start with 500–2800 Hz, 5 seconds per letter, 64–80 frequency
   rows, threshold 35, gamma 1.0, and line thickening 1.
7. In **Radio**, select the radio TX audio output and configure VOX or PTT.
8. Check **Preview**, generate the audio, then transmit.
9. Adjust audio drive until the ALC is low or inactive and the received image is
   clean. More drive usually makes a worse image once clipping or ALC begins.

## Create tab

- **Text:** Message to render.
- **Font size/weight:** Changes the glyph source. Normal weight often keeps the
  centers of O, D, and similar letters open on narrow channels.
- **One letter at a time:** Gives every letter the full available bandwidth and
  stacks the characters down the waterfall. Long messages increase duration.
- **Reverse letter order:** Reverses the character sequence.
- **Flip each letter vertically:** Corrects the time reversal seen on many
  conventional scrolling waterfalls. It is independent of letter order.
- **Load image:** Imports PNG, JPEG, or BMP artwork.
- **Clear loaded art:** Returns to text mode.
- **Presets:** Radio-friendly built-in artwork expanded to the usable canvas,
  including Skull, Alien head, full-body Alien, UFO, and Radio tower lightning
  designs. Load a preset, tune it on the Optimize tab, then select **Save preset
  settings** to remember its duration and channel-processing controls separately
  from every other preset. The full-body alien defaults to 20 seconds and 4.0
  waterfall aspect so it is roughly four letter-heights tall. Its empty margins
  are removed automatically so the figure also fills the available tone span.
- **Send CW ID after transmission:** Appends the callsign entered beside it as
  a 700 Hz, 18 WPM CW identifier after the waterfall audio. This also applies
  to each automatic beacon transmission when enabled.
- **Calibration:** Patterns for diagnosing geometry and lost detail.

Punctuation automatically receives less airtime than a full-height letter. A
period therefore remains a dot instead of becoming a long bar.

## Optimize tab

- **Lowest/highest audio tone:** The occupied audio range. Keep it inside the
  radio's transmit and receiver passbands.
- **Seconds per letter / total duration:** Airtime for a full glyph in sequential
  mode, or the entire picture in artwork mode.
- **Gap between letters:** Silence between adjacent visible characters.
- **Gap for a typed space:** Word spacing; it does not consume a full glyph.
- **Output level:** Digital output amplitude. It is not an RF power control.
- **Resolvable detail:** Number of frequency rows synthesized after channel
  processing. Too many rows in a narrow SSB channel merge together.
- **Brightness threshold:** Removes dim image pixels before synthesis.
- **Gamma:** Changes brightness distribution.
- **Line thickening:** Makes thin details survive filtering and noise.
- **Waterfall aspect:** Corrects time-versus-frequency stretching.
- **Received orientation/mirroring:** Compensates for receiver display direction
  and sideband/orientation differences.

Use **Square** calibration first. Adjust Waterfall aspect until it arrives
square. Then use Frequency bars to find useful detail and Timing bars to check
scroll speed.

## Radio tab

### Audio and PTT

Choose separate TX output and RX input endpoints. The output should feed the
radio; the input should receive monitor or receiver audio. Refresh the lists
after attaching a USB interface.

- **VOX:** Adds guard tones before and after the picture. Set radio VOX delay
  long enough that it does not release between characters.
- **RTS/DTR:** Keys a compatible interface through the selected serial port.
- **FT-710 CAT:** Uses `TX1;` and `TX0;` at the selected baud rate.
- **Hamlib rigctld:** Supports the radio models available in the installed
  Hamlib version. Configure and start `rigctld` for the radio, select **Hamlib
  rigctld**, and enter its host and port (normally `127.0.0.1:4532`). Waterfall
  Studio sends Hamlib PTT commands; rigctld owns the radio-specific protocol.
- **PTT lead/tail:** Allows the transmitter to settle and prevents edge clipping.

### Callsign beacon

Enter the call and interval, then select **Start beacon**. It sends immediately
and repeats on a start-to-start schedule. If transmission lasts longer than the
interval, it waits until the current transmission finishes. **Stop beacon**
cancels the timer and stops an active beacon.

### Listen before transmit on HF

HF audio normally contains continuous noise, so this feature does not depend on
squelch:

1. Tune to the intended frequency when it is genuinely clear.
2. Set receiver volume, AGC, bandwidth, and computer input gain as they will be
   used for the beacon.
3. Click **Calibrate clear-channel noise**.
4. Start with a busy margin of 4–6 dB.
5. Use **Test whether channel is clear** during both clear and occupied periods.
6. Enable **Listen before transmitting**.

A busy manual transmission is cancelled. A busy beacon waits for the configured
retry delay and listens again. Recalibrate after changing band, volume, AGC,
filter width, preamp/attenuator, or audio device. AGC can reduce the difference
between noise and signals, so this is an aid—not a guarantee that a frequency is
clear. Always listen and follow normal operating practice.

## Troubleshooting

| Symptom | Likely adjustment |
| --- | --- |
| O, D, or 0 closes up | Use Normal font, fewer rows, less thickening, or more bandwidth |
| Image is faint | Raise audio gradually; verify transmit passband and input selection |
| Image blooms or smears | Reduce audio/ALC, compression, rows, or line thickening |
| Image is mirrored/upside down | Change received orientation, mirror, Q-tail flip, or letter order one at a time |
| Letters are too far apart | Set letter gap near zero; verify VOX guard is not being inserted per glyph |
| Period looks like a bar | Confirm version 0.2.9 or newer and regenerate audio |
| Preset is too small | Reload the preset in version 0.2.6 or newer |
| Beacon always says busy | Recalibrate at the current RX settings or increase busy margin |
| Beacon misses weak activity | Decrease busy margin or increase listen duration |
| VOX clips the first letter | Increase VOX guard and/or PTT lead time |
| No audio device appears | Reconnect it, close apps holding it exclusively, then refresh devices |
| Hamlib PTT fails | Verify rigctld is running, its model/serial settings work, and host/port match |

## FFT audio preview

Click **Generate audio**, then open **Preview**. The lower panel performs an
actual FFT of the synthesized samples and scrolls time downward with frequency
left-to-right. This can reveal merged tones, closed letter centers, excessive
line thickening, and inadequate time resolution that a source-image preview
cannot show. Select 1x for transmitted timing or 4x/10x for quicker inspection,
then use **Replay scrolling FFT** after changing speed.

## Responsible operation

The operator must select an authorized frequency and emission, remain within
applicable bandwidth and power limits, identify as required, avoid interference,
and consider transmitter duty cycle. A clear-channel detector cannot detect
every weak or hidden station. Use conservative settings and monitor operation.
