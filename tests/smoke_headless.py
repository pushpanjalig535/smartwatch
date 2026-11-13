"""Headless smoke test of the application logic WITHOUT Panda3D installed.

Panda3D / DirectGui are replaced by permissive mocks, then the real HoloApp
update loop is executed through the whole cinematic intro and every control.
This catches wiring bugs (wrong attribute names, array shape errors, state
bugs).  It does NOT validate actual rendering - run `python main.py` for that.

    python tests/smoke_headless.py
"""
import os
import sys
import types
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FakeModule(types.ModuleType):
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        m = MagicMock(name=f"{self.__name__}.{name}")
        setattr(self, name, m)
        return m


def install_fakes():
    for name in ("panda3d", "panda3d.core", "direct", "direct.showbase", "direct.showbase.ShowBase",
                 "direct.gui", "direct.gui.DirectGui", "direct.gui.OnscreenText", "direct.filter",
                 "direct.filter.CommonFilters"):
        sys.modules[name] = FakeModule(name)

    class Clock:
        dt = 1 / 60

        def getDt(self):
            return Clock.dt

    class ClockObject:
        @staticmethod
        def getGlobalClock():
            return Clock()

    sys.modules["panda3d.core"].ClockObject = ClockObject

    class ShowBase:
        def __init__(self):
            self.__dict__["_m"] = MagicMock()

        def __getattr__(self, n):
            if n.startswith("__"):
                raise AttributeError(n)
            return getattr(self.__dict__["_m"], n)

        def run(self):
            pass

    sys.modules["direct.showbase.ShowBase"].ShowBase = ShowBase


def main():
    install_fakes()
    import numpy as np
    import holowatch.app as appmod
    from holowatch import timeline

    appmod.mat4_to_np = lambda m: np.eye(4, dtype=np.float32)

    class FakeUI:
        def __init__(self, app): self.app, self.log = app, []
        def sync(self): pass
        def log_event(self, s): self.log.append(s)
        def set_alpha(self, a): pass
        def update(self, *a, **k): pass

    appmod.Dashboard = FakeUI
    app = appmod.HoloApp(skip_intro=False, audio=False)
    frames = 0

    def run(seconds, dt=1 / 60):
        nonlocal frames
        for _ in range(int(seconds / dt)):
            assert app._update(MagicMock()) is not None
            frames += 1

    run(timeline.INTRO_DURATION + 1.0)
    assert app.t > timeline.INTRO_DURATION and app.lv["done"] and app.lv["form"] == 1.0
    assert app.screen.page == 1, "health screen should be active after the intro"
    print("intro ok, frames:", frames)

    for fn in (app.toggle_wireframe, app.toggle_particles, app.toggle_scanning, app.toggle_xray,
               app.toggle_explode, app.toggle_pause):
        fn(); run(1.2); fn(); run(0.5)
    app.toggle_inspect()
    run(timeline.__dict__.get("X", 0) or 20.0)
    assert not app.state.inspect, "inspection sequence should finish by itself"
    app.toggle_projection(); run(3.0)
    assert app.proj == 0.0 and app.lv["form"] == 0.0
    app.toggle_projection(); run(3.0)
    assert app.proj == 1.0
    for i in range(5):
        app.screen_page(i); run(0.2)
    app.set_brightness(1.4); app.set_speed(90); app.set_size(1.3); run(0.5)
    app.reset_view()
    assert app.state.size == 1.0 and app.state.speed == 20.0 and app.heading == 0.0
    # skip-intro path
    app2 = appmod.HoloApp(skip_intro=True, audio=False)
    app2._update(MagicMock())
    assert app2.lv["done"] and app2.screen.page == 1
    print("ALL SMOKE CHECKS PASSED, frames:", frames)


if __name__ == "__main__":
    main()
