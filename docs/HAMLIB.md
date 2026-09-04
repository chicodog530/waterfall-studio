# Hamlib radio setup

Waterfall Studio can ask a running Hamlib `rigctld` process to control PTT. The
radio-specific serial, USB, or network protocol is handled by Hamlib, so the app
can work with many Yaesu, Icom, Kenwood, Elecraft, Xiegu, SDR, and other models
without embedding every CAT protocol.

## 1. Install Hamlib

Install a recent Hamlib package for the computer running the radio connection.
Confirm that `rigctld` is available from a terminal or command prompt:

```text
rigctld --version
```

## 2. Find the radio model number

Hamlib assigns each backend a numeric model identifier. Search the list rather
than copying a number from an old guide:

Linux:

```bash
rigctld -l | grep -i "part of radio name"
```

Windows Command Prompt:

```bat
rigctld -l | findstr /i "part-of-radio-name"
```

## 3. Start rigctld

Typical serial examples are shown below. Replace `MODEL`, device, and baud with
settings appropriate for the radio:

Linux:

```bash
rigctld -m MODEL -r /dev/ttyUSB0 -s 38400
```

Windows:

```bat
rigctld -m MODEL -r COM3 -s 38400
```

Hamlib listens on TCP port 4532 by default. Keep the terminal running. First
verify normal CAT operation with Hamlib's own tools or another known client.

## 4. Configure Waterfall Studio

1. Open **Radio**.
2. Select **Hamlib-supported radio** as the profile.
3. Select **Hamlib rigctld** as PTT method.
4. Use host `127.0.0.1` and port `4532` when rigctld is on the same computer.
5. Click **Test PTT (1 second)** while using a dummy load or controlled path.

For a rigctld instance on another trusted computer, enter that computer's LAN
address. Do not expose rigctld directly to the public internet; its control
connection has no built-in operator authentication in this application.

## Troubleshooting

- **Connection refused:** rigctld is not running or host/port is wrong.
- **PTT command rejected:** verify the selected Hamlib model supports PTT and
  that no other program has exclusive control of the radio.
- **Serial port busy:** close other CAT applications or configure them to share
  one rigctld server rather than opening the radio independently.
- **Radio keys but no audio:** Hamlib controls PTT only. Select the correct TX
  audio endpoint separately in Waterfall Studio.
- **Remote connection fails:** check the rigctld listen address, firewall, and
  LAN routing. Keep remote control inside a trusted network.
