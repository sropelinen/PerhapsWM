
class Layout:

    def __init__(self, max_workspaces, root_width, root_height):
        self.root_width = root_width
        self.root_height = root_height
        self.order = {i: [] for i in range(max_workspaces)}

    def append_frame(self, workspace, fid, geometry):
        self.order[workspace].append(fid)

    def change_workspace(self, ws1, ws2, fid):
        self.order[ws2].append(fid)
        self.order[ws1].remove(fid)

    def remove_frame(self, workspace, fid):
        self.order[workspace].remove(fid)

    def get_position(self, workspace, fid):
        if fid in self.order[workspace]:
            return self.order[workspace].index(fid)
        else:
            return 0

    def set_position(self, workspace, fid, position):
        pass

    def get_nth_fid(self, workspace, n):
        if n < len(self.order[workspace]):
            return self.order[workspace][n]
        else:
            return

    def move_frame(self, workspace, fid, x, y):
        pass

    def set_size(self, workspace, fid, width, height):
        pass

    def resize_frame(self, workspace, fid, x, y, corner):
        pass

    def switch_frame(self, workspace, fid1, fid2):
        pass

    def get_dimensions(self, workspace):
        x = {}
        y = {}
        width = {}
        height = {}

        for fid in self.order[workspace]:
            x[fid] = 0
            y[fid] = 0
            width[fid] = self.root_width
            height[fid] = self.root_height

        return x, y, width, height
