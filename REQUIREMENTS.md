# Note: This was done on a Debian 13 (Trixie) Dell G5 5000 PC.

# Requirements & Setup Guide

## 1. Hardware Requirements
* Supported Device: Dell or Alienware system/peripheral with the LED controller matching VID: 0x187C and PID: 0x0550.

## 2. Software & Dependencies
* Python Version: Python 3.7 or higher
* Python Packages: PySide6 (GUI), pyusb (USB communication)
* Installation command:
    pip install PySide6 pyusb

## 3. Required Directory Structure
The main GUI script modifies the system path to locate the local elc_ng.py library. You must maintain this exact relative folder structure:

your_project_root/
├── elc_ng.py                         
└── some_folder/                      
    └── gui_color_picker-commented.py 

## 4. System Permissions (Linux)
To allow the script to communicate with the USB controller without requiring root (sudo) privileges, you must set up a udev rule.

1. Create a new rules file:
    sudo nano /etc/udev/rules.d/99-dell-led.rules

2. Add the following line to grant read/write access to standard users:
    SUBSYSTEM=="usb", ATTR{idVendor}=="187c", ATTR{idProduct}=="0550", MODE="0666"

3. Save the file and reload the udev rules:
    sudo udevadm control --reload-rules && sudo udevadm trigger

## 5. Execution
Once the dependencies are installed and the udev rules are applied, navigate to the folder containing the GUI script and run it:
    python3 gui_color_picker-commented.py
