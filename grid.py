
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GdkPixbuf

from PIL import Image, ImageDraw


class Grid(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self)

        self.set_role("grid")
        self.set_name("grid")

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual is not None and screen.is_composited():
            self.set_visual(visual)

        cp = Gtk.CssProvider()
        cp.load_from_data(str.encode(
            "#grid{background:transparent}"
            "#grid image{opacity:1;transition:opacity .5s}"
            "#grid #hidden{opacity:0}"
        ))
        Gtk.StyleContext().add_provider_for_screen(
            Gdk.Screen.get_default(), cp,
            Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

        self.screen_width = 1600
        self.screen_height = 900
        self.gap_top = 25
        self.gap_bottom = 25
        self.gap_right = 25
        self.gap_left = 25
        self.size = 25
        self.c1 = (255, 255, 255, 191)
        self.c2 = (255, 255, 255, 127)

        im = self.draw_image()
        self.image = Gtk.Image.new_from_pixbuf(self.image_to_pixbuf(im))
        self.image.set_name("hidden")
        self.add(self.image)
        self.show_all()

    def show_image(self, show):
        self.image.set_name("" if show else "hidden")

    def image_to_pixbuf(self, image):
        data = image.tobytes()
        size = image.size
        return GdkPixbuf.Pixbuf.new_from_data(
            data, GdkPixbuf.Colorspace.RGB, True, 8,
            size[0], size[1], 4 * size[0]
        )

    def draw_image(self):
        image = Image.new("RGBA", (self.screen_width, self.screen_height),
                          (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        y_offset = int(((self.screen_height - self.gap_top - self.gap_bottom)
                       % self.size) / 2 + self.gap_top)
        x_offset = int(((self.screen_width - self.gap_left - self.gap_right)
                       % self.size) / 2 + self.gap_left)

        for y in range(y_offset % self.size, self.screen_height, self.size):
            draw.line((0, y, self.screen_width, y), fill=self.c2)
        for x in range(x_offset % self.size, self.screen_width, self.size):
            draw.line((x, 0, x, self.screen_height), fill=self.c2)

        for y in range(y_offset, self.screen_height - self.gap_bottom,
                       self.size * 2):
            draw.line((self.gap_left, y, self.screen_width - self.gap_right,
                       y), fill=self.c2)
        for y in range(y_offset + self.size,
                       self.screen_height - self.gap_bottom, self.size * 2):
            draw.line((self.gap_left, y, self.screen_width - self.gap_right,
                       y), fill=self.c1)
        for x in range(x_offset, self.screen_width - self.gap_bottom,
                       self.size * 2):
            draw.line((x, self.gap_top, x,
                       self.screen_height - self.gap_right), fill=self.c2)
        for x in range(x_offset + self.size,
                       self.screen_width - self.gap_bottom, self.size * 2):
            draw.line((x, self.gap_top, x,
                       self.screen_height - self.gap_right), fill=self.c1)

        draw.line((0, self.gap_top, self.screen_width, self.gap_top), width=3,
                  fill=self.c1)
        draw.line((0, self.screen_height - self.gap_bottom, self.screen_width,
                   self.screen_height - self.gap_bottom), width=3,
                  fill=self.c1)
        draw.line((self.gap_left, 0, self.gap_left, self.screen_height),
                  width=3, fill=self.c1)
        draw.line((self.screen_width - self.gap_right, 0,
                   self.screen_width - self.gap_right, self.screen_height),
                  width=3, fill=self.c1)

        return image
