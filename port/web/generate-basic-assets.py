#!/usr/bin/env python3
"""Create original, deliberately plain terrain and UI for the two-map browser demo.

This is an explicit opt-in asset pack, not an engine fallback. Existing archives,
maps and non-generated loose files are never changed. Python standard library only.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parents[2]
GENERATED = ROOT / "games/warcraft-3/game/generated"
MANIFEST = "basic-assets-manifest.json"
ART = "UI\\BrowserBasic\\"
# The supplied archives retain localized CommandStrings but omit CommandFunc.
# Restore only art and command-card positions through the normal profile path.
COMMAND_PROFILES = {
    "CmdMove": ("move", 0, 0), "CmdStop": ("stop", 1, 0),
    "CmdHoldPos": ("hold", 2, 0), "CmdAttack": ("attack", 3, 0),
    "CmdPatrol": ("patrol", 0, 1), "CmdAttackGround": ("ground", 1, 1),
    "CmdSelectSkill": ("skill", 3, 1), "CmdRally": ("rally", 3, 1),
    "CmdCancel": ("cancel", 3, 2), "CmdCancelBuild": ("cancel", 3, 2),
    "CmdCancelTrain": ("cancel", 3, 2), "CmdCancelRevive": ("cancel", 3, 2),
    "CmdBuild": ("build", 0, 2), "CmdBuildHuman": ("build", 0, 2),
    "CmdBuildOrc": ("build", 0, 2), "CmdBuildNightElf": ("build", 0, 2),
    "CmdBuildUndead": ("build", 0, 2), "CmdPurchase": ("purchase", 3, 1),
}
# Runtime reports from both original maps confirmed these stock assets absent.
# Map imports keep precedence over these loose replacements in R_AssetCandidates.
MODELS = {
    "Objects/InventoryItems/OrcCaptureFlag/OrcCaptureFlag.mdx": "flag",
    "buildings/undead/Graveyard/Graveyard.mdx": "building",
    "buildings/undead/TombOfRelics/TombOfRelics.mdx": "building",
    "units/human/Militia/Militia.mdx": "unit",
    "units/undead/Ghoul/Ghoul.mdx": "unit",
    "Units/Other/TNTBarrel/TNTBarrel.mdx": "unit",
    "buildings/orc/SpiritLodge/SpiritLodge.mdx": "building",
    "buildings/other/Marketplace/Marketplace.mdx": "building",
    "units/human/Footman/Footman.mdx": "unit",
    "units/orc/SentryWard/SentryWard.mdx": "unit",
    "Doodads/Ruins/Plants/Ruins_Shrub/Ruins_Shrub.mdx": "shrub",
    "Doodads/LordaeronSummer/Plants/LillyPad/LillyPad.mdx": "lily",
    "Doodads/LordaeronSummer/Plants/RiverRushes/RiverRushes.mdx": "shrub",
}
MODELS.update({f"Doodads/Terrain/LordaeronTree/LordaeronTree{i}.mdx": "tree" for i in range(10)})
TEAM_COLORS = [(255, 3, 3), (0, 66, 255), (28, 230, 185), (84, 0, 129),
               (255, 252, 1), (254, 138, 14), (32, 192, 0), (229, 91, 176),
               (149, 150, 151), (126, 191, 241), (16, 98, 70), (78, 42, 4),
               (155, 0, 0), (0, 0, 195), (0, 234, 255), (190, 0, 254)]
TERRAIN = {
    "DalaranRuins/DRuins_Dirt": (108, 87, 67),
    "DalaranRuins/DRuins_DirtRough": (87, 70, 58),
    "DalaranRuins/DRuins_BlackMarble": (55, 61, 68),
    "DalaranRuins/DRuins_BrickTiles": (131, 95, 80),
    "DalaranRuins/DRuins_SquareTiles": (137, 139, 131),
    "DalaranRuins/DRuins_RoundTiles": (116, 128, 133),
    "DalaranRuins/DRuins_Grass": (70, 111, 60),
    "DalaranRuins/DRuins_GrassTrim": (57, 87, 51),
    "DalaranRuins/DRuins_WhiteMarble": (184, 185, 167),
    "LordaeronSummer/Lords_Dirt": (121, 93, 60),
    "LordaeronSummer/Lords_DirtRough": (95, 75, 49),
    "LordaeronSummer/Lords_DirtGrass": (107, 113, 57),
    "LordaeronSummer/Lords_Rock": (115, 119, 112),
    "LordaeronSummer/Lords_Grass": (86, 132, 57),
    "LordaeronSummer/Lords_GrassDark": (54, 94, 43),
    "Cityscape/City_WhiteMarble": (188, 189, 172),
}
# Only missing files are supplied. Existing SimpleInfoPanel, loading, options,
# alliance, localization, maps and archives continue to come from imported data.
SCREENS = {
    "Glue/MapListBox": "map_list_box",
    "UI/AllianceSlot": "alliance_slot",
    "UI/ChatDialog": "chat_dialog",
    "UI/CinematicPanel": "cinematic_panel",
    "UI/EscMenuMainPanel": "esc_menu_main_panel",
    "UI/EscMenuSaveGamePanel": "esc_menu_save_game_panel",
    "UI/GameResultDialog": "game_result_dialog",
    "UI/GameSaveSplashDialog": "game_save_splash_dialog",
    "UI/InfoPanelBuildingDetail": "info_panel_building_detail",
    "UI/InfoPanelItemDetail": "info_panel_item_detail",
    "UI/InfoPanelUnitDetail": "info_panel_unit_detail",
    "UI/LeaderBoard": "leader_board",
    "UI/LogDialog": "log_dialog",
    "UI/QuestDialog": "quest_dialog",
    "UI/SuspendDialog": "suspend_dialog",
    "UI/TimerDialog": "timer_dialog",
    "UI/UnresponsiveDialog": "unresponsive_dialog",
}


def blp(width, height, pixels):
    """Native renderer BLP2 encoding 3: one BGRA mip, with the full header."""
    data = bytes(channel for r, g, b, a in pixels for channel in (b, g, r, a))
    assert len(data) == width * height * 4
    return (struct.pack("<4sI4B2I", b"BLP2", 1, 3, 8, 0, 0, width, height) +
            struct.pack("<16I", 1172, *([0] * 15)) +
            struct.pack("<16I", len(data), *([0] * 15)) + bytes(1024) + data)


def terrain_pixels(color, cell=16):
    # SetTileUV/GetTile use bits 1,2,4,8 at the four corners of a 4x4
    # transition atlas. Cell 15 is the opaque base, cell 0 is transparent.
    for y in range(cell * 4):
        for x in range(cell * 4):
            mask = x // cell + (y // cell) * 4
            u, v = (x % cell) / (cell - 1), (y % cell) / (cell - 1)
            coverage = ((bool(mask & 1) * (1-u) + bool(mask & 2) * u) * (1-v) +
                        (bool(mask & 8) * (1-u) + bool(mask & 4) * u) * v)
            alpha = round(255 * max(0, min(1, (coverage - 0.35) / 0.3)))
            grain = ((x * 17 + y * 23 + (x * y) % 11) % 9) - 4
            yield (*(max(0, min(255, c + grain)) for c in color), alpha)


def primitive_model(building=False, kind=None):
    """Original simple meshes, using the native MDLX v800 contract."""
    pack = lambda fmt, *values: struct.pack("<" + fmt, *values)
    fixed = lambda value, count: value.encode().ljust(count, b"\0")
    chunk = lambda tag, data: tag.encode() + pack("I", len(data)) + data
    record = lambda data: pack("I", len(data) + 4) + data
    kind = kind or ("building" if building else "unit")
    radius, height = {"building": (64., 100.), "unit": (18., 48.), "tree": (36., 160.),
                      "shrub": (24., 36.), "lily": (24., 6.), "flag": (40., 110.)}[kind]
    bounds = pack("7f", max(radius * 2, height), -radius, -radius, 0, radius, radius, height)
    vertices = [(-radius, -radius, 0.), (radius, -radius, 0.), (radius, radius, 0.),
                (-radius, radius, 0.), (0., 0., height)]
    indices = (0, 1, 4, 1, 2, 4, 2, 3, 4, 3, 0, 4, 0, 3, 2, 0, 2, 1)
    if kind == "flag":
        # A solid pole and two-sided banner remain legible at the map's scale 3.
        vertices = [(-2., -2., 0.), (2., -2., 0.), (2., 2., 0.), (-2., 2., 0.),
                    (-2., -2., height), (2., -2., height), (2., 2., height), (-2., 2., height),
                    (0., 0., height), (radius, 0., height-6), (radius, 0., height-40), (0., 0., height-34)]
        indices = (0, 1, 5, 0, 5, 4, 1, 2, 6, 1, 6, 5, 2, 3, 7, 2, 7, 6,
                   3, 0, 4, 3, 4, 7, 0, 3, 2, 0, 2, 1, 4, 5, 6, 4, 6, 7, 8, 9, 10, 8, 10, 11)
    count = len(vertices)
    sequences = b""
    for i, name in enumerate(("Stand", "Walk", "Attack", "Birth", "Death", "Portrait", "Stand Work")):
        sequences += fixed(name, 80) + pack("2IfIfI", i*1000, i*1000+999, 0., int(name in ("Birth", "Death")), 0., 0) + bounds
    layer = record(pack("5If", 0, 0x11, 0, 0xffffffff, 0, 1.))  # opaque, two-sided, unshaded
    material = record(pack("2I", 0, 0) + b"LAYS" + pack("I", 1) + layer)
    arrays = (b"VRTX" + pack(f"I{count*3}f", count, *(v for xyz in vertices for v in xyz)) +
              b"NRMS" + pack(f"I{count*3}f", count, *([0., 0., 1.] * count)) +
              b"PTYP" + pack("2I", 1, 4) + b"PCNT" + pack("2I", 1, len(indices)) +
              b"PVTX" + pack(f"I{len(indices)}H", len(indices), *indices) +
              b"GNDX" + pack("I", count) + bytes(count) + b"MTGC" + pack("2I", 1, 1) +
              b"MATS" + pack("5I", 1, 0, 0, 0, 0) + bounds + pack("I", 0) +
              b"UVAS" + pack("I", 1) + b"UVBS" + pack(f"I{count*2}f", count, *(v for x, y, z in vertices for v in ((x/radius+1)/2, z/height))))
    scale = b""
    if kind == "tree":
        # Hold a flattened stump at Death's end; Birth restores the full tree.
        keys = [(i*1000+offset, (1., 1., .02 if i == 4 and offset else 1.))
                for i in range(7) for offset in (0, 999)]
        scale = b"KGSC" + pack("3I", len(keys), 1, 0xffffffff)
        scale += b"".join(pack("I3f", time, *value) for time, value in keys)
    bone = pack("I", 96+len(scale)) + fixed("BasicRoot", 80) + pack("3I", 0, 0xffffffff, 256) + scale + pack("2I", 0, 0xffffffff)
    texture = pack("I", 0) + fixed(ART + "tree.blp", 260) + pack("I", 0) if kind in ("tree", "shrub", "lily") else pack("I", 1) + bytes(260) + pack("I", 0)
    return (b"MDLX" + chunk("VERS", pack("I", 800)) +
            chunk("MODL", fixed("Original basic browser pyramid", 80) + bytes(260) + bounds + pack("I", 150)) +
            chunk("SEQS", sequences) + chunk("TEXS", texture) +
            chunk("MTLS", material) + chunk("GEOS", record(arrays)) + chunk("BONE", bone) + chunk("PIVT", bytes(12)))


def pathing_texture(width, height, no_fly=False):
    # One pixel = 32 world units. Magenta blocks walking and construction while
    # leaving the green (no-fly) channel clear. The native LoadTGA keeps BGRA
    # byte order, so symmetric red/blue also preserves that loader's contract.
    header = struct.pack("<3B2HB4H2B", 0, 0, 2, 0, 0, 0, 0, 0, width, height, 24, 0)
    return header + bytes((255, 255 if no_fly else 0, 255)) * (width * height)


def marker_pixels(color, glow=False):
    for y in range(64):
        for x in range(64):
            distance = math.hypot(x - 31.5, y - 31.5) / 31.5
            alpha = max(0, 1-distance) * .6 if glow else max(0, 1-abs(distance-.8)/.07)
            yield (*color, round(alpha * 255))


def command_pixels(symbol):
    """Original, legible geometric glyphs for ordinary command-card actions."""
    for y in range(32):
        for x in range(32):
            dx, dy = x - 15.5, y - 15.5
            if symbol == "move":
                glyph = (abs(x+y-31) <= 2 and 7 <= x <= 24 or
                         20 <= x <= 25 and 6 <= y <= 17 or
                         14 <= x <= 25 and 6 <= y <= 11)
            elif symbol == "stop":
                glyph = 8 <= x <= 23 and 8 <= y <= 23
            elif symbol == "hold":
                glyph = (8 <= x <= 12 or 19 <= x <= 23) and 7 <= y <= 24
            elif symbol == "attack":
                glyph = (abs(dx-dy) <= 1.5 or abs(dx+dy) <= 1.5) and abs(dx) <= 10
                glyph |= (abs(x-9) + abs(y-23) <= 4 or abs(x-22) + abs(y-23) <= 4)
            elif symbol == "patrol":
                glyph = (abs(y-10) <= 1 and 7 <= x <= 25 or
                         abs(y-21) <= 1 and 6 <= x <= 24 or
                         20 <= x <= 25 and abs(y-10) <= x-20 or
                         6 <= x <= 11 and abs(y-21) <= 11-x)
            elif symbol == "ground":
                glyph = (abs(math.hypot(dx, dy)-7) <= 1.3 or
                         abs(dx) <= 1 and abs(dy) <= 12 or abs(dy) <= 1 and abs(dx) <= 12)
            elif symbol == "skill":
                glyph = (abs(dx) <= 2 and abs(dy) <= 10 or abs(dy) <= 2 and abs(dx) <= 10)
            elif symbol == "cancel":
                glyph = (abs(dx-dy) <= 2 or abs(dx+dy) <= 2) and abs(dx) <= 9
            elif symbol == "rally":
                glyph = (7 <= x <= 9 and 5 <= y <= 26 or
                         9 <= x <= 24 and 6 <= y <= 16 and y <= 18-(x-9)//3 or
                         5 <= x <= 13 and 25 <= y <= 27)
            elif symbol == "build":
                glyph = (abs(dx)+abs(y-13) <= 11 and y <= 13 or
                         8 <= x <= 23 and 13 <= y <= 25 and not (13 <= x <= 18 and y >= 19))
            else:  # purchase: two coins
                glyph = (abs(math.hypot(x-12, y-12)-6) <= 2 or
                         abs(math.hypot(x-20, y-21)-6) <= 2)
            edge = min(x, y, 31-x, 31-y) < 2
            color = (229, 235, 213) if glyph else (82, 115, 131) if edge else (19, 31, 42)
            yield (*color, 255)


def icon_pixels(path):
    """Original item-category glyphs, with muted colors for disabled buttons."""
    name = Path(path).stem.lower().removeprefix("dis").removeprefix("btn")
    digest = hashlib.sha256(name.encode()).digest()
    tint = tuple(95 + channel % 135 for channel in digest[:3])
    disabled = "commandbuttonsdisabled/" in path.lower().replace("\\", "/")
    if disabled:
        gray = sum(tint) // 3
        tint = tuple((c + gray * 2) // 3 for c in tint)
    for y in range(32):
        for x in range(32):
            dx, dy = x-15.5, y-15.5
            if "ankh" in name:
                glyph = abs(math.hypot(dx, y-10)-4) < 1.5 or (abs(dx) < 1.5 and 13 <= y <= 26) or (abs(y-18) < 1.5 and abs(dx) <= 7)
            elif "armor" in name or "footman" in name:
                glyph = abs(dx) <= 8 and 7 <= y <= 17 or (17 < y <= 26 and abs(dx) <= 26-y)
            elif "helm" in name:
                glyph = dx*dx + (y-15)**2 <= 85 and y <= 20 or (9 <= x <= 22 and 20 <= y <= 24)
                glyph = glyph and not (12 <= y <= 16 and 10 <= x <= 21)
            elif "tower" in name:
                glyph = 10 <= x <= 21 and 12 <= y <= 25 or (7 <= x <= 24 and 8 <= y <= 12 and (x//3)%2 == 0) or (7 <= x <= 24 and y >= 25 and y <= 27)
            elif "orb" in name:
                glyph = dx*dx + dy*dy < 75
            elif "ring" in name:
                glyph = abs(math.hypot(dx, dy)-8) < 2 or (abs(dx) < 3 and 4 <= y <= 10)
            elif "tome" in name:
                glyph = 7 <= x <= 24 and 7 <= y <= 25 and (x in (7, 8, 15, 16, 23, 24) or y in (7, 8, 24, 25))
            elif "wand" in name:
                glyph = abs(x+y-31) < 2 and 7 <= x <= 24 or (x-24)**2 + (y-7)**2 < 12
            else:
                glyph = abs(dx)+abs(dy) < 10 and (x+y+digest[3]) % 5 < 3
            border = min(x, y, 31-x, 31-y) < 2
            color = tint if glyph else tuple(c//2 for c in tint) if border else tuple(c//7 for c in tint)
            yield (*color, 255)


def ui_pixels(path):
    """Small original geometric UI sprites; keep borders transparent inside."""
    if "commandbuttons" in path.lower() or "passivebuttons" in path.lower():
        yield from icon_pixels(path)
        return
    name = path.lower()
    color = ((210, 177, 69) if "gold" in name else (97, 160, 91) if "lumber" in name
             else (110, 181, 209) if any(t in name for t in ("hero", "supply", "fill")) else (67, 86, 104))
    for y in range(32):
        for x in range(32):
            edge = min(x, y, 31-x, 31-y) < 2
            if "black" in name or "campaign-fade" in name:
                yield (0, 0, 0, 255)
            elif any(t in name for t in ("border", "corners", "highlight")):
                yield (*color, 255 if edge else 0)
            elif any(t in name for t in ("minimap", "resource", "infocard")):
                shape = abs(x-15.5) + abs(y-15.5) < 12
                yield (*color, 255 if shape else 0)
            else:
                yield (*(max(0, c-15) if edge else c for c in color), 255)


def frame(name, kind="FRAME", props="", children=""):
    return f'Frame "{kind}" "{name}" {{\n{props}\n{children}\n}}\n'


def point(parent, x=0, y=0, corner="TOPLEFT"):
    return f'SetPoint {corner}, "{parent}", {corner}, {x:.5f}, {-y:.5f},'


def size(w, h):
    return f"Width {w:.5f}, Height {h:.5f},"


def backdrop(name, art="panel", props="SetAllPoints,"):
    return frame(name, "BACKDROP", props +
                 f' BackdropBackground "{ART}{art}.blp", BackdropBlendAll,')


def text(name, parent, value="", x=0, y=0, w=.28, h=.02, center=False, children=""):
    return frame(name, "TEXT", size(w, h) + " " + point(parent, x, y) +
                 f' FrameFont "MasterFont", 0.011, "", Text "{value}", ' +
                 'FontColor 0.94 0.96 0.98 1, FontJustificationV JUSTIFYMIDDLE, ' +
                 f'FontJustificationH {"JUSTIFYCENTER" if center else "JUSTIFYLEFT"},', children)


def button(name, parent=None, label=None, text_name=None, x=.025, y=.06, w=.24, h=.029):
    text_name = text_name or name + "Text"
    label = label if label is not None else caption(name)
    normal, pushed = name + "BasicNormal", name + "BasicPushed"
    props = size(w, h) + (" " + point(parent, x, y) if parent else "")
    props += (f' ButtonText "{text_name}", ControlBackdrop "{normal}", '
              f'ControlPushedBackdrop "{pushed}",')
    return frame(name, "GLUETEXTBUTTON", props,
                 backdrop(normal, "button") + backdrop(pushed, "pressed") +
                 text(text_name, name, label, w=w, h=h, center=True))


def caption(name):
    labels = {"Pause": "Pause", "Return": "Resume", "Previous": "Back",
              "EndGame": "Leave game", "Quit": "Leave game", "Exit": "Exit",
              "GameResultContinue": "Continue", "GameResultRestart": "Restart",
              "GameResultQuit": "Leave game", "QuestAccept": "Done", "LogOk": "Done",
              "WouldTheRealOptionsTitleTextPleaseStandUp": "Menu"}
    base = re.sub(r"(ButtonText|Button|Text|Value|Label)$", "", name)
    return labels.get(base, re.sub(r"(?<=[a-z])(?=[A-Z])", " ", base))


def binding_tree(stem):
    """Read the checked-in binding contract, retaining every named parent."""
    source = (GENERATED / (stem + ".h")).read_text()
    trees, nodes, current = [], {}, None
    for line in source.splitlines():
        root = re.search(r'BZ_FDF_BIND_ROOT(?:_OPTIONAL)?\(out, (\w+), "([^"]+)"\)', line)
        direct = re.search(r'out->(\w+) = bind_root;', line)
        if root or (direct and current is None):
            key, name = root.groups() if root else (direct[1], direct[1])
            current = {"name": name, "children": []}
            nodes[key] = current
            trees.append(current)
        switch = re.search(r'bind_root = out->(\w+);', line)
        if switch and switch[1] in nodes:
            current = nodes[switch[1]]
        child = re.search(r'BZ_FDF_BIND_CHILD(?:_OPTIONAL)?\(out, (\w+), (bind_root|out->\w+), "([^"]+)"\)', line)
        if child:
            key, parent, name = child.groups()
            node = {"name": name, "children": []}
            nodes[key] = node
            (current if parent == "bind_root" else nodes[parent[5:]])["children"].append(node)
    if not trees:
        raise ValueError("No binding roots in " + stem)
    return trees


def kind_for(name, children):
    if "Backdrop" in name or name == "ColorBorder": return "BACKDROP"
    if "ScrollBar" in name: return "SCROLLBAR"
    if "CheckBox" in name or "RadioButton" in name: return "GLUECHECKBOX"
    if name.endswith("Button"): return "GLUETEXTBUTTON"
    if name.endswith("EditBox"): return "EDITBOX"
    if name.endswith(("Bar", "Indicator")): return "SIMPLESTATUSBAR"
    if name.endswith("Portrait"): return "PORTRAIT"
    if name == "WouldTheRealOptionsTitleTextPleaseStandUp" or re.search(r'(Text|Title|Value|Label|Description|Area|Display)\d*$', name):
        return "TEXTAREA" if name.endswith(("Area", "Display")) else "TEXT"
    return "FRAME"


def render_tree(node, parent=None, index=0, compact=False):
    name, children = node["name"], node["children"]
    kind = kind_for(name, children) if parent else "FRAME"
    if not parent:
        w, h = (.18, .12) if name.startswith("InfoPanel") else (.34, .40)
        if name == "EscMenuMainPanel": h = .40
        if name in ("Leaderboard", "TimerDialog"): w, h = .23, .07
        if name == "AllianceSlot": w, h = .60, .027
        if name == "CinematicPanel": w, h = .80, .60
        props = size(w, h)
    elif kind == "BACKDROP":
        icon = re.match(r'IconBackdrop(\d)', name)
        props = (size(.016, .016) + " " + point(parent, .14, .028 + (int(icon[1])-1)*.018)) if icon else "SetAllPoints,"
    elif kind == "GLUETEXTBUTTON":
        return button(name, parent, text_name=children[0]["name"] if children else None,
                      x=.025, y=.06 + index * .035)
    elif kind in ("TEXT", "TEXTAREA"):
        if parent.endswith("Button"):
            props = "SetAllPoints,"
        elif compact:
            stat = re.match(r'(Defense|Attack|Speed|Range|BuildingDefense|BuildingSupply)(Label|Title|Value)(\d*)$', name)
            rows = {"Defense": 0, "Attack": 1, "Speed": 3, "Range": 4, "BuildingDefense": 0, "BuildingSupply": 1}
            if stat:
                row = rows[stat[1]] + (int(stat[3])-1 if stat[3] else 0)
                props = size(.055 if stat[2] != "Value" else .07, .013) + " " + point(parent, .06 if stat[2] == "Value" else .005, .026 + row * .014)
            else:
                props = size(.155, .016) + " " + point(parent, .005, .003 + min(index, 4) * .018)
        else:
            props = size(.155 if compact else .28, .016 if compact else .024) + " " + point(parent, .005 if compact else .025, .003 + index * (.018 if compact else .032))
        props += (' FrameFont "MasterFont", 0.011, "", FontColor 0.94 0.96 0.98 1, '
                  'FontJustificationH JUSTIFYLEFT, FontJustificationV JUSTIFYMIDDLE, '
                  f'Text "{caption(name) if any(t in name for t in ("Title", "Label")) else ""}",')
    elif kind == "SIMPLESTATUSBAR":
        props = size(.175, .007) + " " + point(parent, .002, .024 + index * .007) + f' File "{ART}bar.blp",'
    elif kind == "SCROLLBAR":
        props = size(.012, .20) + " " + point(parent, 0, .01, "TOPRIGHT") + " SliderLayoutVertical,"
    elif kind == "GLUECHECKBOX":
        props = size(.020, .020) + " " + point(parent, .025 + index * .025, .035)
    elif kind == "EDITBOX":
        props = size(.26, .03) + " " + point(parent, .025, .26) + " EditMaxChars 64,"
    else:
        props = "SetAllPoints,"
    body = ""
    if kind == "BACKDROP":
        props += f' BackdropBackground "{ART}panel.blp", BackdropBlendAll,'
    elif parent is None and not compact:
        body = backdrop(name + "BasicBackground")
    visible_index = 0
    for child in children:
        body += render_tree(child, name, visible_index, compact)
        if kind_for(child["name"], child["children"]) not in ("BACKDROP", "FRAME", "SCROLLBAR"):
            visible_index += 1
    return frame(name, kind, props, body)


def templates():
    result = ""
    for name in ("Title", "Label", "Info", "Button"):
        result += frame("EscMenu" + name + "TextTemplate", "TEXT", 'FrameFont "MasterFont", 0.011, "", FontColor 0.94 0.96 0.98 1,')
    for name in ("EscMenuButtonBackdropTemplate", "EscMenuButtonDisabledBackdropTemplate", "EscMenuPopupMenuBackdropTemplate", "EscMenuPopupMenuDisabledBackdropTemplate"):
        result += backdrop(name, "button")
    result += button("EscMenuButtonTemplate", label="", text_name="EscMenuButtonText")
    for name in ("EscMenuCheckBoxTemplate", "EscMenuRadioButtonTemplate"):
        result += frame(name, "GLUECHECKBOX", size(.02, .02) + f' ControlBackdrop "{name}Normal",', backdrop(name + "Normal", "button"))
    result += frame("EscMenuSliderTemplate", "SLIDER", size(.18, .02) + " SliderLayoutHorizontal, SliderMinValue 0, SliderMaxValue 1, SliderStepSize 0.05,")
    for name in ("EscMenuPopupMenuArrowTemplate", "EscMenuPopupMenuMenuTemplate", "EscMenuPopupMenuTitleTemplate"):
        result += frame(name, "FRAME", size(.18, .025))
    return result


def hud():
    console = frame("ConsoleUI", "SIMPLEFRAME", "SetAllPoints,",
        backdrop("BasicHudTop", props=size(.8, .032) + " " + point("ConsoleUI")) +
        backdrop("BasicHudBottom", props=size(.8, .14) + " " + point("ConsoleUI", corner="BOTTOMLEFT")))
    resource = backdrop("BasicResourcesBackground")
    for i, (name, label) in enumerate((("Gold", "Gold"), ("Lumber", "Wood"), ("Supply", "Food"), ("Upkeep", "Upkeep"))):
        value_name = "ResourceBar" + name + "Text"
        heading = text("BasicResource" + name + "Label", value_name, label, y=-.013, w=.07, h=.013)
        resource += text(value_name, "ResourceBarFrame", "0", x=.005 + i*.078, y=.014, w=.07, h=.013, children=heading)
    upper = "".join(button("UpperButtonBar" + name + "Button", "UpperButtonBarFrame", label,
                            x=.002 + i*.08, y=.003, w=.078, h=.026)
                    for i, (name, label) in enumerate((("Quests", "Quests F9"), ("Menu", "Menu F10"), ("Allies", "Allies F11"), ("Chat", "Log F12"))))
    return {"UI/ConsoleUI": console,
            "UI/ResourceBar": frame("ResourceBarFrame", "SIMPLEFRAME", size(.315, .032), resource),
            "UI/UpperButtonBar": frame("UpperButtonBarFrame", "SIMPLEFRAME", size(.324, .032) + " Anchor TOPLEFT, 0, 0,", upper)}


def script_dialog():
    return (frame("ScriptDialog", "DIALOG", size(.32, .17) + ' DialogBackdrop "ScriptDialogBackdrop",',
                  backdrop("ScriptDialogBackdrop") + text("ScriptDialogText", "ScriptDialog", y=.02, x=.02, w=.28, h=.04, center=True)) +
            button("ScriptDialogButton", w=.26, label=""))


def quest_rows():
    return (frame("QuestListItem", "FRAME", size(.27, .034),
                  button("QuestListItemButton", "QuestListItem", text_name="QuestListItemTitle", label="", x=0, y=0, w=.27, h=.032)) +
            frame("QuestItemListItem", "FRAME", size(.27, .025),
                  text("QuestItemListItemTitle", "QuestItemListItem", w=.27)))


def quest_dialog():
    root = "QuestDialog"
    body = backdrop("QuestBackdrop")
    body += text("QuestTitleValue", root, "Quests", x=.025, y=.012, w=.63, h=.023)
    body += text("QuestSubtitleValue", root, x=.025, y=.040, w=.63)
    for prefix, label, x in (("Main", "Required", .025), ("Optional", "Optional", .355)):
        body += text("Quest" + prefix + "Title", root, label, x=x, y=.073, w=.28)
        body += frame("Quest" + prefix + "Container", "FRAME", size(.28, .13) + " " + point(root, x, .096))
    details = text("QuestDetailsTitle", "QuestDisplayBackdrop", "Details", x=.012, y=.005, w=.60)
    details += frame("QuestItemListContainer", "FRAME", size(.60, .055) + " " + point("QuestDisplayBackdrop", .012, .030))
    scroll = frame("QuestDisplayScrollBar", "SCROLLBAR", size(.012, .10) + " " + point("QuestDisplay", 0, 0, "TOPRIGHT") + " SliderLayoutVertical,")
    details += frame("QuestDisplay", "TEXTAREA", size(.60, .10) + " " + point("QuestDisplayBackdrop", .012, .09) +
                     ' FrameFont "MasterFont", 0.011, "", TextAreaScrollBar "QuestDisplayScrollBar",', scroll)
    body += frame("QuestDisplayBackdrop", "BACKDROP", size(.63, .20) + " " + point(root, .025, .24) +
                  f' BackdropBackground "{ART}panel.blp", BackdropBlendAll,', details)
    body += button("QuestAcceptButton", root, "Done", x=.44, y=.456, w=.19)
    return frame(root, "FRAME", size(.68, .50), body) + quest_rows()


def log_dialog():
    scroll = frame("LogAreaScrollBar", "SCROLLBAR", size(.012, .29) + ' SliderLayoutVertical, ' + point("LogArea", 0, 0, "TOPRIGHT"))
    area = frame("LogArea", "TEXTAREA", size(.58, .29) + " " + point("LogAreaBackdrop", .01, .01) +
                 ' FrameFont "MasterFont", 0.011, "", TextAreaScrollBar "LogAreaScrollBar",', scroll)
    return frame("LogDialog", "FRAME", size(.65, .45), backdrop("LogBackdrop") +
                 text("LogTitle", "LogDialog", "Message log", x=.025, y=.015, w=.6) +
                 frame("LogAreaBackdrop", "BACKDROP", size(.60, .31) + " " + point("LogDialog", .025, .06) + f' BackdropBackground "{ART}panel.blp",', area) +
                 button("LogOkButton", "LogDialog", "Done", x=.445, y=.39, w=.18))


def cinematic_panel():
    scene = backdrop("CinematicPortraitBackground", props=size(.10, .10) + " " + point("CinematicScenePanel", .02, .02))
    scene += frame("CinematicPortrait", "PORTRAIT", size(.10, .10) + " " + point("CinematicScenePanel", .02, .02))
    scene += frame("CinematicPortraitCover", "FRAME", size(.10, .10) + " " + point("CinematicScenePanel", .02, .02))
    scene += text("CinematicSpeakerText", "CinematicScenePanel", x=.14, y=.015, w=.62)
    scene += text("CinematicDialogueText", "CinematicScenePanel", x=.14, y=.04, w=.62, h=.07)
    return frame("CinematicPanel", "FRAME", "SetAllPoints,",
                 backdrop("CinematicBottomBorder", props=size(.8, .14) + " " + point("CinematicPanel", corner="BOTTOMLEFT")) +
                 frame("CinematicScenePanel", "FRAME", size(.8, .14) + " " + point("CinematicPanel", corner="BOTTOMLEFT"), scene) +
                 backdrop("CinematicTopBorder", props=size(.8, .05) + " " + point("CinematicPanel")))


def generate(output, font=None):
    files = {}
    profile = "// Original basic command art; localized command strings remain in imported data.\n"
    for command, (symbol, x, y) in COMMAND_PROFILES.items():
        path = f"UI/BrowserBasic/command-{symbol}.blp"
        files[path] = blp(32, 32, command_pixels(symbol))
        art_path = path.replace("/", "\\")
        profile += f"\n[{command}]\nArt={art_path}\nButtonpos={x},{y}\n"
    files["Units/CommandFunc.txt"] = profile.encode()
    for name, color in TERRAIN.items():
        files["TerrainArt/" + name + ".blp"] = blp(64, 64, terrain_pixels(color))
    for name in ("DRuins", "Lords"):
        files[f"TerrainArt/Blight/{name}_Blight.blp"] = blp(64, 64, terrain_pixels((82, 70, 91)))
    for dimension, suffix in ((2, "Default"), (4, "Default"), (4, "SimpleSolid"), (12, "Simple"), (12, "TreeOfLife")):
        files[f"PathTextures/{dimension}x{dimension}{suffix}.tga"] = pathing_texture(dimension, dimension, suffix == "TreeOfLife")
    for name, color in {"panel": (22, 30, 39, 245), "button": (51, 72, 86, 255),
                        "pressed": (31, 103, 120, 255), "bar": (102, 174, 205, 255),
                        "tree": (64, 133, 63, 255)}.items():
        files["UI/BrowserBasic/" + name + ".blp"] = blp(8, 8, [color] * 64)
    for name, shape in MODELS.items():
        files[name] = primitive_model(kind=shape)
    files["ReplaceableTextures/LordaeronTree/LordaeronSummerTree.blp"] = blp(32, 32, [(64, 133, 63, 255)] * 1024)
    for i, color in enumerate(TEAM_COLORS):
        files[f"ReplaceableTextures/TeamColor/TeamColor{i:02}.blp"] = blp(8, 8, [(*color, 255)] * 64)
        files[f"ReplaceableTextures/TeamGlow/TeamGlow{i:02}.blp"] = blp(64, 64, marker_pixels(color, True))
    for scale in ("Small", "Med", "Large"):
        files[f"ReplaceableTextures/Selection/SelectionCircle{scale}.blp"] = blp(64, 64, marker_pixels((255, 255, 255)))
    for path in (Path(__file__).resolve().parent / "basic-ui-textures.txt").read_text().splitlines():
        if path and not path.startswith("#"):
            files[path] = blp(32, 32, ui_pixels(path))
    screens = {path: "".join(render_tree(tree, compact="InfoPanel" in path)
                              for tree in binding_tree(stem)) for path, stem in SCREENS.items()}
    screens.update(hud())
    screens["UI/EscMenuTemplates"] = templates()
    screens["UI/InfoPanelTemplates"] = '// All basic info-panel frames are self-contained.\n'
    screens["UI/ScriptDialog"] = script_dialog()
    screens["UI/QuestDialog"] = quest_dialog()
    screens["UI/LogDialog"] = log_dialog()
    screens["UI/CinematicPanel"] = cinematic_panel()
    for path, source in screens.items():
        files["UI/FrameDef/" + path + ".fdf"] = ("// Original basic browser assets; generated by port/web/generate-basic-assets.py.\n" + source).encode()
    old = json.loads((output / MANIFEST).read_text()) if (output / MANIFEST).exists() else {"files": {}}
    # The supplied partial installation also has no MasterFont. Use the freely
    # distributable DejaVu font under the data's existing alias, with its license.
    # An existing user-provided loose font takes precedence and is preserved.
    font_alias = "Fonts/FRIZQT__.TTF"
    if not (output / font_alias).exists() or font_alias in old["files"]:
        source = font or Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
        if not source.is_file():
            raise ValueError("Basic HUD requires a font; install fonts-dejavu-core or pass --font PATH")
        files[font_alias] = source.read_bytes()
        license_path = Path("/usr/share/doc/fonts-dejavu-core/copyright")
        if font is None and license_path.is_file():
            files["Fonts/DejaVu-LICENSE.txt"] = license_path.read_bytes()
    # Preflight every path before writing anything, including modified generated
    # assets. This makes repeated generation safe for imported/local game data.
    for name, data in files.items():
        target = output / name
        if target.exists() and target.read_bytes() != data:
            if hashlib.sha256(target.read_bytes()).hexdigest() != old["files"].get(name):
                raise ValueError("Refusing to replace non-generated or edited asset: " + str(target))
    hashes = {}
    for name, data in files.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        hashes[name] = hashlib.sha256(data).hexdigest()
    manifest = {"generator": "port/web/generate-basic-assets.py", "description": "Original simple terrain and UI; no maps or archives modified", "files": hashes}
    (output / MANIFEST).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return files


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "data-input")
    parser.add_argument("--font", type=Path, help="use a locally supplied TrueType font for the basic HUD")
    args = parser.parse_args()
    try:
        files = generate(args.output, args.font)
    except (ValueError, OSError) as exc:
        parser.exit(1, str(exc) + "\n")
    print(f"Prepared {len(files)} basic assets (terrain, UI, font, pathing and primitive models) in {args.output}")
