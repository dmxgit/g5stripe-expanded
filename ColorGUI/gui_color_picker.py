#!/usr/bin/python3
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QColorDialog,
    QComboBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSlider,
    QVBoxLayout,
    QWidget,
)

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
if str(PARENT) not in sys.path:
    sys.path.insert(0, str(PARENT))

from elc_ng import (  # noqa: E402
    ELC,
    set_static_color,
    Action,
    AddActionsCommand,
    AnimationCommand,
    ZoneSelectCommand,
    ZONE_ALL,
    SetDimCommand,
)

VID = 0x187C
PID = 0x0550


def qcolor_to_rgb(color):
    return color.red(), color.green(), color.blue()


def apply_temporary_effect(effect_name, color1, color2=None, duration=3000, tempo=80, brightness=100):
    r1, g1, b1 = qcolor_to_rgb(color1)

    elc = ELC(VID, PID)
    with elc:
        elc.execute(SetDimCommand(100 - brightness, ZONE_ALL))
        elc.execute(AnimationCommand("config_start", 0))
        elc.execute(ZoneSelectCommand(1, ZONE_ALL))

        if effect_name == "morph":
            if color2 is None:
                color2 = QColor(255 - r1, 255 - g1, 255 - b1)
            r2, g2, b2 = qcolor_to_rgb(color2)

            elc.execute(AddActionsCommand([
                Action("morph", r1, g1, b1, duration=duration, tempo=tempo)
            ]))
            elc.execute(AddActionsCommand([
                Action("morph", r2, g2, b2, duration=duration, tempo=tempo)
            ]))
        else:
            elc.execute(AddActionsCommand([
                Action(effect_name, r1, g1, b1, duration=duration, tempo=tempo)
            ]))

        elc.execute(AnimationCommand("config_play", 0))


class ColorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dell LED Color")
        self.resize(430, 420)

        self.current_color = QColor(0, 255, 0)
        self.morph_color = QColor(0, 0, 255)

        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel("Dell / AlienFX color")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        root.addWidget(title)

        self.preview = QFrame()
        self.preview.setFixedHeight(56)
        self.preview.setFrameShape(QFrame.StyledPanel)
        self.preview.setStyleSheet("border-radius: 10px; border: 1px solid palette(mid);")
        root.addWidget(self.preview)

        self.rgb_label = QLabel()
        self.rgb_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        root.addWidget(self.rgb_label)

        preset_layout = QGridLayout()
        preset_layout.setHorizontalSpacing(8)
        preset_layout.setVerticalSpacing(8)
        root.addLayout(preset_layout)

        presets = [
            ("Red", (255, 0, 0)),
            ("Green", (0, 255, 0)),
            ("Blue", (0, 0, 255)),
            ("White", (255, 255, 255)),
            ("Off", (0, 0, 0)),
            ("Orange", (255, 128, 0)),
        ]

        for i, (name, rgb) in enumerate(presets):
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked=False, rgb=rgb: self.set_color(*rgb))
            preset_layout.addWidget(btn, i // 3, i % 3)

        buttons = QHBoxLayout()
        root.addLayout(buttons)

        choose_btn = QPushButton("Choose color…")
        choose_btn.clicked.connect(self.choose_color)
        buttons.addWidget(choose_btn)

        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self.apply_color)
        buttons.addWidget(apply_btn)

        animation_title = QLabel("Animation")
        animation_title.setStyleSheet("font-weight: 600; margin-top: 6px;")
        root.addWidget(animation_title)

        anim_form = QFormLayout()
        root.addLayout(anim_form)

        self.anim_combo = QComboBox()
        self.anim_combo.addItems(["color", "pulse", "morph"])
        self.anim_combo.currentTextChanged.connect(self.update_morph_ui)
        anim_form.addRow("Type:", self.anim_combo)

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(100, 20000)
        self.duration_spin.setSingleStep(100)
        self.duration_spin.setValue(3000)
        self.duration_spin.setSuffix(" ms")
        anim_form.addRow("Duration:", self.duration_spin)

        self.tempo_spin = QSpinBox()
        self.tempo_spin.setRange(1, 1000)
        self.tempo_spin.setValue(80)
        anim_form.addRow("Tempo:", self.tempo_spin)

        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setRange(0, 100)
        self.brightness_slider.setValue(100)
        anim_form.addRow("Brightness:", self.brightness_slider)

        morph_row = QHBoxLayout()
        self.morph_color_btn = QPushButton("Choose morph target…")
        self.morph_color_btn.clicked.connect(self.choose_morph_color)
        morph_row.addWidget(self.morph_color_btn)

        self.morph_preview = QFrame()
        self.morph_preview.setFixedSize(40, 28)
        self.morph_preview.setFrameShape(QFrame.StyledPanel)
        morph_row.addWidget(self.morph_preview)

        morph_row.addStretch(1)

        self.morph_container = QWidget()
        self.morph_container.setLayout(morph_row)
        anim_form.addRow("Morph to:", self.morph_container)

        anim_buttons = QHBoxLayout()
        root.addLayout(anim_buttons)

        preview_anim_btn = QPushButton("Preview animation")
        preview_anim_btn.clicked.connect(self.preview_animation)
        anim_buttons.addWidget(preview_anim_btn)

        self.status_label = QLabel("Ready.")
        self.status_label.setStyleSheet("color: palette(mid);")
        root.addWidget(self.status_label)

        self.refresh_preview()
        self.refresh_morph_preview()
        self.update_morph_ui(self.anim_combo.currentText())

    def set_color(self, r, g, b):
        self.current_color = QColor(r, g, b)
        self.refresh_preview()

    def refresh_preview(self):
        r = self.current_color.red()
        g = self.current_color.green()
        b = self.current_color.blue()
        hex_value = self.current_color.name().upper()

        self.preview.setStyleSheet(
            f"""
            QFrame {{
                background-color: rgb({r}, {g}, {b});
                border-radius: 10px;
                border: 1px solid palette(mid);
            }}
            """
        )
        self.rgb_label.setText(f"RGB: {r}, {g}, {b}    HEX: {hex_value}")

    def refresh_morph_preview(self):
        r = self.morph_color.red()
        g = self.morph_color.green()
        b = self.morph_color.blue()
        self.morph_preview.setStyleSheet(
            f"""
            QFrame {{
                background-color: rgb({r}, {g}, {b});
                border-radius: 6px;
                border: 1px solid palette(mid);
            }}
            """
        )

    def choose_color(self):
        color = QColorDialog.getColor(self.current_color, self, "Choose LED color")
        if color.isValid():
            self.current_color = color
            self.refresh_preview()

    def choose_morph_color(self):
        color = QColorDialog.getColor(self.morph_color, self, "Choose morph target color")
        if color.isValid():
            self.morph_color = color
            self.refresh_morph_preview()

    def update_morph_ui(self, effect):
        self.morph_container.setVisible(effect == "morph")

    def apply_color(self):
        r = self.current_color.red()
        g = self.current_color.green()
        b = self.current_color.blue()
        brightness = self.brightness_slider.value()

        self.status_label.setText("Applying static color…")
        QApplication.processEvents()

        try:
            elc = ELC(VID, PID)
            with elc:
                elc.execute(SetDimCommand(100 - brightness, ZONE_ALL))
            set_static_color(elc, r, g, b)
            self.status_label.setText(f"Applied: rgb({r}, {g}, {b})")
        except Exception as e:
            self.status_label.setText("Failed.")
            QMessageBox.critical(
                self,
                "Error",
                f"Could not apply color.\n\n{type(e).__name__}: {e}",
            )

    def preview_animation(self):
        effect = self.anim_combo.currentText()
        duration = self.duration_spin.value()
        tempo = self.tempo_spin.value()
        brightness = self.brightness_slider.value()

        self.status_label.setText(f"Previewing {effect}…")
        QApplication.processEvents()

        try:
            if effect == "morph":
                apply_temporary_effect(
                    effect,
                    self.current_color,
                    self.morph_color,
                    duration=duration,
                    tempo=tempo,
                    brightness=brightness,
                )
                r1, g1, b1 = qcolor_to_rgb(self.current_color)
                r2, g2, b2 = qcolor_to_rgb(self.morph_color)
                self.status_label.setText(
                    f"Previewing morph: rgb({r1}, {g1}, {b1}) -> rgb({r2}, {g2}, {b2})"
                )
            else:
                apply_temporary_effect(
                    effect,
                    self.current_color,
                    duration=duration,
                    tempo=tempo,
                    brightness=brightness,
                )
                r, g, b = qcolor_to_rgb(self.current_color)
                self.status_label.setText(
                    f"Previewing {effect}: rgb({r}, {g}, {b}), duration={duration}, tempo={tempo}"
                )
        except Exception as e:
            self.status_label.setText("Failed.")
            QMessageBox.critical(
                self,
                "Error",
                f"Could not preview animation.\n\n{type(e).__name__}: {e}",
            )


def main():
    app = QApplication(sys.argv)
    window = ColorWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

