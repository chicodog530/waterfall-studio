# Contributing

Thanks for improving Waterfall Studio. Bug reports should include the app
version, operating system, radio, interface, mode/filter width, selected audio
devices, and exact reproduction steps. Screenshots of both the Preview tab and
the received waterfall are especially useful.

## Development setup

```bash
git clone https://github.com/chicodog530/Waterfall-Studio.git
cd Waterfall-Studio
python -m venv .venv
```

Activate the environment, then run:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
python waterfall_studio.py
```

Before opening a pull request:

```bash
python -m py_compile *.py
```

Keep RF-specific behavior configurable. Never silently increase output level,
key a transmitter, or change saved radio settings. Show signal-processing
changes in both the source and predicted-received previews.

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for architecture details.
