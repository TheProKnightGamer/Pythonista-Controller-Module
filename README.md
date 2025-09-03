# Pythonista-Controller-Module

A Python wrapper for Apple’s GameController framework via objc_util.

Overview
--------
Provides:
- Detecting and managing multiple controllers.
- Polling button and axis states.
- Handling button/axis events via callbacks.
- Controller rumble/vibration (when supported).
- Hot-plugging (detecting disconnects/reconnects).

Requirements
------------
- Pythonista (iOS) with `objc_util`
- iOS/iPadOS with the GameController framework
- Compatible controller (Xbox, PlayStation, MFi, etc.)

Module Contents
---------------
Utility Functions
- btn_pressed(btn) -> bool: True if the button is pressed.
- axis_val(axis) -> float: Current axis value (-1.0 to 1.0).

Class: Controller
-----------------
Represents a single controller.

Attributes:
- obj: Objective-C GCController instance.
- index: Assigned player index.
- name: Vendor name or fallback ("Controller N").
- connected: Boolean connection status.
- deadzone: Minimum axis change required to trigger callbacks.
- prev_buttons: Last known button states.
- prev_axes: Last known axis values.

Methods:
- on_button_down(name, func)
- on_button_up(name, func)
- on_axis(name, func)
- is_button_pressed(name) -> bool
- get_axis(name) -> float
- get_state() -> dict
- set_deadzone(value)
- set_player_index(idx)
- vibrate(low_freq=1.0, high_freq=1.0, duration=0.3) -> bool
- disconnect()
- reconnect(obj, index)
- poll()
- get_buttons() -> dict
- get_axes() -> dict

Class: ControllerManager
------------------------
Manages multiple controllers.

Attributes:
- controllers: List of Controller objects.

Methods:
- discover(timeout=5)
- poll_all()
- get_controller(index) -> Controller | None
- broadcast(func)
- active_controllers() -> list
- wait_for_new_controller(timeout=10) -> Controller | None

Supported Input Names
---------------------
Buttons: "A", "B", "X", "Y", "LB", "RB", "LT", "RT", "L3", "R3",
         "Menu", "Options", "Home", "DPad Up", "DPad Down",
         "DPad Left", "DPad Right"
Axes: "LX", "LY", "RX", "RY"

Notes
-----
- Rumble support varies by controller.
- Deadzone is per-controller.
- Always call poll_all() frequently.
- Hot-plugging supported via polling.

Example can be found in example.py
----------------------------------
