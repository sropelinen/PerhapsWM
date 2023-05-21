
from xcffib.xproto import ModMask


def parse_keybinds(conn, wm, keybinds):
    mod_masks = {
        "": ModMask.Any,
        "Shift": ModMask.Shift,
        "Ctrl": ModMask.Control,
        "Mod1": ModMask._1,
        "Mod2": ModMask._2,
        "Mod3": ModMask._3,
        "Mod4": ModMask._4,
        "Mod5": ModMask._5
    }

    kb = {}
    for string in keybinds:
        split = string.replace(" ", "").split("+")
        if split[-1].startswith("!") and split[-1][1:].isdigit():
            keycode = int(split[-1][1:])
        else:
            keycode = conn.string_to_keycode(split[-1])

        modifiers = 0
        for mod in split[:-1]:
            modifiers |= mod_masks[mod]

        command = keybinds[string]
        command.insert(1, wm)

        if keycode not in kb:
            kb[keycode] = {}
        kb[keycode][modifiers] = command

        conn.grab_key(conn.root, keycode, modifiers)

    return kb
