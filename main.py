#!/bin/env python3

from layouts import tiled, fullscreen, floating
from wm import WindowManager
from events import EventHandler

layouts = [tiled, fullscreen, floating]

keybinds = {
    "Mod1 + Return": [WindowManager.execute, "termite"],
    "Mod1 + e": [WindowManager.execute, "thunar"],
    "Mod1 + d": [WindowManager.execute, "dmenu_run"],
    "Mod1 + w": [WindowManager.destroy],
    "Shift + Mod1 + w": [WindowManager.destroy_frame],
    "Mod1 + Tab": [WindowManager.next_frame],
    "Shift + Mod1 + Tab": [WindowManager.prev_frame],
    "Mod1 + !49": [WindowManager.next_tab],
    "Shift + Mod1 + !49": [WindowManager.prev_tab],
    "Ctrl + Mod1 + Right": [WindowManager.move_frame_next],
    "Ctrl + Mod1 + Left": [WindowManager.move_frame_prev],
    "Mod1 + Right": [WindowManager.move_tab_next],
    "Mod1 + Left": [WindowManager.move_tab_prev],
    "Shift + Mod1 + Right": [WindowManager.move_tab_next_frame],
    "Shift + Mod1 + Left": [WindowManager.move_tab_prev_frame],
    "Mod1 + Down": [WindowManager.detach_tab],
    "Mod1 + g": [WindowManager.toggle_decorations],
    "Mod1 + t": [WindowManager.toggle_next_tab],
    "Mod1 + 1": [WindowManager.set_workspace, 0],
    "Mod1 + 2": [WindowManager.set_workspace, 1],
    "Mod1 + 3": [WindowManager.set_workspace, 2],
    "Mod1 + 9": [WindowManager.prev_workspace],
    "Mod1 + 0": [WindowManager.next_workspace],
    "Shift + Mod1 + 1": [WindowManager.move_frame_workspace, 0],
    "Shift + Mod1 + 2": [WindowManager.move_frame_workspace, 1],
    "Shift + Mod1 + 3": [WindowManager.move_frame_workspace, 2],
    "Shift + Mod1 + 9": [WindowManager.move_frame_prev_workspace],
    "Shift + Mod1 + 0": [WindowManager.move_frame_next_workspace],
    "Mod1 + i": [WindowManager.set_layout, 0],
    "Mod1 + o": [WindowManager.set_layout, 1],
    "Mod1 + p": [WindowManager.set_layout, 2],
    "Ctrl + Shift + Mod1 + Right": [WindowManager.resize_frame, 25, 0],
    "Ctrl + Shift + Mod1 + Left": [WindowManager.resize_frame, -25, 0],
    "Ctrl + Shift + Mod1 + Up": [WindowManager.resize_frame, 0, 25],
    "Ctrl + Shift + Mod1 + Down": [WindowManager.resize_frame, 0, -25],
}

EventHandler(layouts, keybinds).run()
