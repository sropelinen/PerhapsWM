
class Layout:

    def __init__(self, max_workspaces, root_width, root_height):
        self.gap = 25
        self.min_width = 100
        self.min_height = 100
        self.root_width = root_width
        self.root_height = root_height
        self.order = {i: [] for i in range(max_workspaces)}
        self.sizes = {i: [] for i in range(max_workspaces)}

    def append_frame(self, workspace, fid, geometry):
        if len(self.sizes[workspace]) == 0:
            size = self.root_height - 2 * self.gap - \
                (self.root_width - self.gap * 3) / 2
            self.sizes[workspace].append(size)
        else:
            h = (self.root_height - (len(self.sizes[workspace]) + 1)
                 * self.gap) / len(self.sizes[workspace])
            if h < self.min_height:
                print("Max windows reached")
            if len(self.sizes[workspace]) > 1:
                h2 = (self.root_height - len(self.sizes[workspace])
                      * self.gap) / (len(self.sizes[workspace]) - 1)
                for i in range(1, len(self.sizes[workspace])):
                    self.sizes[workspace][i] *= h / h2
            self.sizes[workspace].append(h)
            self.fix_min(workspace, 1, len(self.sizes[workspace]))
        self.order[workspace].append(fid)

    def fix_min(self, workspace, f, n):
        rdy = False
        too_small = []
        while not rdy:
            w = 0
            for i in range(f, n):
                if self.sizes[workspace][i] < self.min_height:
                    w += self.min_height - self.sizes[workspace][i]
                    self.sizes[workspace][i] = self.min_height
                    too_small.append(i)
            if not w:
                rdy = True
            else:
                good = [x for x in range(f, n) if x not in too_small]
                for i in good:
                    self.sizes[workspace][i] -= w / len(good)

    def change_workspace(self, ws1, ws2, fid):
        self.order[ws2].append(fid)
        self.order[ws1].remove(fid)

    def remove_frame(self, workspace, fid):
        self.order[workspace].remove(fid)
        del self.sizes[workspace][-1]
        if len(self.sizes[workspace]) > 1:
            h = (self.root_height - (len(self.sizes[workspace]) + 1)
                 * self.gap) / len(self.sizes[workspace])
            h2 = (self.root_height - len(self.sizes[workspace])
                  * self.gap) / (len(self.sizes[workspace]) - 1)
            for i in range(1, len(self.sizes[workspace])):
                self.sizes[workspace][i] *= h2 / h

    def get_position(self, workspace, fid):
        if fid in self.order[workspace]:
            return self.order[workspace].index(fid)
        else:
            return 0

    def set_position(self, workspace, fid, position):
        self.order[workspace].remove(fid)
        self.order[workspace].insert(position, fid)

    def get_nth_fid(self, workspace, n):
        if n < len(self.order[workspace]):
            return self.order[workspace][n]
        else:
            return 0

    def move_frame(self, workspace, fid, x, y):
        pass

    def set_size(self, workspace, fid, width, height):
        pass

    def resize_frame(self, workspace, fid, x, y, corner):
        if len(self.order[workspace]) > 1 and fid in self.order[workspace]:
            i = self.order[workspace].index(fid)
            if i:
                if corner[0] == "N" and i > 1:
                    self.sizes[workspace][i] -= y
                    for j in range(1, i):
                        self.sizes[workspace][j] += y / (i - 1)
                    self.fix_min(workspace, 1, i + 1)
                elif corner[0] == "S" and i < len(self.sizes[workspace]) - 1:
                    self.sizes[workspace][i] += y
                    for j in range(i + 1, len(self.sizes[workspace])):
                        self.sizes[workspace][j] -= y \
                                / (len(self.sizes[workspace]) - i - 1)
                    self.fix_min(workspace, i, len(self.sizes[workspace]))

            self.sizes[workspace][0] += x

            if self.sizes[workspace][0] > (self.root_width / 2 - self.gap
                                           - self.min_width):
                self.sizes[workspace][0] = (self.root_width / 2 - self.gap
                                            - self.min_width)
            elif self.sizes[workspace][0] < -(self.root_width / 2 - self.gap
                                              - self.min_width):
                self.sizes[workspace][0] = -(self.root_width / 2 - self.gap
                                             - self.min_width)

    def switch_frame(self, workspace, fid1, fid2):
        i = self.order[workspace].index(fid1)
        self.order[workspace][self.order[workspace].index(fid2)] = fid1
        self.order[workspace][i] = fid2

    def get_dimensions(self, workspace):
        x = {}
        y = {}
        width = {}
        height = {}

        if len(self.order[workspace]) == 1:
            o = self.order[workspace][0]
            x[o] = self.gap
            y[o] = self.gap
            width[o] = self.root_width - 2 * self.gap
            height[o] = self.root_height - 2 * self.gap
        elif len(self.order[workspace]) > 1:
            o = self.order[workspace][0]
            x[o] = self.gap
            y[o] = self.gap
            width[o] = int(self.root_width / 2 - 1.5 * self.gap
                           + self.sizes[workspace][0])
            height[o] = int(self.root_height - 2 * self.gap)

            h = 0
            for i in range(1, len(self.order[workspace])):
                oi = self.order[workspace][i]
                x[oi] = int(self.root_width / 2 + 0.5 * self.gap
                            + self.sizes[workspace][0])
                y[oi] = int(h + self.gap)
                width[oi] = int(self.root_width / 2 - self.sizes[workspace][0]
                                - 1.5 * self.gap)
                height[oi] = int(self.sizes[workspace][i])
                h += self.gap + height[oi]

            err = self.root_height - self.gap - h
            if err:
                height[self.order[workspace][-1]] += err

        return x, y, width, height
