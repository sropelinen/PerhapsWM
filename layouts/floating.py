
class Layout:

    def __init__(self, max_workspaces, root_width, root_height):
        self.root_width = root_width
        self.root_height = root_height

        self.x = [{} for _ in range(max_workspaces)]
        self.y = [{} for _ in range(max_workspaces)]
        self.width = [{} for _ in range(max_workspaces)]
        self.height = [{} for _ in range(max_workspaces)]

        self.min_width = 100
        self.min_height = 60

    def append_frame(self, workspace, fid, geometry):
        if geometry[0]:
            width = geometry[0]
        else:
            width = 800

        self.width[workspace][fid] = width
        if geometry[1]:
            height = geometry[1] + 34
        else:
            height = 500
        self.height[workspace][fid] = height

        self.x[workspace][fid] = (self.root_width - width) // 2 + 25 \
            * len(self.x[workspace]) - 15
        self.y[workspace][fid] = (self.root_height - height) // 2 + 25 \
            * len(self.y[workspace])

    def change_workspace(self, ws1, ws2, fid):
        for i in [self.x, self.y, self.width, self.height]:
            i[ws2][fid] = i[ws1][fid]
            del i[ws1][fid]

    def remove_frame(self, workspace, fid):
        del self.x[workspace][fid]
        del self.y[workspace][fid]
        del self.width[workspace][fid]
        del self.height[workspace][fid]

    def get_position(self, workspace, fid):
        return 0

    def set_position(self, workspace, fid, position):
        pass

    def get_nth_fid(self, workspace, n):
        return 0

    def move_frame(self, workspace, fid, x, y):
        self.x[workspace][fid] += x
        self.y[workspace][fid] += y

    def set_size(self, workspace, fid, width, height):
        if width >= self.min_width:
            self.width[workspace][fid] = width
        if height >= self.min_height:
            self.height[workspace][fid] = height

    def resize_frame(self, workspace, fid, x, y, corner):
        if corner[0] == "N":
            if self.height[workspace][fid] - y >= self.min_height:
                self.y[workspace][fid] += y
            y = -y
        if corner[1] == "W":
            if self.width[workspace][fid] - x >= self.min_width:
                self.x[workspace][fid] += x
            x = -x

        self.width[workspace][fid] += x
        self.height[workspace][fid] += y

        if self.width[workspace][fid] < self.min_width:
            self.width[workspace][fid] = self.min_width
        if self.height[workspace][fid] < self.min_height:
            self.height[workspace][fid] = self.min_height

    def switch_frame(self, workspace, fid1, fid2):
        pass

    def get_dimensions(self, workspace):
        x = {}
        y = {}
        width = {}
        height = {}

        for fid in self.x[workspace]:
            x[fid] = self.x[workspace][fid]
            y[fid] = self.y[workspace][fid]
            width[fid] = self.width[workspace][fid]
            height[fid] = self.height[workspace][fid]

        return x, y, width, height
