from objc_util import ObjCClass, load_framework
import time

load_framework("GameController")
GCController = ObjCClass("GCController")

def btn_pressed(btn):
    return bool(btn and btn.isPressed())

def axis_val(axis):
    return float(axis.value()) if axis else 0.0

class Controller:
    def __init__(self, obj, index=0):
        self.obj = obj
        self.index = index
        self.name = str(obj.vendorName() or f"Controller {index+1}")
        self.prev_buttons, self.prev_axes = {}, {}
        self.deadzone = 0.05
        self.connected = True
        self.callbacks = {
            "button_down": {},
            "button_up": {},
            "axis": {},
        }

    def on_button_down(self, btn, func): self.callbacks["button_down"][btn] = func

    def on_button_up(self, btn, func): self.callbacks["button_up"][btn] = func

    def on_axis(self, axis, func): self.callbacks["axis"][axis] = func

    def is_button_pressed(self, name): return self.prev_buttons.get(name, False)

    def get_axis(self, name): return self.prev_axes.get(name, 0.0)

    def set_deadzone(self, dz): self.deadzone = max(0.0, min(dz, 1.0))

    def set_player_index(self, idx):
        self.index = idx
        if hasattr(self.obj, "setPlayerIndex_"):
            try: self.obj.setPlayerIndex_(idx)
            except Exception: pass

    def vibrate(self, low_freq=1.0, high_freq=1.0, duration=0.3):
        try:
            haptics = getattr(self.obj, "haptics", None)
            if haptics:
                engine = haptics().createEngineWithLocality_("all")
                if engine:
                    engine.start()
                    event = getattr(engine, "createContinuousHapticEventWithIntensity_frequency_relativeTime_duration_", None)
                    if event:
                        event_obj = event(max(low_freq, high_freq), 1.0, 0.0, duration)
                        engine.playPattern_(event_obj)
                    else:
                        time.sleep(duration)
                    engine.stop()
                    return True
            profile = getattr(self.obj, "physicalInputProfile", lambda: None)()
            rumble = getattr(self.obj, "rumble", None) or getattr(profile, "rumble", None)
            if rumble and hasattr(rumble, "startWithIntensity_duration_"):
                rumble.startWithIntensity_duration_(max(low_freq, high_freq), duration)
                time.sleep(duration)
                rumble.stop()
                return True
            return False
        except Exception as e:
            print(f"{self.name}: Error triggering rumble → {e}")
            return False

    def disconnect(self):
        self.connected = False

    def reconnect(self, obj, index):
        self.obj, self.index, self.connected = obj, index, True

    def get_state(self):
        return {"buttons": dict(self.prev_buttons), "axes": dict(self.prev_axes)}

    def get_buttons(self):
        gp = self.obj.extendedGamepad() or self.obj.microGamepad()
        if not gp: return {}
        button_map = {
            "A": "buttonA", "B": "buttonB", "X": "buttonX", "Y": "buttonY",
            "LB": "leftShoulder", "RB": "rightShoulder",
            "LT": "leftTrigger", "RT": "rightTrigger",
            "L3": "leftThumbstickButton", "R3": "rightThumbstickButton",
            "Menu": "buttonMenu", "Options": "buttonOptions", "Home": "buttonHome",
        }
        btns = {name: getattr(gp, attr)() for name, attr in button_map.items() if hasattr(gp, attr)}
        if hasattr(gp, "dpad"):
            dpad = gp.dpad()
            if dpad:
                btns.update({
                    "DPad Up": dpad.up(),
                    "DPad Down": dpad.down(),
                    "DPad Left": dpad.left(),
                    "DPad Right": dpad.right(),
                })
        return btns

    def get_axes(self):
        gp = self.obj.extendedGamepad() or self.obj.microGamepad()
        if not gp: return {}
        axes = {}
        if hasattr(gp, "leftThumbstick"):
            stick = gp.leftThumbstick()
            axes["LX"], axes["LY"] = axis_val(stick.xAxis()), axis_val(stick.yAxis())
        if hasattr(gp, "rightThumbstick"):
            stick = gp.rightThumbstick()
            axes["RX"], axes["RY"] = axis_val(stick.xAxis()), axis_val(stick.yAxis())
        return axes

    def poll(self):
        if not self.connected: return
        btns, axes = self.get_buttons(), self.get_axes()
        for name, btn in btns.items():
            pressed, prev = btn_pressed(btn), self.prev_buttons.get(name, False)
            if pressed != prev:
                cb_type = "button_down" if pressed else "button_up"
                if name in self.callbacks[cb_type]:
                    self.callbacks[cb_type][name](self)
            self.prev_buttons[name] = pressed
        for axis, val in axes.items():
            prev_val = self.prev_axes.get(axis, 0.0)
            if abs(val - prev_val) > self.deadzone and axis in self.callbacks["axis"]:
                self.callbacks["axis"][axis](self, val)
            self.prev_axes[axis] = val

class ControllerManager:
    def __init__(self):
        self.controllers = []
        self.discover()

    def discover(self, timeout=5):
        arr = GCController.controllers()
        if arr and arr.count() > 0:
            self.controllers = [Controller(c, i) for i, c in enumerate(arr)]
            return
        try: GCController.startWirelessControllerDiscoveryWithCompletionHandler_(None)
        except Exception: pass
        for _ in range(timeout):
            arr = GCController.controllers()
            if arr and arr.count() > 0:
                self.controllers = [Controller(c, i) for i, c in enumerate(arr)]
                return
            time.sleep(1)

    def poll_all(self):
        current_objs = list(GCController.controllers()) or []
        current_map = {int(obj.hash()): obj for obj in current_objs}
        for ctrl in self.controllers:
            if ctrl.connected and int(ctrl.obj.hash()) not in current_map:
                ctrl.disconnect()
        for i, obj in enumerate(current_objs):
            obj_id = int(obj.hash())
            found = next((c for c in self.controllers if int(c.obj.hash()) == obj_id), None)
            if not found:
                new_ctrl = Controller(obj, i)
                self.controllers.append(new_ctrl)
            elif not found.connected:
                found.reconnect(obj, i)
        for c in self.controllers:
            if c.connected:
                c.poll()

    def get_controller(self, index): return self.controllers[index] if 0 <= index < len(self.controllers) else None

    def broadcast(self, func): [func(c) for c in self.controllers if c.connected]

    def active_controllers(self): return [c for c in self.controllers if c.connected]

    def wait_for_new_controller(self, timeout=10):
        start, prev_count = time.time(), len(self.controllers)
        while time.time() - start < timeout:
            arr = GCController.controllers()
            if arr and arr.count() > prev_count:
                self.controllers = [Controller(c, i) for i, c in enumerate(arr)]
                return self.controllers[-1]
            time.sleep(0.5)
        return None
