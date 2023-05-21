#!/bin/env python3

import os
import subprocess
import sys
import fcntl
import select

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Pango, Gdk

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop

import grid


RDY_MSG = "READY"


class DBusService(dbus.service.Object):

    def __init__(self, application):
        name = dbus.service.BusName("org.wm.Frames", bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, name, "/org/wm/Frames")

        self.application = application
        self.frames = {}
        self.cp = Gtk.CssProvider()
        self.colors = {}
        self.dark = {}
        self.grid = grid.Grid()

        self.path = os.path.dirname(os.path.realpath(__file__))
        with open(self.path + "/color_list.txt") as f:
            lines = f.read().split("\n")

        self.color_list = {}
        for line in lines:
            p = line.replace(" ", "").split("=")
            self.color_list[p[0]] = tuple(map(int, p[1].split(",")))

        self.terminals = ["termite", "xterm", "urxvt"]

    @dbus.service.method("org.wm.Frames")
    def append_frame(self):
        frame = Frame()
        self.application.add_window(frame)
        frame.show_all()
        fid = frame.get_window().get_xid()
        self.frames[fid] = frame
        return fid

    @dbus.service.method("org.wm.Frames")
    def remove_frame(self, fid):
        self.frames[fid].close()

    @dbus.service.method("org.wm.Frames")
    def send_fid(self, fid):
        self.frames[fid] = self.frames[0]
        del self.frames[0]

    @dbus.service.method("org.wm.Frames")
    def append_tab(self, fid, wid, name, classes):
        frame = self.frames[fid]
        if wid not in frame.labels:
            icon_name = self.get_icon_name(classes, name)
            icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.MENU)
            icon.set_name("icon")

            label = Gtk.Label()
            label.set_text(name)
            label.set_xalign(0)
            label.set_max_width_chars(0)
            label.set_ellipsize(Pango.EllipsizeMode.END)

            close_button = Gtk.Button()
            close_button.connect("clicked", self.close_button_clicked, wid)

            close_box = Gtk.Box()
            close_box.pack_end(close_button, False, False, 0)

            box = Gtk.Box()
            box.pack_start(label, True, True, 0)
            box.pack_end(close_box, False, False, 0)
            box.set_name("inner")

            event_box = Gtk.EventBox()
            event_box.connect("button-press-event", self.tab_pressed, wid)
            event_box.connect("enter-notify-event", self.tab_hover)
            event_box.connect("leave-notify-event", self.tab_hover_off)

            tab = Gtk.Box()
            tab.pack_start(icon, False, False, 0)
            tab.pack_end(box, True, True, 0)
            tab.set_name(str(wid))
            tab.show_all()
            event_box.add(tab)

            window = Gtk.Box()
            frame.notebook.append_page(window, event_box)
            frame.notebook.set_tab_detachable(window, True)
            frame.notebook.set_tab_reorderable(window, True)
            frame.notebook.set_group_name("wm_frame")
            frame.append_tab(wid, window, tab, label, icon)

            classlist = ",".join(classes)
            if classlist in self.color_list:
                self.add_color(fid, wid, classlist, self.color_list[classlist])

            frame.set_title("wm_frame_{}".format(wid))
            frame.show_all()
            frame.notebook.set_current_page(frame.notebook.page_num(window))

    def tab_hover(self, box, ec):
        box.set_name("hover")

    def tab_hover_off(self, box, ec):
        if ec.detail != Gdk.NotifyType.INFERIOR:
            box.set_name("")

    def tab_pressed(self, sender, event, wid):
        if event.button == 2:
            frame = None
            for fid in self.frames:
                if wid in self.frames[fid].labels:
                    frame = self.frames[fid]
                    break

            if frame:
                frame.iconify()
                frame.notebook.remove_page(
                        frame.notebook.page_num(frame.windows[wid]))
                frame.remove_tab(wid)

    def close_button_clicked(self, sender, wid):
        frame = None
        for fid in self.frames:
            if wid in self.frames[fid].labels:
                frame = self.frames[fid]
                break

        if frame:
            frame.iconify()
            frame.notebook.remove_page(
                    frame.notebook.page_num(frame.windows[wid]))
            frame.remove_tab(wid)

    @dbus.service.method("org.wm.Frames")
    def toggle_decorations(self, fid):
        frame = self.frames[fid]
        if frame.fullscreen:
            frame.notebook.show()
            frame.fullscreen = False
        else:
            frame.notebook.hide()
            frame.fullscreen = True

    @dbus.service.method("org.wm.Frames")
    def remove_tab(self, fid, wid):
        frame = self.frames[fid]
        if wid in frame.labels:
            frame.notebook.remove_page(
                    frame.notebook.page_num(frame.windows[wid]))
            frame.remove_tab(wid)

    @dbus.service.method("org.wm.Frames")
    def set_tab_name(self, fid, wid, name):
        if wid in self.frames[fid].labels:
            self.frames[fid].labels[wid].set_text(name)

    @dbus.service.method("org.wm.Frames")
    def set_tab_icon(self, fid, wid, classes, name):
        icon = self.frames[fid].icons[wid]
        size = Gtk.IconSize.MENU
        icon_name = self.get_icon_name(classes, name)
        icon.set_from_icon_name(icon_name, size)

    def get_icon_name(self, classes, name):
        for c in classes:
            if c in self.terminals:
                title = name.split(" ")[0]
                if Gtk.IconTheme.get_default().has_icon(title):
                    return title
                else:
                    return "utilities-terminal"

        for c in classes:
            if Gtk.IconTheme.get_default().has_icon(c):
                return c

        return ""

    @dbus.service.method("org.wm.Frames")
    def set_tab_position(self, fid, wid, position):
        frame = self.frames[fid]
        if wid in frame.labels:
            n_pages = frame.notebook.get_n_pages()
            if position < n_pages:
                frame.notebook.reorder_child(frame.windows[wid], position)
            else:
                frame.notebook.reorder_child(frame.windows[wid], n_pages)

    @dbus.service.method("org.wm.Frames")
    def get_active_client(self, fid):
        if fid in self.frames:
            frame = self.frames[fid]
            active = frame.notebook.get_current_page()
            for wid in frame.windows:
                if frame.notebook.page_num(frame.windows[wid]) == active:
                    return wid
        return 0

    @dbus.service.method("org.wm.Frames")
    def change_tab_position_next(self, fid, wid):
        frame = self.frames[fid]
        if wid in frame.labels:
            pos = frame.notebook.page_num(frame.windows[wid])
            if pos == frame.notebook.get_n_pages() - 1:
                position = 0
            else:
                position = pos + 1
            frame.notebook.reorder_child(frame.windows[wid], position)

    @dbus.service.method("org.wm.Frames")
    def change_tab_position_prev(self, fid, wid):
        frame = self.frames[fid]
        if wid in frame.labels:
            pos = frame.notebook.page_num(frame.windows[wid])
            if pos == 0:
                position = frame.notebook.get_n_pages() - 1
            else:
                position = pos - 1
            frame.notebook.reorder_child(frame.windows[wid], position)

    @dbus.service.method("org.wm.Frames")
    def goto_tab(self, fid, wid):
        frame = self.frames[fid]
        if wid in frame.windows:
            frame.notebook.set_current_page(frame.notebook.page_num(
                    frame.windows[wid]))

    @dbus.service.method("org.wm.Frames")
    def next_tab(self, fid):
        frame = self.frames[fid]
        notebook = frame.notebook

        if notebook.get_current_page() == notebook.get_n_pages() - 1:
            notebook.set_current_page(0)
        else:
            notebook.next_page()

        for wid in frame.windows:
            if frame.windows[wid] == notebook.get_nth_page(
                    notebook.get_current_page()):
                return wid

        return 0

    @dbus.service.method("org.wm.Frames")
    def prev_tab(self, fid):
        frame = self.frames[fid]
        notebook = frame.notebook

        if notebook.get_current_page() == 0:
            notebook.set_current_page(notebook.get_n_pages() - 1)
        else:
            notebook.prev_page()

        for wid in frame.windows:
            if frame.windows[wid] == notebook.get_nth_page(
                    notebook.get_current_page()):
                return wid

        return 0

    @dbus.service.method("org.wm.Frames")
    def goto_tab_num(self, fid, n):
        frame = self.frames[fid]
        notebook = frame.notebook

        if n < notebook.get_n_pages():
            notebook.set_current_page(n)
            for wid in frame.windows:
                if frame.windows[wid] == notebook.get_nth_page(n):
                    return wid

        return 0

    @dbus.service.method("org.wm.Frames")
    def get_wids(self):
        self.check_changes()

        frames = {}
        for fid in self.frames:
            wids = []
            for wid in self.frames[fid].labels:
                wids.append(wid)
            if len(wids) > 0:
                frames[int(fid)] = wids
            else:
                frames[int(fid)] = [0]

        if len(frames) > 0:
            return frames
        else:
            return None

    def check_changes(self):
        missing = {}
        for fid in self.frames:
            notebook_windows = []
            for i in range(self.frames[fid].notebook.get_n_pages()):
                notebook_windows.append(self.frames[fid].notebook
                                        .get_nth_page(i))

            frame_windows = []
            for wid in self.frames[fid].windows:
                frame_windows.append(self.frames[fid].windows[wid])

            missing = [w for w in notebook_windows if w not in frame_windows]
            if len(missing) > 0:
                missing = missing[0]
                fid2 = 0
                for f2 in self.frames:
                    for w in self.frames[f2].windows:
                        if self.frames[f2].windows[w] == missing:
                            wid = w
                            fid2 = f2

                if fid2 != 0:
                    frame = self.frames[fid]
                    frame2 = self.frames[fid2]

                    frame.labels[wid] = frame2.labels[wid]
                    frame.windows[wid] = frame2.windows[wid]
                    frame.tabs[wid] = frame2.tabs[wid]
                    frame.icons[wid] = frame2.icons[wid]

                    del frame2.labels[wid]
                    del frame2.windows[wid]
                    del frame2.tabs[wid]
                    del frame2.icons[wid]

    @dbus.service.method("org.wm.Frames")
    def add_color(self, fid, wid, classlist, color):
        if classlist:
            classlist = classlist.replace(",", "")
            self.frames[fid].tabs[wid].set_name(classlist)
            wid = classlist

        if color in self.colors:
            if wid in self.colors[color]:
                return
        else:
            self.colors[color] = []

        self.colors[color].append(wid)
        if color not in self.dark:
            self.dark[color] = 0.2126 * color[0] + 0.7152 * color[1] \
                    + 0.0722 * color[2] > 128
        self.update_colors()

    @dbus.service.method("org.wm.Frames")
    def remove_color(self, wid):
        for c in self.colors:
            if wid in self.colors[c]:
                self.colors[c].remove(wid)
                if not self.colors[c]:
                    del self.colors[c]
                self.update_colors()
                break

    @dbus.service.method("org.wm.Frames")
    def update_colors(self):
        css = ""
        for c in self.colors:
            if self.dark[c]:
                text_color = "#333"
                button_color = "dark"
            else:
                text_color = "#DDD"
                button_color = "light"

            with open(self.path + "/color.txt") as f:
                text = f.read().split("|")

            selectors = text[:-1]
            css_color = text[-1].format(text_color, button_color,
                                        "{},{},{}".format(*c))

            for wid in self.colors[c]:
                css_color = css_color.replace(
                        "{", "{{{{").replace("}", "}}}}") \
                    .replace("{{{{", "{}{{{{").format(*selectors).format(wid)

            css += css_color.replace(",{", "{")

        self.cp.load_from_data(str.encode(css))
        Gtk.StyleContext().add_provider_for_screen(
            Gdk.Screen.get_default(), self.cp,
            Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

    @dbus.service.method("org.wm.Frames")
    def set_header_color(self, fid, focused):
        notebook = self.frames[fid].notebook
        if focused:
            notebook.set_name("focused")
        else:
            notebook.set_name("")

    @dbus.service.method("org.wm.Frames")
    def show_grid(self):
        self.grid.show_image(True)

    @dbus.service.method("org.wm.Frames")
    def hide_grid(self):
        self.grid.show_image(False)


class Frame(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self)

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)

        self.set_name("frame")

        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)
        self.notebook.set_name("")
        self.add(self.notebook)

        self.windows = {}
        self.tabs = {}
        self.labels = {}
        self.icons = {}

        self.fullscreen = False

    def append_tab(self, wid, window, tab, label, icon):
        self.windows[wid] = window
        self.tabs[wid] = tab
        self.labels[wid] = label
        self.icons[wid] = icon

    def remove_tab(self, wid):
        del self.windows[wid]
        del self.tabs[wid]
        del self.labels[wid]
        del self.icons[wid]


class Application(Gtk.Application):

    def __init__(self):
        Gtk.Application.__init__(self)

        self.connect("activate", self.activate)

        css_path = os.path.dirname(os.path.realpath(__file__)) + "/style.css"

        f = open(css_path, "rb")
        main_css = f.read()
        f.close()

        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(main_css)
        Gtk.StyleContext().add_provider_for_screen(
            Gdk.Screen.get_default(), style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

    def activate(self, data=None):
        self.hold()


def run():
    process = subprocess.Popen(["python3", __file__], stdout=subprocess.PIPE)
    fcntl.fcntl(
        process.stdout.fileno(), fcntl.F_SETFL,
        fcntl.fcntl(process.stdout.fileno(), fcntl.F_GETFL) | os.O_NONBLOCK
    )

    while not process.poll():
        if select.select([process.stdout.fileno()], [], [])[0]:
            if process.stdout.read().decode("UTF-8") == RDY_MSG:
                break


if __name__ == "__main__":
    os.environ["GTK_THEME"] = "Adwaita"

    application = Application()

    DBusGMainLoop(set_as_default=True)
    DBusService(application)

    sys.stdout.write(RDY_MSG)
    sys.stdout.flush()

    application.run(None)
