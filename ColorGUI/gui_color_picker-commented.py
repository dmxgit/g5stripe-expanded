#!/usr/bin/python3
import sys
from pathlib import Path

# PySide6 imports for GUI components
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

# Dynamically add the parent directory to sys.path to resolve local imports
HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
if str(PARENT) not in sys.path:
    sys.path.insert(0, str(PARENT))

# Local hardware control library imports
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

# Hardware USB Vendor and Product IDs for the Dell LED controller
VID = 0x187C
PID = 0x0550


def qcolor_to_rgb(color):
    """Converts a PySide QColor object to a standard RGB tuple."""
    return color.red(), color.green(), color.blue()


def apply_temporary_effect(effect_name, color1, color2=None, duration=3000, tempo=80, brightness=100):
    """
    Sends animation commands directly to the hardware controller.
    Configures brightness, sets up the animation blocks (standard or morph),
    and triggers playback.
    """
    r1, g1, b1 = qcolor_to_rgb(color1)

    elc = ELC(VID, PID)
    with elc:
        # Calculate dim level (0 is full brightness, 100 is off)
        elc.execute(SetDimCommand(100 - brightness, ZONE_ALL))
        elc.execute(AnimationCommand("config_start", 0))
        elc.execute(ZoneSelectCommand(1, ZONE_ALL))

        if effect_name == "morph":
            # If no secondary color is provided, default to an inverted color
            if color2 is None:
                color2 = QColor(255 - r1, 255 - g1, 255 - b1)
            r2, g2, b2 = qcolor_to_rgb(color2)

            # Morph requires two actions to interpolate between colors
            elc.execute(AddActionsCommand([
                Action("morph", r1, g1, b1, duration=duration, tempo=tempo)
            ]))
            elc.execute(AddActionsCommand([
                Action("morph", r2, g2, b2, duration=duration, tempo=tempo)
            ]))
        else:
            # Standard single-color effects (e.g., pulse, color)
            elc.execute(AddActionsCommand([
                Action(effect_name, r1, g1, b1, duration=duration, tempo=tempo)
            ]))

        elc.execute(AnimationCommand("config_play", 0))


class ColorWindow(QMainWindow):
    """Main graphical interface for controlling the Dell/AlienFX LEDs."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dell LED Color")
        self.resize(430, 420)

        # Default state variables
        self.current_color = QColor(0, 255, 0)
        self.morph_color = QColor(0, 0, 255)

        # Main layout setup
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # --- Header Section ---
        title = QLabel("Dell / AlienFX color")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        root.addWidget(title)

        # --- Primary Color Preview Section ---
        self.preview = QFrame()
        self.preview.setFixedHeight(56)
        self.preview.setFrameShape(QFrame.StyledPanel)
        self.preview.setStyleSheet("border-radius: 10px; border: 1px solid palette(mid);")
        root.addWidget(self.preview)

        self.rgb_label = QLabel()
        self.rgb_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        root.addWidget(self.rgb_label)

        # --- Quick Presets Grid ---
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

        # Generate preset buttons dynamically
        for i, (name, rgb) in enumerate(presets):
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked=False, rgb=rgb: self.set_color(*rgb))
            preset_layout.addWidget(btn, i // 3, i % 3)

        # --- Custom Color & Apply Buttons ---
        buttons = QHBoxLayout()
        root.addLayout(buttons)

        choose_btn = QPushButton("Choose color…")
        choose_btn.clicked.connect(self.choose_color)
        buttons.addWidget(choose_btn)

        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self.apply_color)
        buttons.addWidget(apply_btn)

        # --- Animation Settings Section ---
        animation_title = QLabel("Animation")
        animation_title.setStyleSheet("font-weight: 600; margin-top: 6px;")
        root.addWidget(animation_title)

        anim_form = QFormLayout()
        root.addLayout(anim_form)

        # Effect selection dropdown
        self.anim_combo = QComboBox()
        self.anim_combo.addItems(["color", "pulse", "morph"])
        self.anim_combo.currentTextChanged.connect(self.update_morph_ui)
        anim_form.addRow("Type:", self.anim_combo)

        # Duration control
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(100, 20000)
        self.duration_spin.setSingleStep(100)
        self.duration_spin.setValue(3000)
        self.duration_spin.setSuffix(" ms")
        anim_form.addRow("Duration:", self.duration_spin)

        # Tempo control
        self.tempo_spin = QSpinBox()
        self.tempo_spin.setRange(1, 1000)
        self.tempo_spin.setValue(80)
        anim_form.addRow("Tempo:", self.tempo_spin)

        # Brightness control
        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setRange(0, 100)
        self.brightness_slider.setValue(100)
        anim_form.addRow("Brightness:", self.brightness_slider)

        # Morph target color picker (conditionally visible)
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

        # --- Animation Preview Button ---
        anim_buttons = QHBoxLayout()
        root.addLayout(anim_buttons)

        preview_anim_btn = QPushButton("Preview animation")
        preview_anim_btn.clicked.connect(self.preview_animation)
        anim_buttons.addWidget(preview_anim_btn)

        # --- Status Bar ---
        self.status_label = QLabel("Ready.")
        self.status_label.setStyleSheet("color: palette(mid);")
        root.addWidget(self.status_label)

        # Initialize UI states
        self.refresh_preview()
        self.refresh_morph_preview()
        self.update_morph_ui(self.anim_combo.currentText())

    def set_color(self, r, g, b):
        """Updates the internal primary color state and refreshes the UI."""
        self.current_color = QColor(r, g, b)
        self.refresh_preview()

    def refresh_preview(self):
        """Updates the main color preview box and RGB/HEX text labels."""
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
        """Updates the smaller preview box used for the morph target color."""
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
        """Opens a standard OS color picker dialog for the primary color."""
        color = QColorDialog.getColor(self.current_color, self, "Choose LED color")
        if color.isValid():
            self.current_color = color
            self.refresh_preview()

    def choose_morph_color(self):
        """Opens a standard OS color picker dialog for the secondary morph color."""
        color = QColorDialog.getColor(self.morph_color, self, "Choose morph target color")
        if color.isValid():
            self.morph_color = color
            self.refresh_morph_preview()

    def update_morph_ui(self, effect):
        """Toggles the visibility of the morph target selection row based on effect type."""
        self.morph_container.setVisible(effect == "morph")

    def apply_color(self):
        """Sends the static color application command to the hardware."""
        r = self.current_color.red()
        g = self.current_color.green()
        b = self.current_color.blue()
        brightness = self.brightness_slider.value()

        self.status_label.setText("Applying static color…")
        QApplication.processEvents()  # Force UI update

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
        """Extracts animation parameters from the UI and triggers the effect."""
        effect = self.anim_combo.currentText()
        duration = self.duration_spin.value()
        tempo = self.tempo_spin.value()
        brightness = self.brightness_slider.value()

        self.status_label.setText(f"Previewing {effect}…")
        QApplication.processEvents()  # Force UI update

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
    """Application entry point."""
    app = QApplication(sys.argv)
    window = ColorWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
