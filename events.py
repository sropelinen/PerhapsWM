
from xcffib.xproto import ButtonPressEvent, ConfigureRequestEvent, \
    DestroyNotifyEvent, KeyPressEvent, MapNotifyEvent, MapRequestEvent, \
    PropertyNotifyEvent, WindowError, ClientMessageEvent, ButtonIndex, \
    ModMask, ButtonReleaseEvent, MotionNotifyEvent, EventMask, \
    EnterNotifyEvent

import x
import wm
from util import parse_keybinds


class EventHandler:

    def __init__(self, layouts, keybinds):
        self.conn = x.Connection()
        self.wm = wm.WindowManager(self.conn, layouts)
        self.kb = parse_keybinds(self.conn, self.wm, keybinds)
        self.sleep_time = 0.1

    def run(self):
        prev_time = 0

        pn_atoms = self.conn.get_atoms([
            "WM_NAME", "_NET_WM_NAME", "_NET_WM_VISIBLE_NAME",
            "WM_ICON_NAME", "_NET_WM_ICON_NAME", "_NET_WM_VISIBLE_ICON_NAME",
            "WM_NORMAL_HINTS", "_NET_WM_USER_TIME"
        ])
        names = ["WM_{}NAME", "_NET_WM_{}NAME", "_NET_WM_VISIBLE_{}NAME"]

        while True:
            try:
                event = self.conn.get_next_event()
                if isinstance(event, MapRequestEvent):
                    self.wm.map_request(event.window)
                elif isinstance(event, DestroyNotifyEvent):
                    self.wm.close_tab(event.window)
                elif isinstance(event, ConfigureRequestEvent):
                    self.wm.configure(event)
                elif isinstance(event, KeyPressEvent):
                    if event.time - prev_time > self.sleep_time * 1000:
                        code = event.detail
                        mods = event.state
                        if self.kb and code in self.kb \
                                and mods in self.kb[code]:
                            self.kb[code][mods][0](*self.kb[code][mods][1:])
                        prev_time = event.time
                elif isinstance(event, ButtonPressEvent):
                    self.wm.focus_frame(event.child)
                    self.wm.button_press(event)
                    self.conn.replay_pointer(event.time)
                elif isinstance(event, MotionNotifyEvent):
                    self.wm.button_motion(event)
                    self.conn.replay_pointer(event.time)
                elif isinstance(event, ButtonReleaseEvent):
                    self.wm.button_release(event)
                    self.conn.replay_pointer(event.time)
                elif isinstance(event, PropertyNotifyEvent):
                    if event.atom == pn_atoms["WM_NORMAL_HINTS"]:
                        self.wm.handle_property_normal_hints(event.window)
                    elif event.atom == pn_atoms["_NET_WM_USER_TIME"]:
                        self.wm.update_tab_order(event.window)
                    else:
                        for n in names:
                            if event.atom == pn_atoms[n.format("")]:
                                self.wm.set_name(event.window)
                                break
                            elif event.atom == pn_atoms[n.format("ICON_")]:
                                self.wm.set_icon_name(event.window)
                                break
                elif isinstance(event, ClientMessageEvent):
                    self.wm.check_tab_amount(event)
                elif isinstance(event, EnterNotifyEvent):
                    self.wm.enter_window(event)
                elif isinstance(event, MapNotifyEvent):
                    pass

            except WindowError as e:
                print(e)
