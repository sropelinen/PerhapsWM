
import xcffib
from xcffib.xproto import Allow, Atom, ButtonIndex, ConfigWindow, \
    ClientMessageData, ClientMessageEvent, CW, EventMask, GrabMode, \
    InputFocus, ModMask, PropertyNotifyEvent, StackMode, Time, WindowError, \
    WindowClass
import xcffib.shape
from Xlib import XK


atom_names = (
    "ATOM",
    "STRING",
    "UTF8_STRING",
    "WM_PROTOCOLS",
    "WM_DELETE_WINDOW",
    "_NET_WM_VISIBLE_NAME",
    "_NET_WM_NAME",
    "WM_NAME",
    "WM_CLASS",
    "WM_WINDOW_ROLE"
)


configure_masks = {
    "x": ConfigWindow.X,
    "y": ConfigWindow.Y,
    "width": ConfigWindow.Width,
    "height": ConfigWindow.Height,
    "stack": ConfigWindow.StackMode,
    "border": ConfigWindow.BorderWidth
}


class Connection:

    def __init__(self):
        self.conn = xcffib.connect()
        self.default_screen = self.conn.get_setup() \
            .roots[self.conn.pref_screen]
        self.root = self.default_screen.root
        self.root_width = self.default_screen.width_in_pixels
        self.root_height = self.default_screen.height_in_pixels
        self.keycodes = self.get_keycodes()
        self.atoms = self.get_atoms(atom_names)

    def get_next_event(self):
        return self.conn.wait_for_event()

    def map_window(self, wid):
        self.conn.core.MapWindow(wid)
        self.conn.flush()

    def unmap_window(self, wid):
        self.conn.core.UnmapWindow(wid)
        self.conn.flush()

    def unmap_subwindows(self, wid):
        self.conn.core.UnmapSubwindows(wid)
        self.conn.flush()

    def reparent_window(self, wid, parent):
        self.conn.core.ReparentWindow(wid, parent, 0, 0)
        self.conn.flush()

    def configure_window(self, wid, **kwargs):
        values = []
        mask = 0
        for key in kwargs:
            if key in configure_masks:
                values.append(kwargs[key])
                mask |= configure_masks[key]
        self.conn.core.ConfigureWindow(wid, mask, values)
        self.conn.flush()

    def get_size(self, wid):
        r = self.conn.core.GetGeometry(wid).reply()
        return r.width, r.height

    def close_window(self, wid):
        properties = self.get_property(wid, "WM_PROTOCOLS", "ATOM")
        if self.atoms["WM_DELETE_WINDOW"] in properties:
            data = ClientMessageData.synthetic(
                [self.atoms["WM_DELETE_WINDOW"], Time.CurrentTime, 0, 0, 0],
                "I" * 5
            )
            event = ClientMessageEvent.synthetic(
                format=32, window=wid, data=data,
                type=self.atoms["WM_PROTOCOLS"]
            ).pack()
            self.conn.core.SendEvent(False, wid, EventMask.NoEvent, event)
        else:
            self.conn.core.KillClient(wid)
        self.conn.flush()

    def set_event_mask(self, wid, mask):
        self.conn.core.ChangeWindowAttributes(wid, CW.EventMask, [mask])
        self.conn.flush()

    def grab_key(self, wid, key, mod):
        if isinstance(key, str):
            keysym = XK.string_to_keysym(key)
            keycode = self.keycodes[keysym]
        elif isinstance(key, int):
            keycode = key
        else:
            raise ValueError
        self.conn.core.GrabKey(
            False, wid, mod, keycode, GrabMode.Async, GrabMode.Async
        )
        self.conn.flush()

    def grab_button_press(self, wid, button, mod):
        self.conn.core.GrabButton(
            True, wid, EventMask.ButtonPress, GrabMode.Sync, GrabMode.Async,
            Atom._None, Atom._None, button, mod
        )
        self.conn.flush()

    def grab_button_release(self, wid, button, mod):
        self.conn.core.GrabButton(
            True, wid, EventMask.ButtonRelease | EventMask.ButtonMotion,
            GrabMode.Async, GrabMode.Async, Atom._None, Atom._None, button,
            mod
        )
        self.conn.flush()

    def replay_pointer(self, time):
        self.conn.core.AllowEvents(Allow.ReplayPointer, time)
        self.conn.flush()

    def set_input_focus(self, wid):
        self.conn.core.SetInputFocus(
            InputFocus.PointerRoot, wid, Time.CurrentTime
        )
        self.conn.flush()

    def get_window_name(self, wid):
        for n in ["_NET_WM_VISIBLE_NAME", "_NET_WM_NAME", "WM_NAME"]:
            name = self.get_property(wid, n, "UTF8_STRING")
            if name:
                return name
        return ""

    def get_window_classes(self, wid):
        chars = list(self.get_property(wid, "WM_CLASS", "STRING"))
        classes = []
        while "\x00" in chars:
            i = chars.index("\x00")
            classes.append("".join(chars[:i]))
            chars = chars[i + 1:]
        return classes

    def get_window_role(self, wid):
        return self.get_property(wid, "WM_WINDOW_ROLE", "STRING")

    def get_property(self, wid, property, type):
        value = self.conn.core.GetProperty(
            False, wid, self.atoms[property], self.atoms[type], 0,
            (2 ** 32) - 1
        ).reply().value
        if type == "UTF8_STRING":
            return value.to_utf8()
        elif type == "STRING":
            return value.to_string()
        elif type == "ATOM":
            return value.to_atoms()
        raise ValueError(type)

    def string_to_keycode(self, string):
        return self.keycodes[XK.string_to_keysym(string)]

    def get_keycodes(self):
        setup = self.conn.get_setup()
        first = setup.min_keycode
        count = setup.max_keycode - first + 1
        reply = self.conn.core.GetKeyboardMapping(first, count).reply()

        keycodes = {}
        for i in range(len(reply.keysyms) // reply.keysyms_per_keycode):
            sym = reply.keysyms[i * reply.keysyms_per_keycode]
            if sym:
                keycodes[sym] = first + i

        return keycodes

    def get_atoms(self, names):
        try:
            atoms = {}
            for n in names:
                atoms[n] = self.conn.core.InternAtom(False, len(n), n) \
                    .reply().atom
            return atoms
        except TypeError as e:
            print(e)

    def get_corner(self, wid, x, y):
        corner = ""
        geometry = self.conn.core.GetGeometry(wid).reply()
        if y < geometry.y + geometry.height / 2:
            corner += "N"
        else:
            corner += "S"
        if x < geometry.x + geometry.width / 2:
            corner += "W"
        else:
            corner += "E"
        return corner

    def is_inside(self, wid, x, y):
        geometry = self.conn.core.GetGeometry(wid).reply()
        if x >= geometry.x and x <= geometry.x + geometry.width \
                and y >= geometry.y and y <= geometry.y + geometry.height:
            return True
        return False

    def update_corners(self, wid, rad_top, rad_bot):
        if rad_top > 0 or rad_bot > 0:
            dia_top = rad_top * 2 - 1 if rad_top > 0 else 0
            dia_bot = rad_bot * 2 - 1 if rad_bot > 0 else 0
            geometry = self.conn.core.GetGeometry(wid).reply()
            width = geometry.width
            height = geometry.height
            pixmap = self.conn.generate_id()
            self.conn.core.CreatePixmap(1, pixmap, wid, width, height)
            black = self.conn.generate_id()
            white = self.conn.generate_id()
            self.conn.core.CreateGC(black, pixmap, xcffib.xproto.GC.Foreground,
                                    [self.default_screen.black_pixel])
            self.conn.core.CreateGC(white, pixmap, xcffib.xproto.GC.Foreground,
                                    [self.default_screen.white_pixel])
            main_rect = [
                xcffib.xproto.RECTANGLE.synthetic(0, 0, width, height)
            ]
            corner_rects = [
                xcffib.xproto.RECTANGLE.synthetic(0, 0, rad_top, rad_top),
                xcffib.xproto.RECTANGLE.synthetic(
                        width - rad_top, 0, rad_top, rad_top),
                xcffib.xproto.RECTANGLE.synthetic(
                        0, height - rad_bot, rad_bot, rad_bot),
                xcffib.xproto.RECTANGLE.synthetic(
                        width - rad_bot, height - rad_bot, rad_bot, rad_bot)
            ]
            corner_arcs = [
                xcffib.xproto.ARC.synthetic(
                        -1, -1, dia_top, dia_top, 0, 360 << 6),
                xcffib.xproto.ARC.synthetic(
                        width - dia_top, -1, dia_top, dia_top, 0, 360 << 6),
                xcffib.xproto.ARC.synthetic(
                        -1, height - dia_bot, dia_bot, dia_bot, 0, 360 << 6),
                xcffib.xproto.ARC.synthetic(
                        width - dia_bot, height - dia_bot, dia_bot, dia_bot,
                        0, 360 << 6)
            ]
            self.conn.core.PolyFillRectangle(pixmap, white, 1, main_rect)
            self.conn.core.PolyFillRectangle(pixmap, black, 4, corner_rects)
            self.conn.core.PolyFillArc(pixmap, white, 4, corner_arcs)
            shape = xcffib.shape.shapeExtension(
                        self.conn, key=xcffib.ExtensionKey("SHAPE"))
            shape.Mask(xcffib.shape.SO.Set, xcffib.shape.SK.Bounding, wid, 0,
                       0, pixmap)
            self.conn.core.FreePixmap(pixmap)
            self.conn.flush()

    def set_border_color_white(self, wid):
        pixel = self.default_screen.white_pixel
        self.conn.core.ChangeWindowAttributes(wid, CW.BorderPixel, [pixel])
        self.conn.flush()
