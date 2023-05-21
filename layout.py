
from xcffib.xproto import ConfigWindow


class Frame:
    def __init__(self, fid):
        self.fid = fid
        self.history = []
        self.decorations = True


class LayoutManager:

    def __init__(self, connection, layouts, root_width, root_height):
        self.conn = connection

        self.frames_fid = {}
        self.frames_wid = {}

        self.history = []
        self.max_workspaces = 3
        self.workspace = 0
        self.frame = 0
        self.workspaces = [[] for _ in range(self.max_workspaces)]

        self.layouts = []
        for layout in layouts:
            self.layouts.append(layout.Layout(self.max_workspaces, root_width,
                                              root_height))
        self.layout = [0] * len(self.layouts)

        self.root_width = root_width
        self.root_height = root_height

    def append_client(self, fid, wid):
        frame = self.frames_fid[fid]
        frame.history.append(wid)
        self.frames_wid[wid] = frame
        self.update_layout()

    def remove_client(self, fid, wid):
        self.frames_fid[fid].history.remove(wid)
        del self.frames_wid[wid]

    def client_exists(self, wid):
        if wid in self.frames_wid \
                and self.frames_wid[wid].fid in self.history:
            return True
        return False

    def get_fids(self):
        fids = []
        for fid in self.frames_fid:
            fids.append(fid)
        return fids

    def get_fid(self, wid):
        if wid in self.frames_wid:
            return self.frames_wid[wid].fid
        else:
            return 0

    def append_frame(self, fid, wid):
        self.frames_fid[fid] = Frame(fid)
        self.history.append(fid)

        w, h = self.conn.get_size(wid)
        for layout in self.layouts:
            layout.append_frame(self.workspace, fid, (w, h))

    def remove_frame(self, fid):
        if fid in self.frames_fid:
            del self.frames_fid[fid]
            self.history.remove(fid)
            for layout in self.layouts:
                layout.remove_frame(self.workspace, fid)
            self.update_layout()

    def get_frame(self, id):
        if id in self.frames_fid and id in self.history:
            return self.frames_fid[id]
        elif id in self.frames_wid:
            frame = self.frames_wid[id]
            if frame.fid in self.history:
                return frame
        return None

    def get_n_frames(self):
        return len(self.history)

    def frame_exists(self, fid):
        return fid in self.history

    def get_next_frame(self):
        if self.frame + 1 >= self.get_n_frames():
            self.frame = 0
        else:
            self.frame += 1
        fid = self.layouts[self.layout[self.workspace]].get_nth_fid(
                self.workspace, self.frame)
        if fid != 0:
            return self.frames_fid[fid]
        else:
            return None

    def get_prev_frame(self):
        if self.frame - 1 < 0:
            self.frame = self.get_n_frames() - 1
        else:
            self.frame -= 1
        fid = self.layouts[self.layout[self.workspace]].get_nth_fid(
                self.workspace, self.frame)
        if fid != 0:
            return self.frames_fid[fid]
        else:
            return None

    def get_position(self, fid):
        return self.layouts[self.layout[self.workspace]].get_position(
                self.workspace, fid)

    def set_position(self, fid, position):
        self.layouts[self.layout[self.workspace]].set_position(
                self.workspace, fid, position)
        self.update_layout()

    def set_size(self, fid, width, height):
        self.layouts[self.layout[self.workspace]].set_size(
                self.workspace, fid, width, height)
        self.update_layout()

    def resize_frame(self, fid, x, y):
        self.layouts[self.layout[self.workspace]].resize_frame(
                self.workspace, fid, x, y)
        self.update_layout()

    def set_focused_frame(self, fid):
        self.history.append(self.history.pop(self.history.index(fid)))
        self.frame = self.layouts[self.layout[self.workspace]] \
            .get_position(self.workspace, fid)

    def get_dimensions(self, wid):
        x, y, width, height = self.layouts[self.layout[self.workspace]] \
                .get_dimensions(self.workspace)
        fid = self.frames_wid[wid].fid
        if self.frames_fid[fid].decorations:
            height[fid] -= 34
            y[fid] += 34
        return x[fid], y[fid], width[fid], height[fid]

    def set_layout(self, id):
        if id >= 0 and id < len(self.layouts):
            self.layout[self.workspace] = id
            self.update_layout()

    def update_layout(self):
        x, y, width, height = self.layouts[self.layout[self.workspace]] \
                .get_dimensions(self.workspace)
        for fid in self.history:
            self.conn.configure_window(
                fid, x=x[fid], y=y[fid], width=width[fid], height=height[fid]
            )

            cy = 0
            if self.frames_fid[fid].decorations:
                height[fid] -= 34
                cy = 34

            for wid in self.frames_fid[fid].history:
                self.conn.configure_window(
                    wid, x=0, y=cy, width=width[fid], height=height[fid]
                )
                if self.get_frame(fid).decorations:
                    self.conn.update_corners(wid, 0, 10)
                else:
                    self.conn.update_corners(wid, 10, 10)

    def set_workspace(self, id):
        if id < self.max_workspaces and id != self.workspace:
            for fid in self.history:
                self.conn.unmap_window(fid)

            self.workspaces[self.workspace] = self.history
            self.workspace = id
            self.history = self.workspaces[id]

            for fid in self.history:
                self.conn.map_window(fid)

            if len(self.history):
                frame = self.get_frame(self.history[-1])
                if len(frame.history):
                    self.conn.set_input_focus(frame.history[-1])

            self.update_layout()

    def move_to_workspace(self, fid, id):
        if id < self.max_workspaces and id != self.workspace:
            self.workspaces[id].append(fid)
            self.history.remove(fid)
            self.conn.unmap_window(fid)
            for layout in self.layouts:
                layout.change_workspace(self.workspace, id, fid)
            self.update_layout()

    def move(self, fid, x, y):
        self.layouts[self.layout[self.workspace]].move_frame(
                self.workspace, fid, x, y)
        self.update_layout()

    def resize(self, fid, x, y, corner):
        self.layouts[self.layout[self.workspace]].resize_frame(
                self.workspace, fid, x, y, corner)
        self.update_layout()

    def switch(self, fid1, fid2):
        self.layouts[self.layout[self.workspace]].switch_frame(
                self.workspace, fid1, fid2)
        self.update_layout()
