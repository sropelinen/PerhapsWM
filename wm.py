
import dbus
import sys
import os
import subprocess

from xcffib.xproto import ButtonIndex, ButtonPressEvent, \
    ConfigureRequestEvent, DestroyNotifyEvent, EventMask, \
    KeyPressEvent, MapRequestEvent, ModMask, PropertyNotifyEvent, \
    StackMode, WindowError

from layout import LayoutManager
import decorations


class WindowManager:

    def __init__(self, connection, layouts):

        self.conn = connection

        self.unmapped = {}
        self.next_is_tab = False
        self.bg_prev_size = None

        self.drag = 0
        self.drag_frame = None
        self.start_x = None
        self.start_y = None
        self.min_change = 25
        self.change_x = 0
        self.change_y = 0
        self.corner = ""
        self.grid = False

        self.lm = LayoutManager(
            self.conn, layouts, self.conn.root_width, self.conn.root_height
        )

        self.conn.set_event_mask(
            self.conn.root,
            EventMask.SubstructureNotify | EventMask.SubstructureRedirect
        )
        self.conn.grab_button_press(self.conn.root, ButtonIndex.Any,
                                    ModMask.Any)
        self.conn.grab_button_release(self.conn.root, ButtonIndex._1,
                                      ModMask._1)
        self.conn.grab_button_release(self.conn.root, ButtonIndex._3,
                                      ModMask._1)

        self.decorations = self.connect_dbus(
            "org.wm.Frames", "/org/wm/Frames"
        )

    def connect_dbus(self, name, path):
        decorations.run()
        try:
            bus = dbus.SessionBus()
            bus_obj = bus.get_object(name, path)
            return dbus.Interface(bus_obj, name)
        except dbus.DBusException as e:
            sys.exit(e)

    def map_request(self, wid):
        role = self.conn.get_window_role(wid)
        if role == "grid":
            self.conn.map_window(wid)
        else:
            if wid in self.unmapped:
                self.map_unmapped(wid)
            else:
                if not self.lm.get_n_frames() or not self.next_is_tab:
                    self.append_unmapped(wid)
                else:
                    self.map_new_tab(wid)

    def map_unmapped(self, fid):
        prev_fid = self.get_focused_fid()
        wid = self.unmapped[fid]

        self.conn.set_event_mask(
            fid, EventMask.SubstructureNotify | EventMask.PropertyChange
            | EventMask.EnterWindow
        )
        self.lm.append_frame(fid, wid)
        self.lm.set_position(fid, self.lm.get_position(prev_fid) + 1)
        self.append_client(fid, wid)

        self.conn.map_window(wid)
        if self.lm.get_frame(wid).decorations:
            self.conn.update_corners(wid, 0, 10)
        else:
            self.conn.update_corners(wid, 10, 10)
        self.conn.map_window(fid)
        self.focus_client(wid)

        del self.unmapped[fid]

    def append_unmapped(self, wid):
        fid = self.decorations.append_frame()
        self.append_tab(fid, wid)
        self.unmapped[fid] = wid

    def map_new_tab(self, wid):
        fid = self.get_focused_fid()
        self.append_client(fid, wid)
        self.append_tab(fid, wid)
        self.show_tab(wid)

    def append_client(self, fid, wid):
        self.conn.set_event_mask(
                wid, EventMask.PropertyChange | EventMask.StructureNotify)
        self.conn.reparent_window(wid, fid)
        self.lm.append_client(fid, wid)

    def append_tab(self, fid, wid):
        name = self.conn.get_window_name(wid)
        classes = self.conn.get_window_classes(wid)
        self.decorations.append_tab(fid, wid, name, classes)

    def set_name(self, wid):
        if self.lm.client_exists(wid):
            fid = self.lm.get_fid(wid)
            name = self.conn.get_window_name(wid)
            self.decorations.set_tab_name(fid, wid, name)

    def set_icon_name(self, wid):
        if self.lm.client_exists(wid):
            fid = self.lm.get_fid(wid)
            classes = self.conn.get_window_classes(wid)
            name = self.conn.get_window_name(wid)
            self.decorations.set_tab_icon(fid, wid, classes, name)

    def handle_property_normal_hints(self, fid):
        if self.lm.frame_exists(fid):
            wids = self.decorations.get_wids()
            if wids and fid in wids:
                cwids = []
                for cwid in self.lm.get_frame(fid).history:
                    cwids.append(cwid)
                for cwid in cwids:
                    if cwid not in wids[fid]:
                        fid2 = 0
                        for f in wids:
                            if f != fid:
                                for w in wids[f]:
                                    if w == cwid:
                                        fid2 = f
                                        wid = w
                        if fid2:
                            self.move_tab(fid, fid2, wid)
                        else:
                            self.conn.close_window(cwid)

    def update_tab_order(self, fid):
        if self.lm.frame_exists(fid):
            wid = int(self.decorations.get_active_client(fid))
            if wid and wid != self.lm.get_frame(wid).history[-1]:
                self.show_tab(wid)

    def check_tab_amount(self, event):
        data = event.data.data32
        if data[0] == 3 and not sum(data[1:]):
            fid = event.window
            dwids = self.decorations.get_wids()
            if dwids and fid in dwids:
                wids = self.lm.get_frame(fid).history
                if len(dwids[fid]) < len(wids):
                    for w in wids:
                        if w not in dwids[fid]:
                            self.conn.close_window(w)

    def toggle_next_tab(self):
        self.next_is_tab = not self.next_is_tab

    def close_tab(self, wid):
        if self.lm.client_exists(wid):
            frame = self.lm.get_frame(wid)
            if len(frame.history) <= 1:
                self.lm.remove_frame(frame.fid)
                self.decorations.remove_frame(frame.fid)
                if self.lm.get_n_frames():
                    self.focus_frame(self.lm.history[-1])
            else:
                self.lm.remove_client(frame.fid, wid)
                self.show_tab(frame.history[-1])
                self.decorations.remove_tab(frame.fid, wid)
            self.decorations.remove_color(wid)

    def move_tab(self, fid, fid2, wid):
        self.conn.reparent_window(wid, fid2)

        self.lm.remove_client(fid, wid)
        self.lm.append_client(fid2, wid)

        self.show_tab(wid)

        if self.lm.get_frame(fid).history:
            self.show_tab(self.lm.get_frame(fid).history[-1])
        else:
            self.lm.remove_frame(fid)
            self.decorations.remove_frame(fid)

    def show_tab(self, wid):
        if self.lm.client_exists(wid):
            frame = self.lm.get_frame(wid)
            self.conn.unmap_subwindows(frame.fid)
            self.conn.map_window(wid)
            if self.lm.get_frame(wid).decorations:
                self.conn.update_corners(wid, 0, 10)
            else:
                self.conn.update_corners(wid, 10, 10)

            if wid in frame.history:
                frame.history.remove(wid)
                frame.history.append(wid)

            self.decorations.goto_tab(frame.fid, wid)
            self.focus_client(wid)

    def focus_client(self, wid):
        fid = self.lm.get_frame(wid).fid
        self.lm.set_focused_frame(fid)
        self.conn.set_input_focus(wid)
        self.header_color(fid)

    def focus_frame(self, fid):
        if self.lm.frame_exists(fid):
            self.lm.set_focused_frame(fid)
            self.conn.set_input_focus(self.lm.get_frame(fid).history[-1])
            self.conn.configure_window(fid, stack=StackMode.Above)
            self.header_color(fid)

    def header_color(self, fid):
        self.decorations.set_header_color(fid, True)
        for f in self.lm.history:
            if f != fid:
                self.decorations.set_header_color(f, False)

    def get_focused_fid(self):
        if self.lm.history:
            return self.lm.history[-1]
        else:
            return 0

    def configure(self, event):
        if not self.lm.frame_exists(event.window):
            self.conn.configure_window(
                event.window, x=event.x, y=event.y, width=event.width,
                height=event.height, border=0
            )

    # Key bindings:

    def execute(self, command):
        if not os.fork():
            subprocess.Popen(["/bin/sh", "-c", command])
            os._exit(0)

    def destroy(self):
        fid = self.get_focused_fid()
        if fid:
            self.conn.close_window(self.lm.get_frame(fid).history[-1])

    def destroy_frame(self):
        fid = self.get_focused_fid()
        if fid:
            wids = []
            for wid in self.lm.get_frame(fid).history:
                wids.append(wid)
            for w in wids:
                self.conn.close_window(w)

    def next_frame(self):
        frame = self.lm.get_next_frame()
        if frame:
            self.focus_client(frame.history[-1])

    def prev_frame(self):
        frame = self.lm.get_prev_frame()
        if frame:
            self.focus_client(frame.history[-1])

    def next_tab(self):
        fid = self.get_focused_fid()
        if fid:
            wid = self.decorations.next_tab(fid)
            self.show_tab(wid)

    def prev_tab(self):
        fid = self.get_focused_fid()
        if fid:
            wid = self.decorations.prev_tab(fid)
            self.show_tab(wid)

    def set_tab(self, n):
        fid = self.get_focused_fid()
        if fid:
            wid = self.decorations.goto_tab_num(fid, n)
            if wid:
                self.show_tab(wid)

    def move_frame_next(self):
        fid = self.get_focused_fid()
        if fid:
            pos = self.lm.get_position(fid) + 1
            if pos >= self.lm.get_n_frames():
                pos = 0
            self.lm.set_position(fid, pos)

    def move_frame_prev(self):
        fid = self.get_focused_fid()
        if fid:
            pos = self.lm.get_position(fid) - 1
            if pos < 0:
                pos = self.lm.get_n_frames() - 1
            self.lm.set_position(fid, pos)

    def move_tab_next(self):
        fid = self.get_focused_fid()
        if fid:
            wid = self.lm.get_frame(fid).history[-1]
            self.decorations.change_tab_position_next(fid, wid)

    def move_tab_prev(self):
        fid = self.get_focused_fid()
        if fid:
            wid = self.lm.get_frame(fid).history[-1]
            self.decorations.change_tab_position_prev(fid, wid)

    def move_tab_next_frame(self):
        if self.lm.get_n_frames() > 1:
            fid = self.get_focused_fid()
            fid2 = self.lm.get_next_frame().fid
            wid = self.lm.get_frame(fid).history[-1]

            self.decorations.remove_tab(fid, wid)
            self.append_tab(fid2, wid)

            self.move_tab(fid, fid2, wid)
            if self.lm.get_frame(fid):
                self.show_tab(wid)

    def move_tab_prev_frame(self):
        if self.lm.get_n_frames() > 1:
            fid = self.get_focused_fid()
            fid2 = self.lm.get_prev_frame().fid
            wid = self.lm.get_frame(fid).history[-1]

            self.decorations.remove_tab(fid, wid)
            self.append_tab(fid2, wid)

            self.move_tab(fid, fid2, wid)
            if self.lm.get_frame(fid):
                self.show_tab(wid)

    def detach_tab(self):
        if self.lm.get_n_frames() > 0:
            fid = self.get_focused_fid()
            if len(self.lm.get_frame(fid).history) > 1:
                wid = self.lm.get_frame(fid).history[-1]

                self.lm.remove_client(fid, wid)
                self.decorations.remove_tab(fid, wid)
                self.show_tab(self.lm.get_frame(fid).history[-1])

                self.append_unmapped(wid)
                self.show_tab(wid)

    def toggle_decorations(self):
        fid = self.get_focused_fid()
        if fid:
            frame = self.lm.get_frame(fid)
            _, _, width, height = self.lm.get_dimensions(frame.history[-1])
            if frame.decorations:
                frame.decorations = False
                self.lm.move(fid, 0, 34)
                self.lm.set_size(fid, width, height)
            else:
                frame.decorations = True
                self.lm.move(fid, 0, -34)
                self.lm.set_size(fid, width, height + 34)

            self.lm.update_layout()
            self.decorations.toggle_decorations(fid)

    def set_workspace(self, id):
        self.lm.set_workspace(id)

    def next_workspace(self):
        if self.lm.workspace < self.lm.max_workspaces:
            self.lm.set_workspace(self.lm.workspace + 1)

    def prev_workspace(self):
        if self.lm.workspace != 0:
            self.lm.set_workspace(self.lm.workspace - 1)

    def move_frame_workspace(self, id):
        fid = self.get_focused_fid()
        if fid:
            self.lm.move_to_workspace(fid, id)

    def move_frame_next_workspace(self):
        if self.lm.workspace < self.lm.max_workspaces:
            self.move_frame_workspace(self.lm.workspace + 1)

    def move_frame_prev_workspace(self):
        if self.lm.workspace != 0:
            self.move_frame_workspace(self.lm.workspace - 1)

    def set_layout(self, id):
        self.lm.set_layout(id)

    def button_press(self, event):
        fid = self.get_focused_fid()
        if fid and not self.drag and event.state == ModMask._1 \
                and self.conn.is_inside(fid, event.event_x, event.event_y):
            for i in [ButtonIndex._1, ButtonIndex._3]:
                if event.detail == i:
                    self.drag = i
                    self.drag_frame = fid
                    self.start_x = event.event_x
                    self.start_y = event.event_y
                    self.corner = self.conn.get_corner(fid, self.start_x,
                                                       self.start_y)

    def button_motion(self, event):
        if self.drag:
            self.change_x += event.event_x - self.start_x
            self.change_y += event.event_y - self.start_y

            x = 0
            y = 0
            if self.change_x >= self.min_change:
                x += self.min_change
                self.change_x -= self.min_change
            elif self.change_x <= -self.min_change:
                x -= self.min_change
                self.change_x += self.min_change
            if self.change_y >= self.min_change:
                y += self.min_change
                self.change_y -= self.min_change
            elif self.change_y <= -self.min_change:
                y -= self.min_change
                self.change_y += self.min_change

            self.start_x = event.event_x
            self.start_y = event.event_y

            if x or y:
                if self.drag == ButtonIndex._1:
                    self.lm.move(self.drag_frame, x, y)
                elif self.drag == ButtonIndex._3:
                    self.lm.resize(self.drag_frame, x, y, self.corner)

                if not self.grid:
                    self.decorations.show_grid()
                    self.grid = True

                    for fid in self.lm.history:
                        self.conn.configure_window(fid, border=3)
                        self.conn.set_border_color_white(fid)

    def button_release(self, event):
        if self.drag == event.detail:
            self.drag = 0
            self.drag_frame = None
            self.start_x = None
            self.start_y = None
            self.change_x = 0
            self.change_y = 0
            self.corner = ""

            for fid in self.lm.history:
                self.conn.configure_window(fid, border=0)

            self.decorations.hide_grid()
            self.grid = False

    def enter_window(self, event):
        fid1 = self.drag_frame
        fid2 = event.child
        if not self.lm.frame_exists(fid2):
            fid2 = self.lm.get_fid(fid2)

        if fid1 and fid2 and self.drag == ButtonIndex._1 and fid1 != fid2:
            self.lm.switch(fid1, fid2)

        if self.drag == ButtonIndex._1 and not fid2:
            pointer = self.conn.conn.core.QueryPointer(fid1).reply()
            for fid in self.lm.history:
                if self.conn.is_inside(fid, pointer.root_x, pointer.root_y):
                    self.lm.switch(fid1, fid)
                    break

    def resize_frame(self, x, y):
        self.lm.resize(self.get_focused_fid(), x, -y, "SE")

    def move_frame(self, x, y):
        self.lm.move(self.get_focused_fid(), x, -y)
