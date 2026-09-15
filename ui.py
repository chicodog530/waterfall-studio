#!/usr/bin/env python3
"""Waterfall Studio graphical user interface.

A monochrome image is treated as a time/frequency intensity map. Image columns
become consecutive slices of audio, while illuminated rows become
phase-continuous tones between the chosen low and high audio frequencies.

Image, DSP, and radio backends live in separate modules; this module coordinates
them through PySide6. The operator and external radio remain responsible for
frequency, bandwidth, power, identification, and duty cycle.
"""

from __future__ import annotations

import json
import sys
import time
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd
from PIL import Image, ImageDraw, ImageOps
from PySide6.QtCore import QSettings, QTimer, Signal, Qt
from PySide6.QtGui import QFont, QFontMetrics, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog,
    QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QProgressBar, QPushButton, QSlider, QSpinBox,
    QTabWidget, QVBoxLayout, QWidget,
)

from serial.tools import list_ports

from constants import (APP_VERSION, CALIBRATIONS, LAYOUTS, ORIENTATIONS,
                       PRESETS, SAMPLE_RATE)
from dsp import (MORSE, activity_level_dbfs, add_vox_guards, audio_spectrogram,
                 morse_id, synthesize)
from image_processing import (channel_image, expand_preset_art, glyph_duration,
                              predicted_waterfall, rotate_for_transmission,
                              trim_glyph_time_margins)
from radio import AudioWorker, PTTController


# Image orientation and channel-model helpers.

def pil_to_pixmap(image: Image.Image) -> QPixmap:
    rgb = image.convert("RGB")
    raw = rgb.tobytes("raw", "RGB")
    qimage = QImage(raw, rgb.width, rgb.height, rgb.width * 3, QImage.Format_RGB888)
    return QPixmap.fromImage(qimage.copy())


















# Radio keying and background playback. Hardware access stays outside the image
# pipeline so saved WAV files can be generated without a connected transceiver.




class CanvasLabel(QLabel):
    """Preview widget that stores freehand strokes in normalized coordinates."""
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.setMinimumSize(520, 220)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background:#03070a;border:1px solid #35414a")
        self.strokes: list[list[tuple[float, float]]] = []
        self.drawing = False
        self.drawing_enabled = True

    def mousePressEvent(self, event):
        if self.drawing_enabled and event.button() == Qt.LeftButton:
            self.drawing = True
            self.strokes.append([(event.position().x()/self.width(), event.position().y()/self.height())])
            self.changed.emit()

    def mouseMoveEvent(self, event):
        if self.drawing:
            self.strokes[-1].append((event.position().x()/self.width(), event.position().y()/self.height()))
            self.changed.emit()

    def mouseReleaseEvent(self, event):
        self.drawing = False


class MainWindow(QMainWindow):
    """Coordinate interface state, rendering, audio, channel sensing, and PTT."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Waterfall Studio {APP_VERSION}")
        self.resize(1180, 800)
        self.settings = QSettings("KE0CGB", "WaterfallStudio")
        self.source_image: Image.Image | None = None
        self.current_preset_name: str | None = None
        self.preset_profiles: dict[str, dict] = {}
        self.source_render = Image.new("L", (360, 120), 0)
        self.transmit_render = self.source_render.copy()
        self.letter_frames: list[Image.Image | None] = []
        self.frame_durations: list[float] = []
        self.audio: np.ndarray | None = None
        self.worker: AudioWorker | None = None
        self.beacon_active = False
        self.beacon_last_started = 0.0
        self.beacon_timer = QTimer(self)
        self.beacon_timer.setSingleShot(True)
        self.beacon_timer.timeout.connect(self.transmit_beacon)
        self.fft_image: Image.Image | None = None
        self.fft_row = 0
        self.fft_timer = QTimer(self); self.fft_timer.setInterval(50)
        self.fft_timer.timeout.connect(self.advance_fft_preview)

        root = QWidget(); self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        self.tabs = QTabWidget(); outer.addWidget(self.tabs, 1)
        self.create_tab = QWidget(); self.signal_tab = QWidget(); self.radio_tab = QWidget(); self.preview_tab = QWidget()
        self.tabs.addTab(self.create_tab, "1  Create")
        self.tabs.addTab(self.signal_tab, "2  Optimize")
        self.tabs.addTab(self.radio_tab, "3  Radio")
        self.tabs.addTab(self.preview_tab, "4  Preview")
        self.build_create_tab(); self.build_signal_tab(); self.build_radio_tab(); self.build_preview_tab()

        actions = QHBoxLayout(); outer.addLayout(actions)
        self.generate_btn = QPushButton("Generate audio"); self.generate_btn.clicked.connect(self.generate)
        save = QPushButton("Save WAV..."); save.clicked.connect(self.save_wav)
        self.send_btn = QPushButton("Transmit / play"); self.send_btn.clicked.connect(self.play)
        self.stop_btn = QPushButton("Stop"); self.stop_btn.clicked.connect(self.stop); self.stop_btn.setEnabled(False)
        reset = QPushButton("Reset to Defaults"); reset.clicked.connect(self.reset_defaults)
        for widget in (self.generate_btn, save, self.send_btn, self.stop_btn, reset): actions.addWidget(widget)
        self.progress = QProgressBar(); outer.addWidget(self.progress)
        self.statusBar().showMessage("Ready — calibrate into a dummy load or low-power test path first")
        self.refresh_audio(); self.refresh_ports(); self.restore_settings(); self.rebuild()

    def build_create_tab(self):
        layout = QVBoxLayout(self.create_tab)
        controls = QGridLayout(); layout.addLayout(controls)
        self.text = QLineEdit("KE0CGB"); self.text.textChanged.connect(self.rebuild)
        self.font_size = QSpinBox(); self.font_size.setRange(12, 200); self.font_size.setValue(72); self.font_size.valueChanged.connect(self.rebuild)
        self.font_weight = QComboBox(); self.font_weight.addItems(("Normal", "Bold")); self.font_weight.currentTextChanged.connect(self.rebuild)
        self.layout_mode = QComboBox(); self.layout_mode.addItems(LAYOUTS); self.layout_mode.setCurrentIndex(1); self.layout_mode.currentTextChanged.connect(self.rebuild)
        self.reverse_letters = QCheckBox("Reverse letter order"); self.reverse_letters.toggled.connect(self.rebuild)
        self.flip_vertical = QCheckBox("Flip each letter vertically (Q-tail fix)"); self.flip_vertical.setChecked(True); self.flip_vertical.toggled.connect(self.rebuild)
        self.cw_id_enabled = QCheckBox("Send CW ID after transmission")
        self.cw_id_enabled.toggled.connect(self.rebuild)
        self.cw_id_call = QLineEdit("KE0CGB")
        self.cw_id_call.setMaxLength(24); self.cw_id_call.textChanged.connect(self.rebuild)
        form = QFormLayout(); form.addRow("Text", self.text); form.addRow("Font size", self.font_size); form.addRow("Font weight", self.font_weight)
        form.addRow("Text layout", self.layout_mode); form.addRow(self.reverse_letters); form.addRow(self.flip_vertical)
        form.addRow(self.cw_id_enabled); form.addRow("CW ID callsign", self.cw_id_call)
        controls.addLayout(form, 0, 0)

        art = QFormLayout()
        load = QPushButton("Load image…"); load.clicked.connect(self.load_image)
        clear = QPushButton("Clear loaded art"); clear.clicked.connect(self.clear_art)
        row = QHBoxLayout(); row.addWidget(load); row.addWidget(clear); art.addRow(row)
        self.preset = QComboBox(); self.preset.addItems(PRESETS)
        preset_btn = QPushButton("Load preset"); preset_btn.clicked.connect(self.load_selected_preset)
        save_preset = QPushButton("Save preset settings"); save_preset.clicked.connect(self.save_current_preset_profile)
        prow = QHBoxLayout(); prow.addWidget(self.preset); prow.addWidget(preset_btn); prow.addWidget(save_preset); art.addRow("Preset", prow)
        self.calibration = QComboBox(); self.calibration.addItems(CALIBRATIONS)
        cal_btn = QPushButton("Load calibration"); cal_btn.clicked.connect(self.load_selected_calibration)
        crow = QHBoxLayout(); crow.addWidget(self.calibration); crow.addWidget(cal_btn); art.addRow("Calibration", crow)
        controls.addLayout(art, 0, 1)

        self.canvas_caption = QLabel("Source artwork"); layout.addWidget(self.canvas_caption)
        self.canvas = CanvasLabel(); self.canvas.changed.connect(self.rebuild); layout.addWidget(self.canvas, 1)
        clear_draw = QPushButton("Clear drawing strokes"); clear_draw.clicked.connect(self.clear_drawing); layout.addWidget(clear_draw)

    def build_signal_tab(self):
        layout = QVBoxLayout(self.signal_tab)
        box = QGroupBox("Channel model and transmission")
        form = QFormLayout(box)
        self.low = QSpinBox(); self.low.setRange(20, 18000); self.low.setValue(100)
        self.high = QSpinBox(); self.high.setRange(50, 20000); self.high.setValue(3000)
        self.duration = QDoubleSpinBox(); self.duration.setRange(.5, 120); self.duration.setValue(5); self.duration.setSuffix(" s")
        self.letter_gap = QDoubleSpinBox(); self.letter_gap.setRange(0, 10); self.letter_gap.setValue(.4); self.letter_gap.setSingleStep(.1); self.letter_gap.setSuffix(" s")
        self.word_gap = QDoubleSpinBox(); self.word_gap.setRange(0, 10); self.word_gap.setValue(.8); self.word_gap.setSingleStep(.1); self.word_gap.setSuffix(" s")
        self.level = QSlider(Qt.Horizontal); self.level.setRange(1, 80); self.level.setValue(20)
        self.detail = QSpinBox(); self.detail.setRange(16, 256); self.detail.setValue(72); self.detail.setSuffix(" frequency rows")
        self.threshold = QSpinBox(); self.threshold.setRange(0, 250); self.threshold.setValue(35)
        self.gamma = QDoubleSpinBox(); self.gamma.setRange(.25, 3); self.gamma.setValue(1); self.gamma.setSingleStep(.1)
        self.thicken = QSpinBox(); self.thicken.setRange(0, 4); self.thicken.setValue(1)
        self.aspect = QDoubleSpinBox(); self.aspect.setRange(.2, 5); self.aspect.setValue(1); self.aspect.setSingleStep(.1)
        self.orientation = QComboBox(); self.orientation.addItems(ORIENTATIONS)
        self.invert = QCheckBox("Invert brightness"); self.mirror = QCheckBox("Mirror horizontally")
        for control in (self.low, self.high, self.duration, self.detail, self.threshold,
                        self.gamma, self.thicken, self.aspect, self.letter_gap, self.word_gap, self.orientation,
                        self.invert, self.mirror):
            if isinstance(control, QComboBox): control.currentTextChanged.connect(self.rebuild)
            elif isinstance(control, QCheckBox): control.toggled.connect(self.rebuild)
            else: control.valueChanged.connect(self.rebuild)
        form.addRow("Lowest audio tone", self.low); form.addRow("Highest audio tone", self.high)
        self.duration_label = QLabel("Seconds per letter")
        form.addRow(self.duration_label, self.duration); form.addRow("Gap between letters", self.letter_gap)
        form.addRow("Gap for a typed space", self.word_gap)
        self.total_time_label = QLabel("Estimated total: 5.0 s"); form.addRow(self.total_time_label)
        form.addRow("Output level", self.level)
        form.addRow("Resolvable detail", self.detail); form.addRow("Brightness threshold", self.threshold)
        form.addRow("Gamma", self.gamma); form.addRow("Line thickening", self.thicken)
        form.addRow("Waterfall aspect", self.aspect); form.addRow("Received orientation", self.orientation)
        form.addRow(self.invert); form.addRow(self.mirror)
        layout.addWidget(box); layout.addStretch()

    def build_radio_tab(self):
        layout = QGridLayout(self.radio_tab)
        audio = QGroupBox("Audio interface"); af = QFormLayout(audio)
        self.output_devices = QComboBox(); self.input_devices = QComboBox()
        self.repeat = QCheckBox("Repeat continuously")
        self.listen_first = QCheckBox("Listen before transmitting")
        self.listen_seconds = QDoubleSpinBox(); self.listen_seconds.setRange(.5, 15)
        self.listen_seconds.setValue(3); self.listen_seconds.setSingleStep(.5); self.listen_seconds.setSuffix(" s")
        self.noise_floor = QDoubleSpinBox(); self.noise_floor.setRange(-120, 0)
        self.noise_floor.setValue(-55); self.noise_floor.setDecimals(1); self.noise_floor.setSuffix(" dBFS")
        self.busy_margin = QDoubleSpinBox(); self.busy_margin.setRange(1, 30)
        self.busy_margin.setValue(4); self.busy_margin.setSingleStep(.5); self.busy_margin.setSuffix(" dB")
        self.busy_retry = QDoubleSpinBox(); self.busy_retry.setRange(1, 300)
        self.busy_retry.setValue(15); self.busy_retry.setSingleStep(5); self.busy_retry.setSuffix(" s")
        calibrate = QPushButton("Calibrate clear-channel noise"); calibrate.clicked.connect(self.calibrate_noise_floor)
        listen_test = QPushButton("Test whether channel is clear"); listen_test.clicked.connect(self.test_channel_clear)
        refresh = QPushButton("Refresh audio devices"); refresh.clicked.connect(self.refresh_audio)
        af.addRow("Radio TX audio output", self.output_devices)
        af.addRow("Radio RX audio input", self.input_devices); af.addRow(self.repeat)
        af.addRow(self.listen_first); af.addRow("Listen for", self.listen_seconds)
        af.addRow("Calibrated noise level", self.noise_floor); af.addRow("Busy margin above noise", self.busy_margin)
        af.addRow("Beacon busy retry", self.busy_retry); af.addRow(calibrate); af.addRow(listen_test); af.addRow(refresh)
        layout.addWidget(audio, 0, 0)

        rig = QGroupBox("Rig control / PTT"); rf = QFormLayout(rig)
        self.radio_name = QComboBox(); self.radio_name.addItems(("Generic / G90", "Yaesu FT-710", "Hamlib-supported radio"))
        self.port = QComboBox(); self.baud = QComboBox(); self.baud.addItems(("19200", "38400", "115200"))
        self.ptt_method = QComboBox(); self.ptt_method.addItems(("VOX", "CAT", "RTS", "DTR", "Hamlib rigctld"))
        self.rigctld_host = QLineEdit("127.0.0.1")
        self.rigctld_port = QSpinBox(); self.rigctld_port.setRange(1, 65535); self.rigctld_port.setValue(4532)
        self.lead = QSpinBox(); self.lead.setRange(0, 3000); self.lead.setValue(300); self.lead.setSuffix(" ms")
        self.tail = QSpinBox(); self.tail.setRange(0, 3000); self.tail.setValue(250); self.tail.setSuffix(" ms")
        self.vox_guard = QDoubleSpinBox(); self.vox_guard.setRange(0, 3); self.vox_guard.setValue(.8); self.vox_guard.setSingleStep(.1); self.vox_guard.setSuffix(" s")
        self.vox_tone = QSpinBox(); self.vox_tone.setRange(300, 2500); self.vox_tone.setValue(1000); self.vox_tone.setSuffix(" Hz")
        ports = QPushButton("Refresh ports"); ports.clicked.connect(self.refresh_ports)
        test = QPushButton("Test PTT (1 second)"); test.clicked.connect(self.test_ptt)
        rf.addRow("Radio profile", self.radio_name); rf.addRow("COM port", self.port); rf.addRow("Baud", self.baud)
        rf.addRow("PTT method", self.ptt_method); rf.addRow("PTT lead", self.lead); rf.addRow("PTT tail", self.tail)
        rf.addRow("rigctld host", self.rigctld_host); rf.addRow("rigctld port", self.rigctld_port)
        rf.addRow("VOX guard before/after", self.vox_guard); rf.addRow("VOX guard tone", self.vox_tone)
        rf.addRow(ports); rf.addRow(test)
        layout.addWidget(rig, 0, 1)

        beacon = QGroupBox("Callsign beacon"); bf = QFormLayout(beacon)
        self.beacon_call = QLineEdit("KE0CGB"); self.beacon_call.setMaxLength(24)
        self.beacon_interval = QDoubleSpinBox(); self.beacon_interval.setRange(.1, 1440)
        self.beacon_interval.setValue(10); self.beacon_interval.setSingleStep(.5)
        self.beacon_interval.setDecimals(1); self.beacon_interval.setSuffix(" min")
        self.beacon_start = QPushButton("Start beacon"); self.beacon_start.clicked.connect(self.start_beacon)
        self.beacon_stop = QPushButton("Stop beacon"); self.beacon_stop.clicked.connect(self.stop_beacon)
        self.beacon_stop.setEnabled(False)
        brow = QHBoxLayout(); brow.addWidget(self.beacon_start); brow.addWidget(self.beacon_stop)
        bf.addRow("Callsign", self.beacon_call); bf.addRow("Send every", self.beacon_interval); bf.addRow(brow)
        bf.addRow(QLabel("Sends immediately, then repeats at the selected start-to-start interval."))
        layout.addWidget(beacon, 1, 0, 1, 2)
        note = QLabel("FT-710 direct CAT uses TX1/TX0. Other rigs can use Hamlib rigctld, RTS, DTR, or VOX.\n"
                      "The RX input is used for HF noise calibration and listen-before-transmit.")
        note.setWordWrap(True); layout.addWidget(note, 2, 0, 1, 2)

    def build_preview_tab(self):
        layout = QGridLayout(self.preview_tab)
        layout.addWidget(QLabel("Source artwork"), 0, 0); layout.addWidget(QLabel("Predicted received waterfall"), 0, 1)
        self.source_preview = QLabel(); self.result_preview = QLabel()
        for label in (self.source_preview, self.result_preview):
            label.setMinimumSize(480, 300); label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("background:#03070a;border:1px solid #35414a")
        layout.addWidget(self.source_preview, 1, 0); layout.addWidget(self.result_preview, 1, 1)
        self.summary = QLabel(); self.summary.setWordWrap(True); layout.addWidget(self.summary, 2, 0, 1, 2)
        layout.addWidget(QLabel("FFT of generated audio — frequency left/right, time scrolls downward"), 3, 0, 1, 2)
        self.fft_preview = QLabel("Generate audio to build the FFT waterfall")
        self.fft_preview.setMinimumHeight(200); self.fft_preview.setAlignment(Qt.AlignCenter)
        self.fft_preview.setStyleSheet("background:#030008;border:1px solid #35414a")
        layout.addWidget(self.fft_preview, 4, 0, 1, 2)
        controls = QHBoxLayout()
        self.fft_speed = QComboBox(); self.fft_speed.addItems(("1x", "4x", "10x")); self.fft_speed.setCurrentText("4x")
        replay = QPushButton("Replay scrolling FFT"); replay.clicked.connect(self.start_fft_preview)
        controls.addWidget(QLabel("Preview speed")); controls.addWidget(self.fft_speed)
        controls.addWidget(replay); controls.addStretch()
        layout.addLayout(controls, 5, 0, 1, 2)

    def render_text(self, text: str, font_size: int, box_size: int = 0) -> Image.Image:
        weight = QFont.Bold if self.font_weight.currentText() == "Bold" else QFont.Normal
        font = QFont("DejaVu Sans", font_size, weight)
        metrics = QFontMetrics(font)
        if box_size:
            width = height = box_size
        else:
            width = max(1, min(16000, metrics.horizontalAdvance(text) + 20))
            height = max(1, metrics.height() + 20)
        qimage = QImage(width, height, QImage.Format_Grayscale8); qimage.fill(0)
        painter = QPainter(qimage); painter.setPen(QPen(Qt.white)); painter.setFont(font)
        painter.drawText(qimage.rect(), Qt.AlignCenter, text); painter.end()
        return Image.frombytes("L", (width, height), bytes(qimage.constBits()), "raw", "L", qimage.bytesPerLine(), 1)

    def rebuild(self, *_):
        """Rebuild source art, transmit frames, timing, and both previews."""
        sequential_v = self.layout_mode.currentText() == LAYOUTS[1] and self.source_image is None
        sequential_h = self.layout_mode.currentText() == LAYOUTS[2] and self.source_image is None
        sequential = sequential_v or sequential_h
        self.canvas.drawing_enabled = not sequential
        if hasattr(self, "duration_label"):
            self.duration_label.setText("Seconds per letter" if sequential else "Total duration")
            self.letter_gap.setEnabled(sequential)
            self.word_gap.setEnabled(sequential)
        if self.source_image is None:
            source = self.render_text(self.text.text(), self.font_size.value())
            ref = self.render_text("H", self.font_size.value())
            self.artwork_duration = self.duration.value() * max(1.0, source.width / ref.width)
        else:
            width = max(360, round(120 * self.source_image.width / max(1, self.source_image.height)))
            source = ImageOps.contain(self.source_image, (min(width, 16000), 120))
            self.artwork_duration = self.duration.value()
        if self.canvas.strokes and not sequential:
            q = QImage(source.tobytes(), source.width, source.height, source.width, QImage.Format_Grayscale8).copy()
            p = QPainter(q); p.setPen(QPen(Qt.white, 3))
            for stroke in self.canvas.strokes:
                for a, b in zip(stroke, stroke[1:]):
                    p.drawLine(round(a[0]*source.width), round(a[1]*source.height),
                               round(b[0]*source.width), round(b[1]*source.height))
            p.end(); source = Image.frombytes("L", source.size, bytes(q.constBits()))
        if self.invert.isChecked(): source = ImageOps.invert(source)
        if self.mirror.isChecked(): source = ImageOps.mirror(source)
        self.source_render = source

        self.letter_frames = []
        self.frame_durations = []
        if sequential:
            text = self.text.text()[::-1] if self.reverse_letters.isChecked() else self.text.text()
            glyphs = []
            durations = []
            
            # Determine the global frequency padding needed so font size 200 fills 100% bandwidth
            global_freq_pad = 1
            for ch in set(text):
                if ch.isspace(): continue
                test_glyph = self.render_text(ch, 200)
                test_rot = rotate_for_transmission(test_glyph, self.orientation.currentText())
                global_freq_pad = max(global_freq_pad, test_rot.height)
                
            reference = trim_glyph_time_margins(
                self.render_text("H", self.font_size.value()),
                self.threshold.value(), sequential_h)
            reference_size = max(1, reference.width if sequential_h else reference.height)
            
            for ch in text:
                if ch.isspace():
                    glyphs.append(None)
                    durations.append(self.word_gap.value())
                    continue
                glyph = self.render_text(ch, self.font_size.value())
                glyph = trim_glyph_time_margins(glyph, self.threshold.value(), sequential_h)
                
                # The trimmed source dimension becomes time after rotation. Preserve
                # that geometry instead of stretching punctuation to a full letter.
                glyph_size = glyph.width if sequential_h else glyph.height
                durations.append(glyph_duration(self.duration.value(), glyph_size, reference_size))
                
                if self.invert.isChecked(): glyph = ImageOps.invert(glyph)
                if self.mirror.isChecked(): glyph = ImageOps.mirror(glyph)
                if self.flip_vertical.isChecked(): glyph = ImageOps.flip(glyph)
                
                glyph = rotate_for_transmission(glyph, self.orientation.currentText())
                
                # Pad the frequency axis (Y) to the global padding so letters scale uniformly
                padded = Image.new("L", (glyph.width, max(glyph.height, global_freq_pad)), 0)
                padded.paste(glyph, (0, (padded.height - glyph.height) // 2))
                
                if self.aspect.value() != 1:
                    padded = padded.resize((max(1, round(padded.width*self.aspect.value())), padded.height), Image.Resampling.BICUBIC)
                glyphs.append(channel_image(padded, self.detail.value(), self.threshold.value(),
                                            self.gamma.value(), self.thicken.value()))
            self.letter_frames = glyphs
            self.frame_durations = durations
            visible = [g for g in glyphs if g is not None]
            if visible:
                typical_width = round(sum(g.width for g in visible)/len(visible))
                gap = round(typical_width * self.letter_gap.value() / self.duration.value())
                word_gap = max(1, round(typical_width * self.word_gap.value() / self.duration.value()))
                pieces = [Image.new("L", (word_gap, visible[0].height), 0) if g is None else g for g in glyphs]
                joins = [gap if pieces[i].getbbox() and pieces[i+1].getbbox() else 0 for i in range(len(pieces)-1)]
                stream = Image.new("L", (sum(g.width for g in pieces)+sum(joins), max(g.height for g in pieces)), 0)
                x = 0
                for index, glyph in enumerate(pieces):
                    stream.paste(glyph, (x, (stream.height-glyph.height)//2)); x += glyph.width+gap
                    if index < len(joins): x += joins[index]-gap
            else: stream = Image.new("L", (120, 120), 0)
            self.transmit_render = stream
        else:
            artwork = ImageOps.flip(source) if self.flip_vertical.isChecked() else source
            stream = rotate_for_transmission(artwork, self.orientation.currentText())
            if self.aspect.value() != 1:
                stream = stream.resize((max(1, round(stream.width*self.aspect.value())), stream.height), Image.Resampling.BICUBIC)
            self.transmit_render = channel_image(stream, self.detail.value(), self.threshold.value(),
                                                 self.gamma.value(), self.thicken.value())
        self.audio = None; self.progress.setValue(0)
        self.update_previews()

    def update_previews(self):
        source_color = ImageOps.colorize(self.source_render, "#02070b", "#00f0a0")
        result = predicted_waterfall(self.transmit_render, self.orientation.currentText())
        result_color = ImageOps.colorize(result, "#061326", "#fff200")
        canvas_image = result_color if self.letter_frames else source_color
        self.canvas_caption.setText("Actual stacked transmit sequence" if self.letter_frames else "Source artwork")
        self.canvas.setPixmap(pil_to_pixmap(canvas_image).scaled(self.canvas.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.source_preview.setPixmap(pil_to_pixmap(source_color).scaled(self.source_preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.result_preview.setPixmap(pil_to_pixmap(result_color).scaled(self.result_preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        bandwidth = self.high.value()-self.low.value()
        if self.letter_frames:
            adjacent = sum(a is not None and b is not None for a,b in zip(self.letter_frames,self.letter_frames[1:]))
            total_time = sum(self.frame_durations)+adjacent*self.letter_gap.value()
        else:
            total_time = getattr(self, 'artwork_duration', self.duration.value())
        self.total_time_label.setText(f"Estimated total: {total_time:.1f} s")
        self.summary.setText(f"Predicted occupied audio span: {bandwidth} Hz | "
                             f"Channel detail: {self.transmit_render.height} frequency rows | "
                             f"Transmission time: {total_time:.1f} s. Preview includes orientation, threshold, aspect and line processing.")

    def prepare_fft_preview(self):
        """Analyze generated samples and start a receiver-like scrolling view."""
        if self.audio is None: return
        self.fft_image = audio_spectrogram(self.audio, self.low.value(), self.high.value())
        self.start_fft_preview()

    def start_fft_preview(self):
        if self.fft_image is None:
            self.fft_preview.setText("Generate audio to build the FFT waterfall")
            return
        self.fft_row = 0; self.fft_timer.start(); self.advance_fft_preview()

    def advance_fft_preview(self):
        """Reveal FFT rows in a fixed-height window as a waterfall would scroll."""
        if self.fft_image is None: return
        speed = int(self.fft_speed.currentText().rstrip("x"))
        self.fft_row = min(self.fft_image.height, self.fft_row + max(1, round(2.35 * speed)))
        view_rows = min(240, max(80, self.fft_preview.height()))
        start = max(0, self.fft_row-view_rows)
        strip = self.fft_image.crop((0, start, self.fft_image.width, self.fft_row))
        frame = Image.new("L", (self.fft_image.width, view_rows), 0)
        frame.paste(strip, (0, view_rows-strip.height))
        colored = ImageOps.colorize(frame, "#050014", "#fff04a")
        pixmap = pil_to_pixmap(colored).scaled(self.fft_preview.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        self.fft_preview.setPixmap(pixmap)
        if self.fft_row >= self.fft_image.height: self.fft_timer.stop()

    def make_preset(self, name: str) -> Image.Image:
        # Detailed presets are shipped as deliberately simple, two-colour
        # 3:1 images.  Keeping them on disk also lets operators reuse the PNGs
        # in other waterfall/SSTV tools without extracting them from the code.
        bundled_art = {
            "Skull": "skull.png",
            "Alien head": "alien-head.png",
            "Alien full body": "alien-full-body.png",
            "UFO": "ufo.png",
            "Radio tower lightning": "radio-tower-lightning.png",
        }
        if filename := bundled_art.get(name):
            path = Path(__file__).with_name("artwork") / filename
            with Image.open(path) as artwork:
                image = artwork.convert("L")
                # Crop unused margins before channel processing. This is
                # especially important for the full-body alien: otherwise the
                # figure occupies only a narrow slice of the available tones.
                return expand_preset_art(image)

        image = Image.new("L", (360, 120), 0); d = ImageDraw.Draw(image); w = 255
        if name == "Smiley face":
            d.ellipse((126, 8, 234, 112), outline=w, width=11); d.ellipse((151, 33, 167, 49), fill=w); d.ellipse((193, 33, 209, 49), fill=w); d.arc((148, 42, 212, 94), 20, 160, fill=w, width=11)
        elif name in ("Thumbs up", "Thumbs down"):
            d.polygon([(126,54),(151,54),(168,18),(184,18),(188,48),(225,48),(234,58),(224,101),(151,101),(151,91),(126,91)], fill=w)
            if name == "Thumbs down": image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        elif name == "Heart":
            d.polygon([(180,112),(112,50),(119,23),(144,8),(180,35),(216,8),(241,23),(248,50)], fill=w)
        elif name in ("73 in a circle", "CQ", "QSL", "QRZ?", "RST 599", "SK", "SOS"):
            text = "73" if name == "73 in a circle" else name
            if name == "73 in a circle": d.ellipse((118,5,242,115), outline=w, width=7)
            overlay = self.render_text(text, 48 if len(text)>3 else 68)
            image = Image.fromarray(np.maximum(np.asarray(image), np.asarray(ImageOps.fit(overlay, image.size))))
        elif name == "Antenna":
            d.line((180,14,180,108),fill=w,width=10); d.line((180,27,137,62),fill=w,width=10); d.line((180,27,223,62),fill=w,width=10); d.line((148,108,212,108),fill=w,width=10)
        elif name == "Radio waves":
            d.ellipse((171,51,189,69),fill=w)
            for box in ((145,25,215,95),(111,-9,249,129)):
                d.arc(box,300,60,fill=w,width=11); d.arc(box,120,240,fill=w,width=11)
        elif name == "Arrow right":
            d.line((95,60,255,60),fill=w,width=12); d.polygon([(230,25),(275,60),(230,95)],fill=w)
        else:
            d.polygon([(192,5),(132,67),(172,67),(155,115),(228,48),(185,48)],fill=w)
        return expand_preset_art(image)

    def make_calibration(self, name: str) -> Image.Image:
        image = Image.new("L", (360, 120), 0); d = ImageDraw.Draw(image); w = 255
        if name == "Square": d.rectangle((125,10,235,110),outline=w,width=5)
        elif name == "Grid":
            for x in range(30, 360, 30): d.line((x,5,x,115),fill=w,width=3)
            for y in range(10, 120, 20): d.line((5,y,355,y),fill=w,width=3)
        elif name == "Frequency bars":
            for y in range(10, 120, 15): d.line((15,y,345,y),fill=w,width=4)
        else:
            for x in range(15, 360, 25): d.line((x,8,x,112),fill=w,width=4)
        return image

    def set_art(self, image):
        self.source_image = image.convert("L"); self.canvas.strokes.clear(); self.rebuild()

    def signal_profile(self) -> dict:
        """Capture channel controls that materially affect a preset on air."""
        return {
            "duration": self.duration.value(), "low": self.low.value(),
            "high": self.high.value(), "detail": self.detail.value(),
            "threshold": self.threshold.value(), "gamma": self.gamma.value(),
            "thicken": self.thicken.value(), "aspect": self.aspect.value(),
            "orientation": self.orientation.currentText(),
            "invert": self.invert.isChecked(), "mirror": self.mirror.isChecked(),
        }

    def apply_signal_profile(self, profile: dict):
        """Restore one preset's independently saved transmission settings."""
        for control, key in ((self.duration, "duration"), (self.low, "low"),
                             (self.high, "high"), (self.detail, "detail"),
                             (self.threshold, "threshold"), (self.gamma, "gamma"),
                             (self.thicken, "thicken"), (self.aspect, "aspect")):
            if key in profile: control.setValue(profile[key])
        if "orientation" in profile:
            index = self.orientation.findText(profile["orientation"])
            if index >= 0: self.orientation.setCurrentIndex(index)
        if "invert" in profile: self.invert.setChecked(bool(profile["invert"]))
        if "mirror" in profile: self.mirror.setChecked(bool(profile["mirror"]))

    def load_selected_preset(self):
        """Load preset artwork and its saved or factory transmission profile."""
        name = self.preset.currentText()
        self.current_preset_name = name
        self.set_art(self.make_preset(name))
        factory = {"duration": 20.0, "aspect": 4.0} if name == "Alien full body" else {}
        self.apply_signal_profile(self.preset_profiles.get(name, factory))
        self.rebuild()
        self.statusBar().showMessage(f"Loaded {name} with its preset transmission settings")

    def save_current_preset_profile(self):
        """Store the current Optimize controls under the selected preset name."""
        if self.current_preset_name is None:
            QMessageBox.information(self, "Load a preset", "Load the preset you want to tune first.")
            return
        self.preset_profiles[self.current_preset_name] = self.signal_profile()
        self.save_settings()
        self.statusBar().showMessage(f"Saved transmission settings for {self.current_preset_name}")

    def load_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open artwork", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if path:
            try:
                self.current_preset_name = None
                self.set_art(Image.open(path))
            except Exception as exc: QMessageBox.critical(self, "Image error", str(exc))

    def load_selected_calibration(self):
        self.current_preset_name = None
        self.set_art(self.make_calibration(self.calibration.currentText()))

    def clear_art(self): self.source_image = None; self.current_preset_name = None; self.canvas.strokes.clear(); self.rebuild()
    def clear_drawing(self): self.canvas.strokes.clear(); self.rebuild()

    def refresh_audio(self):
        old_out = self.output_devices.currentData() if hasattr(self, "output_devices") else None
        old_in = self.input_devices.currentData() if hasattr(self, "input_devices") else None
        if not hasattr(self, "output_devices"): return
        self.output_devices.clear(); self.input_devices.clear()
        try:
            for index, device in enumerate(sd.query_devices()):
                if device["max_output_channels"]: self.output_devices.addItem(f"{index}: {device['name']}", index)
                if device["max_input_channels"]: self.input_devices.addItem(f"{index}: {device['name']}", index)
            for combo, old in ((self.output_devices,old_out),(self.input_devices,old_in)):
                found = combo.findData(old)
                if found >= 0: combo.setCurrentIndex(found)
        except Exception as exc: self.output_devices.addItem(f"Audio unavailable: {exc}", None)

    def refresh_ports(self):
        if not hasattr(self, "port"): return
        old = self.port.currentText(); self.port.clear()
        if list_ports:
            for item in list_ports.comports(): self.port.addItem(f"{item.device} — {item.description}", item.device)
        found = self.port.findText(old)
        if found >= 0: self.port.setCurrentIndex(found)

    def ptt_config(self):
        return dict(port=self.port.currentData() or "", baud=int(self.baud.currentText()),
                    method=self.ptt_method.currentText(), radio_name=self.radio_name.currentText(),
                    rigctld_host=self.rigctld_host.text().strip() or "127.0.0.1",
                    rigctld_port=self.rigctld_port.value())

    def test_ptt(self):
        if self.ptt_method.currentText() == "VOX":
            QMessageBox.information(self, "VOX", "VOX keys only when audio is sent. Use Transmit/play for the test."); return
        try:
            ptt = PTTController(**self.ptt_config()); ptt.key(True); QApplication.processEvents(); time.sleep(1); ptt.close()
            self.statusBar().showMessage("PTT test complete")
        except Exception as exc: QMessageBox.critical(self, "PTT error", str(exc))

    def generate(self):
        """Synthesize either the whole artwork or each sequential character."""
        if self.high.value() <= self.low.value():
            QMessageBox.warning(self, "Invalid tones", "Highest tone must be above lowest tone."); return False
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            if self.letter_frames:
                gap = np.zeros(round(SAMPLE_RATE*self.letter_gap.value()), dtype=np.float32)
                pieces = []
                for index, frame in enumerate(self.letter_frames):
                    if frame is None:
                        pieces.append(np.zeros(round(SAMPLE_RATE*self.frame_durations[index]), dtype=np.float32))
                    else:
                        pieces.append(synthesize(frame, self.low.value(), self.high.value(),
                                                 self.frame_durations[index], self.level.value()/100))
                    if (index < len(self.letter_frames)-1 and frame is not None and
                            self.letter_frames[index+1] is not None and gap.size): pieces.append(gap)
                self.audio = np.concatenate(pieces)
            else:
                dur = getattr(self, "artwork_duration", self.duration.value())
                self.audio = synthesize(self.transmit_render, self.low.value(), self.high.value(),
                                        dur, self.level.value()/100)
            if self.cw_id_enabled.isChecked():
                callsign = self.cw_id_call.text().strip().upper()
                if not callsign or any(char != " " and char not in MORSE for char in callsign):
                    QMessageBox.warning(
                        self, "Invalid CW ID",
                        "Enter a callsign using letters, numbers, spaces, / or -.")
                    return False
                separator = np.zeros(round(SAMPLE_RATE * .5), dtype=np.float32)
                identifier = morse_id(callsign, frequency=700, wpm=18,
                                      level=self.level.value()/100)
                self.audio = np.concatenate((self.audio, separator, identifier,
                                             np.zeros(round(SAMPLE_RATE * .2), dtype=np.float32)))
            self.prepare_fft_preview()
            self.statusBar().showMessage(f"Generated {len(self.audio)/SAMPLE_RATE:.1f} seconds; inspect Preview before transmitting")
            return True
        except Exception as exc: QMessageBox.critical(self, "Generation error", str(exc)); return False
        finally: QApplication.restoreOverrideCursor()

    def save_wav(self):
        if self.audio is None and not self.generate(): return
        path, _ = QFileDialog.getSaveFileName(self, "Save audio", "waterfall.wav", "WAV audio (*.wav)")
        if not path: return
        pcm = (np.clip(self.audio,-1,1)*32767).astype("<i2")
        with wave.open(path,"wb") as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SAMPLE_RATE); wf.writeframes(pcm.tobytes())

    def play(self):
        """Check the channel when enabled, add VOX guards, and start TX audio."""
        if self.worker and self.worker.isRunning(): return
        if self.audio is None and not self.generate(): return
        device = self.output_devices.currentData()
        if device is None: QMessageBox.warning(self,"No output","Select the radio TX audio output device."); return
        if self.listen_first.isChecked():
            result = self.channel_clear_result()
            if result is None:
                if self.beacon_active: self.stop_beacon()
                return
            clear, measured = result
            if not clear:
                if self.beacon_active:
                    delay = self.busy_retry.value()
                    self.beacon_timer.start(round(delay * 1000))
                    self.statusBar().showMessage(
                        f"Channel busy ({measured:.1f} dBFS) — beacon retry in {delay:g} seconds")
                else:
                    QMessageBox.information(
                        self, "Channel busy",
                        f"Transmission cancelled. Received level was {measured:.1f} dBFS; "
                        f"the busy point is {self.noise_floor.value()+self.busy_margin.value():.1f} dBFS.")
                return
        self.save_settings()
        send_audio = self.audio
        if self.ptt_method.currentText() == "VOX" and self.vox_guard.value() > 0:
            guard_level = min(.06, max(.015, self.level.value()/250))
            send_audio = add_vox_guards(self.audio, self.vox_guard.value(),
                                        self.vox_tone.value(), guard_level)
        if self.beacon_active: self.beacon_last_started = time.monotonic()
        self.worker = AudioWorker(send_audio,device,self.repeat.isChecked(),self.ptt_config(),self.lead.value(),self.tail.value())
        self.worker.progress.connect(self.progress.setValue); self.worker.failed.connect(lambda message: QMessageBox.critical(self,"Transmit error",message))
        self.worker.finished.connect(self.finished); self.worker.start(); self.send_btn.setEnabled(False); self.stop_btn.setEnabled(True)
        self.statusBar().showMessage("Transmitting — verify frequency, mode, power, bandwidth, load and identification")

    def receive_activity_level(self):
        """Sample unsquelched RX audio and return its activity level in dBFS."""
        device = self.input_devices.currentData()
        if device is None:
            QMessageBox.warning(self, "No RX input", "Select the radio RX audio input device first.")
            return None
        seconds = self.listen_seconds.value()
        self.statusBar().showMessage(f"Listening for {seconds:g} seconds before transmitting…")
        QApplication.processEvents()
        try:
            audio = sd.rec(round(SAMPLE_RATE * seconds), samplerate=SAMPLE_RATE,
                           channels=1, dtype="float32", device=device)
            sd.wait()
            return activity_level_dbfs(audio, round(SAMPLE_RATE * .1))
        except Exception as exc:
            QMessageBox.critical(self, "RX audio error", str(exc))
            return None

    def channel_clear_result(self):
        """Compare received activity with the calibrated HF noise baseline."""
        measured = self.receive_activity_level()
        if measured is None: return None
        busy_point = self.noise_floor.value() + self.busy_margin.value()
        return measured < busy_point, measured

    def calibrate_noise_floor(self):
        measured = self.receive_activity_level()
        if measured is None: return
        self.noise_floor.setValue(measured)
        self.save_settings()
        self.statusBar().showMessage(
            f"Clear-channel HF noise calibrated at {measured:.1f} dBFS; "
            f"busy point is {measured+self.busy_margin.value():.1f} dBFS")

    def test_channel_clear(self):
        result = self.channel_clear_result()
        if result is None: return
        clear, measured = result
        state = "CLEAR" if clear else "BUSY"
        self.statusBar().showMessage(
            f"Channel {state}: {measured:.1f} dBFS "
            f"(noise {self.noise_floor.value():.1f}, margin {self.busy_margin.value():.1f} dB)")

    def start_beacon(self):
        """Validate the beacon configuration and make the first attempt now."""
        callsign = self.beacon_call.text().strip().upper()
        if not callsign or any(not (c.isalnum() or c in "/-") for c in callsign):
            QMessageBox.warning(self, "Invalid callsign", "Enter a callsign using letters, numbers, / or -.")
            return
        if self.output_devices.currentData() is None:
            QMessageBox.warning(self, "No output", "Select the radio TX audio output device first.")
            return
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Transmitter busy", "Stop the current transmission before starting the beacon.")
            return
        self.beacon_call.setText(callsign)
        self.beacon_active = True
        self.beacon_start.setEnabled(False); self.beacon_stop.setEnabled(True)
        self.beacon_timer.stop(); self.transmit_beacon()

    def transmit_beacon(self):
        """Prepare the callsign as sequential glyphs and attempt one beacon."""
        if not self.beacon_active or (self.worker and self.worker.isRunning()):
            return
        self.repeat.setChecked(False)
        self.source_image = None; self.canvas.strokes.clear()
        self.layout_mode.setCurrentText(LAYOUTS[1])
        self.text.setText(self.beacon_call.text().strip().upper())
        self.rebuild(); self.audio = None
        self.play()

    def stop_beacon(self):
        self.beacon_active = False; self.beacon_timer.stop()
        self.beacon_start.setEnabled(True); self.beacon_stop.setEnabled(False)
        if self.worker and self.worker.isRunning(): self.worker.stop()
        self.statusBar().showMessage("Beacon stopped")

    def stop(self):
        if self.beacon_active:
            self.beacon_active = False; self.beacon_timer.stop()
            self.beacon_start.setEnabled(True); self.beacon_stop.setEnabled(False)
        if self.worker: self.worker.stop()

    def finished(self):
        """Restore controls and schedule the next start-to-start beacon time."""
        self.send_btn.setEnabled(True); self.stop_btn.setEnabled(False)
        if self.beacon_active:
            period = self.beacon_interval.value() * 60
            remaining = max(.25, period - (time.monotonic() - self.beacon_last_started))
            self.beacon_timer.start(round(remaining * 1000))
            self.statusBar().showMessage(f"Beacon sent — next transmission in {remaining/60:.1f} minutes")
        else:
            self.statusBar().showMessage("Stopped")

    def save_settings(self):
        data = dict(output=self.output_devices.currentData(), input=self.input_devices.currentData(),
                    radio=self.radio_name.currentText(), port=self.port.currentData(), baud=self.baud.currentText(),
                    ptt=self.ptt_method.currentText(), low=self.low.value(), high=self.high.value(), detail=self.detail.value(),
                    layout=self.layout_mode.currentText(), reverse=self.reverse_letters.isChecked(),
                    orientation=self.orientation.currentText(), aspect=self.aspect.value(), duration=self.duration.value(),
                    gap=self.letter_gap.value(), word_gap=self.word_gap.value(), threshold=self.threshold.value(), gamma=self.gamma.value(),
                    thicken=self.thicken.value(), font_weight=self.font_weight.currentText(),
                    flip_vertical=self.flip_vertical.isChecked(),
                    cw_id_enabled=self.cw_id_enabled.isChecked(),
                    cw_id_call=self.cw_id_call.text(),
                    preset_profiles=self.preset_profiles,
                    vox_guard=self.vox_guard.value(), vox_tone=self.vox_tone.value(),
                    beacon_call=self.beacon_call.text(), beacon_interval=self.beacon_interval.value(),
                    listen_first=self.listen_first.isChecked(), listen_seconds=self.listen_seconds.value(),
                    noise_floor=self.noise_floor.value(), busy_margin=self.busy_margin.value(),
                    busy_retry=self.busy_retry.value(), rigctld_host=self.rigctld_host.text(),
                    rigctld_port=self.rigctld_port.value(), fft_speed=self.fft_speed.currentText(),
                    font_size=self.font_size.value(), text=self.text.text())
        self.settings.setValue("profile", json.dumps(data))

    def restore_settings(self, reset=False):
        if reset: data = {}
        else:
            try: data = json.loads(self.settings.value("profile", "{}"))
            except Exception: return
        for combo, value in ((self.output_devices,data.get("output")),(self.input_devices,data.get("input")),
                             (self.radio_name,data.get("radio")),(self.port,data.get("port")),
                             (self.baud,data.get("baud")),(self.ptt_method,data.get("ptt"))):
            if value is None: continue
            index = combo.findData(value) if combo in (self.output_devices,self.input_devices,self.port) else combo.findText(str(value))
            if index >= 0: combo.setCurrentIndex(index)
        self.low.setValue(data.get("low",100)); self.high.setValue(data.get("high",3000)); self.detail.setValue(data.get("detail",72))
        for combo, value in ((self.layout_mode,data.get("layout",LAYOUTS[1])),(self.orientation,data.get("orientation",ORIENTATIONS[0])),
                             (self.font_weight,data.get("font_weight","Normal"))):
            index = combo.findText(str(value))
            if index >= 0: combo.setCurrentIndex(index)
        self.reverse_letters.setChecked(bool(data.get("reverse",False)))
        self.flip_vertical.setChecked(bool(data.get("flip_vertical",True)))
        self.cw_id_enabled.setChecked(bool(data.get("cw_id_enabled",False)))
        self.cw_id_call.setText(data.get("cw_id_call", data.get("beacon_call", "KE0CGB")))
        profiles = data.get("preset_profiles", {})
        self.preset_profiles = profiles if isinstance(profiles, dict) else {}
        self.aspect.setValue(data.get("aspect",1)); self.duration.setValue(data.get("duration",5))
        self.letter_gap.setValue(data.get("gap",.4)); self.threshold.setValue(data.get("threshold",35))
        self.word_gap.setValue(data.get("word_gap",.8))
        self.gamma.setValue(data.get("gamma",1)); self.thicken.setValue(data.get("thicken",1))
        self.vox_guard.setValue(data.get("vox_guard",.8)); self.vox_tone.setValue(data.get("vox_tone",1000))
        self.beacon_call.setText(data.get("beacon_call","KE0CGB"))
        self.beacon_interval.setValue(data.get("beacon_interval",10))
        self.listen_first.setChecked(bool(data.get("listen_first",False)))
        self.listen_seconds.setValue(data.get("listen_seconds",3.0))
        self.busy_margin.setValue(data.get("busy_margin",5.0))
        self.busy_retry.setValue(data.get("busy_retry",1.0))
        self.noise_floor.setValue(data.get("noise_floor",0.0))
        self.rigctld_host.setText(data.get("rigctld_host","127.0.0.1"))
        self.rigctld_port.setValue(data.get("rigctld_port",4532))
        self.font_size.setValue(data.get("font_size",72))
        self.text.setText(data.get("text","KE0CGB"))
        index = self.fft_speed.findText(data.get("fft_speed", "1x (realtime)"))
        if index >= 0: self.fft_speed.setCurrentIndex(index)

    def reset_defaults(self):
        self.restore_settings(reset=True)

    def closeEvent(self, event):
        self.save_settings(); self.stop()
        if self.worker: self.worker.wait(1800)
        event.accept()


def main():
    app = QApplication(sys.argv); app.setStyle("Fusion")
    app.setStyleSheet("QWidget{font-size:10pt} QMainWindow{background:#171a1f} QGroupBox{font-weight:bold}")
    window = MainWindow(); window.show(); sys.exit(app.exec())


if __name__ == "__main__": main()
