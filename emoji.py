# Emoji Roguelike — D* Lite & MCTS AI Edition 🎮🐉
# The ultimate AI dungeon crawler. Features Expert BSP Map Generation 🧠,
# Dynamic Biomes 🌿🔮🌋🧊☣️ with Biome-Specific Spawning & Movement AI,
# Multiple Bosses 🐊🐧🗿🐲👨‍💻, D* Lite 🧭 for dynamic pathfinding,
# and MCTS 🌳 for tactical decision-making.

# Controls 🎯:
#   WASD / Arrows — Move / Attack ⚔️
#   . (period)    — Wait ⏳
#   > (Shift+.)   — Descend stairs 🪜
#   Space/Enter   — Confirm / Skip ✅
#   P / Esc       — Pause ⏸️
#   M             — Mute audio 🔇
#   R             — Reduced motion 🌀
#   F1            — Debug overlay 🐛 (Shows MCTS win rates & AI state)
#   F2            — Slow-motion toggle 🐢

import pygame, random, math, sys, os, array, collections, heapq
from dataclasses import dataclass, field
from enum import Enum, auto

# ─── INIT 🚀 ───────────────────────────────────────────────
pygame.init()
HAS_AUDIO = False
try:
    # Lowered sample rate to 22050 for authentic 8-bit retro grit
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=256)
    HAS_AUDIO = True
except Exception:
    pass

# ─── CONFIG ⚙️ ─────────────────────────────────────────────
TILE      = 36
GRID_W    = 28
GRID_H    = 18
HUD_H     = 130
SCREEN_W  = TILE * GRID_W
SCREEN_H  = TILE * GRID_H + HUD_H
FPS       = 60
MAX_FLOOR = 10
VISION_R  = 6.5

C_BG=(10,10,16)
C_HUD=(14,14,22); C_HUD_LN=(55,52,70)
C_TXT=(235,235,245); C_TXT_D=(130,130,150)
C_GOLD=(255,210,60); C_HP=(230,70,80); C_HP_D=(90,30,35)
C_XP=(90,180,255); C_XP_D=(35,60,90)
C_ACC=(255,150,70); C_GRN=(100,220,120); C_RED=(255,90,90)
C_BLU=(90,170,255); C_WHITE=(255,255,255)
C_PURPLE=(180,100,220); C_CYAN=(100,220,220); C_POISON=(120,200,80)
C_ICE=(150,220,255); C_SHOCK=(255,230,90)
C_BLEED=(220, 50, 50); C_STUN=(255, 220, 0)

T_FLOOR=0; T_WALL=1; T_STAIRS=2; T_CHEST=3; T_ALTAR=4; T_FOUNTAIN=5
T_TRAP=6; T_TORCH=7; T_GRAVE=8; T_WATER=9; T_TREE=10; T_WALL_TEMP=11
T_LAVA=12; T_MUSHROOM=13; T_CRYSTAL=14; T_FLOWER=15; T_PORTAL=16

# ─── BIOMES 🌍 ─────────────────────────────────────────────
BIOMES = {
    "overgrown": {
        "floor": (34, 45, 30), "floor_d": (22, 30, 20), "floor_fog": (16, 22, 14),
        "wall": (55, 70, 45), "wall_l": (85, 100, 65), "wall_fog": (28, 36, 22),
        "weather": "🦋",
        "decor": {"T_TREE": 6, "T_FLOWER": 5, "T_MUSHROOM": 3, "T_WATER": 2, "T_CHEST": 2}
    },
    "crystal": {
        "floor": (40, 35, 55), "floor_d": (25, 22, 35), "floor_fog": (15, 14, 22),
        "wall": (65, 55, 85), "wall_l": (95, 85, 115), "wall_fog": (32, 28, 42),
        "weather": "✨",
        "decor": {"T_CRYSTAL": 6, "T_WATER": 2, "T_FLOWER": 1, "T_CHEST": 2}
    },
    "lava": {
        "floor": (50, 30, 25), "floor_d": (35, 20, 15), "floor_fog": (20, 12, 10),
        "wall": (80, 40, 30), "wall_l": (110, 60, 40), "wall_fog": (40, 20, 15),
        "weather": "🔥",
        "decor": {"T_LAVA": 5, "T_TORCH": 4, "T_GRAVE": 1, "T_CHEST": 2}
    },
    "frozen": {
        "floor": (30, 45, 55), "floor_d": (20, 30, 35), "floor_fog": (12, 18, 22),
        "wall": (50, 70, 85), "wall_l": (70, 90, 110), "wall_fog": (25, 35, 42),
        "weather": "❄️",
        "decor": {"T_WATER": 4, "T_TREE": 4, "T_TORCH": 2, "T_CHEST": 2}
    },
    "toxic": {
        "floor": (40, 50, 25), "floor_d": (25, 35, 15), "floor_fog": (15, 22, 10),
        "wall": (60, 75, 35), "wall_l": (85, 100, 50), "wall_fog": (30, 38, 18),
        "weather": "🟢",
        "decor": {"T_WATER": 4, "T_MUSHROOM": 4, "T_GRAVE": 3, "T_TRAP": 4, "T_CHEST": 2}
    }
}

# ─── CLASSES 🦸‍♂️ ───────────────────────────────────────────
CLASSES = [
    ("🧙", "Wizard",   20, 7, 1, "Arcane bolt ✨", None),
    ("🛡️", "Knight",   32, 4, 4, "Stalwart 🏰", None),
    ("🏹", "Ranger",   24, 5, 2, "+1 Vision 👁️", "vision"),
    ("🗡️", "Rogue",    18, 8, 1, "25% Crit 🎯", "crit"),
    ("🧚", "Fairy",    16, 5, 3, "Regen 1/turn ✨", "regen"),
    ("🤺", "Duelist",  26, 6, 2, "15% Riposte 🤺", "riposte"),
    ("👑", "King",     28, 5, 3, "+50% Gold 💰", "gold"),
    ("🦸", "Hero",     24, 6, 2, "Lifesteal 🩸", "lifesteal"),
    ("🧝", "Elf",      22, 6, 2, "Dodge 15% 🤸", "dodge"),
    ("👽", "Alien",    18, 7, 1, "Mind Shock ⚡", "shock"),
    ("🧑‍💻", "Hacker",  18, 5, 2, "Ranged 🖱️", "ranged"),
]

# ─── ENEMIES 👾 ────────────────────────────────────────────
# (name, emoji, hp, atk, def, xp, gold, min_floor, weight, status, ranged, is_boss, biomes)
ENEMIES = [
    # ☣️ TOXIC BIOME CREATURES ☣️
    ("Rat",       "🐀",   5,  3, 0,   3,  2,  1, 10, "poison", False, False, ["toxic", "overgrown", "frozen"]),
    ("Mosquito",  "🦟",   3,  5, 0,   3,  2,  1,  4, "poison", False, False, ["toxic"]),
    ("Snail",     "🐌",   9,  2, 3,   5,  3,  1,  5, "poison", False, False, ["toxic", "overgrown"]),
    ("Snake",     "🐍",  13,  6, 1,   8,  5,  2,  6, "poison", False, False, ["toxic", "overgrown"]),
    ("Virus",     "🦠",  10,  4, 1,   6,  4,  2,  5, "poison", False, False, ["toxic"]),
    ("Scorpion",  "🦂",  15,  7, 2,  11,  7,  3,  5, "poison", False, False, ["toxic"]),
    ("Wasp",      "🐝",   6,  8, 0,   8,  4,  3,  4, "poison", False, False, ["toxic"]),
    ("Zombie",    "🧟",  34, 12, 4,  24, 18,  6,  3, "poison", False, False, ["toxic"]),
    ("Sludge",    "🤢",  28, 10, 3,  20, 15,  6,  2, "poison", True,  False, ["toxic", "crystal"]),
    ("Toad",      "🐸",  12,  5, 1,   6,  3,  2,  4, "poison", False, False, ["toxic", "overgrown"]),
    ("Cockroach", "🪳",   6,  3, 0,   4,  2,  1,  6, "poison", False, False, ["toxic"]),
    ("Skunk",     "🦨",  12,  5, 1,   7,  5,  2,  4, "poison", True,  False, ["toxic", "overgrown"]),
    ("Maggot",    "🪱",   4,  2, 0,   2,  1,  1,  6, "poison", False, False, ["toxic"]),

    # 🌿 OVERGROWN BIOME CREATURES 🌿
    ("Ant",       "🐜",   4,  3, 0,   2,  1,  1,  6, None, False, False, ["overgrown"]),
    ("Beetle",    "🪲",  12,  5, 2,   6,  4,  2,  5, None, False, False, ["overgrown", "crystal"]),
    ("Hedgehog",  "🦔",  10,  6, 2,   6,  4,  2,  5, None, False, False, ["overgrown"]),
    ("Butterfly", "🦋",   8,  5, 0,   6,  4,  3,  4, "poison", False, False, ["overgrown"]),
    ("Peacock",   "🦚",  16,  8, 1,   9,  6,  4,  3, None, False, False, ["overgrown"]),
    ("Giraffe",   "🦒",  35, 12, 2,  28, 20,  6,  3, None, False, False, ["overgrown"]),
    ("Rhino",     "🦏",  40, 15, 6,  30, 20,  6,  3, None, False, False, ["overgrown"]),
    ("Zebra",     "🦓",  20,  8, 2,  15, 10,  3,  3, None, False, False, ["overgrown"]),
    ("Tiger",     "🐯",  22, 11, 3,  18, 12,  4,  4, "bleed", False, False, ["overgrown", "frozen"]),
    ("Lion",      "🦁",  25, 12, 3,  20, 15,  5,  4, "bleed", False, False, ["overgrown", "lava"]),
    ("Bear",      "🐻",  30, 13, 4,  22, 15,  5,  4, None, False, False, ["overgrown", "frozen"]),
    ("Kangaroo",  "🦘",  28, 11, 2,  20, 15,  4,  4, None, False, False, ["overgrown"]),
    ("Dodo",      "🦤",  15,  5, 1,   8,  5,  3,  3, None, False, False, ["overgrown"]),
    ("Gorilla",   "🦍",  35, 14, 3,  25, 15, 5,  3, "stun", False, False, ["overgrown"]),
    ("Panda",     "🐼",  28, 10, 3,  20, 12,  4,  3, None, False, False, ["overgrown", "frozen"]),
    ("Deer",      "🦌",  15,  6, 1,  10,  6,  3,  4, None, False, False, ["overgrown"]),
    ("Owl",       "🦉",  18,  8, 1,  12,  8,  4,  3, None, False, False, ["overgrown", "frozen"]),
    ("Sloth",     "🦥",  20,  4, 4,  15, 10,  4,  2, None, False, False, ["overgrown"]),
    ("Bison",     "🐃",  40, 14, 5,  30, 20,  6,  2, None, False, False, ["overgrown"]),

    # 🌋 LAVA BIOME CREATURES 🌋
    ("Lizard",    "🦎",  12,  6, 2,   8,  5,  2,  5, "burn", False, False, ["lava", "overgrown"]),
    ("Boar",      "🐗",  24,  9, 3,  15, 10,  4,  4, None, False, False, ["lava"]),
    ("Imp",       "👺",  18, 15, 2,  22, 15,  6,  2, "burn", True,  False, ["lava"]),
    ("Ogre",      "👹",  52, 17, 6,  42, 32,  8,  3, None, False, False, ["lava"]),
    ("Demon",     "👿",  46, 19, 5,  44, 36,  8,  2, "burn", True,  False, ["lava"]),
    ("TRex",      "🦖",  65, 22, 7,  75, 60,  9,  1, None, False, False, ["lava"]),
    ("Dragon",    "🐉",  75, 21, 7, 110, 85, 10,  2, "burn", True,  False, ["lava"]),
    ("Wyvern",    "🐲",  40, 16, 4,  38, 30,  7,  2, "burn", True,  False, ["lava"]),
    ("Magworm",   "🪱",  18,  8, 2,  12,  8,  3,  3, "burn", False, False, ["lava"]),
    ("Bull",      "🐂",  30, 12, 4,  22, 14,  4,  3, None, False, False, ["lava"]),
    ("Salamander","🦎",  20,  9, 2,  15, 10,  3,  4, "burn", False, False, ["lava"]),
    ("Cyclops",   "👁️",  35, 15, 3,  28, 20,  6,  2, None, False, False, ["lava", "crystal"]),

    # 🧊 FROZEN BIOME CREATURES 🧊
    ("Bat",       "🦇",   7,  4, 0,   4,  3,  1,  8, "freeze", False, False, ["frozen", "crystal"]),
    ("Crab",      "🦀",  14,  5, 4,   9,  6,  2,  4, "freeze", False, False, ["frozen"]),
    ("Turtle",    "🐢",  18,  4, 5,  10,  6,  2,  3, "freeze", False, False, ["frozen"]),
    ("Eagle",     "🦅",  16, 10, 1,  13, 9,  3,  3, "freeze", False, False, ["frozen"]),
    ("Octopus",   "🐙",  22,  9, 3,  14, 11,  4,  3, "freeze", True,  False, ["frozen"]),
    ("Ghost",     "👻",  20, 11, 2,  18, 13,  5,  4, "freeze", False, False, ["frozen", "crystal"]),
    ("Seal",      "🦭",  20,  8, 2,  15, 10,  3,  3, "freeze", False, False, ["frozen"]),
    ("Mammoth",   "🦣",  45, 14, 5,  35, 28,  6,  2, "freeze", False, False, ["frozen"]),
    ("Wolf",      "🐺",  19,  9, 2,  13, 9,  3,  5, "bleed", False, False, ["frozen", "overgrown"]),
    ("Penguin",   "🐧",  16,  7, 2,  12, 8,  3,  4, "freeze", False, False, ["frozen"]),
    ("Moose",     "🫎",  40, 14, 4,  30, 20,  6,  2, None, False, False, ["frozen"]),
    ("Snow Leopard","🐆", 28, 13, 2,  22, 15,  5,  3, "bleed", False, False, ["frozen"]),

    # 🔮 CRYSTAL BIOME CREATURES 🔮
    ("Slime",     "👾",   8,  3, 1,   4,  3,  1,  8, None, False, False, ["crystal"]),
    ("Vampire",   "🧛",  30, 14, 3,  26, 22,  6,  3, "bleed", False, False, ["crystal"]),
    ("Flayer",    "🐙",  30,  8, 4,  25, 20,  6,  2, "shock", True,  False, ["crystal"]),
    ("Golem",     "🤖",  62, 15, 9,  52, 42,  9,  2, "shock", True,  False, ["crystal"]),
    ("Unicorn",   "🦄",  50, 18, 5,  45, 40,  8,  2, "freeze", True,  False, ["crystal"]),
    ("Alien",     "👽",  20, 10, 2,  15, 12,  4,  3, "shock", True,  False, ["crystal"]),
    ("Gargoyle",  "🗿",  45, 12, 8,  35, 25,  7,  2, "stun", False, False, ["crystal"]),
    ("Mimic",     "🃏",  30, 15, 3,  40, 30,  6,  1, None, False, False, ["crystal", "any"]),
    ("Warlock",   "🧙‍♀️", 20, 10, 2,  18, 12,  5,  3, "weaken", True,  False, ["crystal", "any"]),

    # 🌑 ANY BIOME CREATURES (Dungeon Crawlers) 🌑
    ("Bug",       "🐛",   3,  3, 0,   2,  1,  1,  6, None, False, False, ["any"]),
    ("Goblin",    "👺",  17,  8, 2,  11,  8,  3,  6, None, False, False, ["any"]),
    ("Skeleton",  "💀",  22, 10, 3,  15, 11,  4, 5, None, False, False, ["any"]),
    ("Evil Mage", "🧙‍♂️", 15,  6, 2,  12,  8,  3,  4, "burn", True,  False, ["any"]),
    ("Ninja",     "🥷",  25, 12, 2,  20, 15,  4,  3, "bleed", False, False, ["any"]),
    ("Cultist",   "🧙",  18,  8, 2,  15, 10,  3,  4, "burn", True,  False, ["any"]),
    ("Raven",     "🐦‍⬛", 15,  8, 1,  12,  8,  4,  3, None, True,  False, ["any"]),
    
    # 🩸 NEW STATUS EFFECT CREATURES & CROSS-BIOME 🩸
    ("Swamp Beast", "🐊",  45, 16, 5,  40, 30,  6,  3, "bleed", False, False, ["toxic", "overgrown"]),
    ("Rock Golem",  "🗿",  55, 12, 8,  45, 35,  4,  3, "stun", False, False, ["lava", "crystal"]),
    ("Giant Rat",   "🐀",  10,  5, 1,   6,  4,  1,  8, "bleed", False, False, ["toxic", "overgrown", "frozen", "any"]),
    ("Lava Strider","🕷️",  18, 10, 2,  14,  9,  4,  3, "burn", False, False, ["lava"]),
    ("Ice Spider",  "🕷️",  20,  8, 2,  15, 10,  3,  5, "freeze", False, False, ["frozen", "toxic", "crystal"]),
    ("Mana Wraith", "👻",  25, 12, 1,  22, 15,  4,  3, "weaken", True,  False, ["crystal", "lava"]),
    ("Adventurer",  "🧗",  40, 14, 4,  30, 25,  4,  3, None, True,  False, ["any"]),
    ("Chameleon",   "🦎",  25,  9, 3,  20, 15,  3,  4, None, False, False, ["overgrown", "crystal", "toxic"]),
    ("Plague Doctor","🧑‍⚕️", 28, 10, 2,  25, 20,  5,  2, "poison", True,  False, ["toxic", "any"]),
    ("Lich",        "💀",  45, 16, 4,  40, 35,  6,  1, "weaken", True,  False, ["crystal", "toxic", "any"]),

    # 👑 BOSSES (Floor-Specific) 👑
    ("Swamp King",  "🐊",  80, 14, 5,  80, 60,  3, 1, "poison", True,  True, ["toxic"]),
    ("Frost Monarch","🐧",  90, 16, 6,  90, 70,  5, 1, "freeze", True,  True, ["frozen"]),
    ("Crystal Titan","🗿", 110, 18, 8, 100, 80,  7, 1, "shock",  True,  True, ["crystal"]),
    ("Inferno Drake","🐲", 130, 20, 7, 120,100,  9, 1, "burn",   True,  True, ["lava"]),
    ("Dev AI",      "👨‍💻", 150, 18, 5, 200,150, 10, 1, "shock",  True,  True, ["any"]),
]

# ─── ITEMS 🎁 ──────────────────────────────────────────────
ITEM_DEFS = {
    'potion_hp':     ("🧪", "Health Potion",   "Restores 20 HP ❤️"),
    'potion_str':    ("🍷", "Strength Elixir", "+2 ATK permanent ⚔️"),
    'potion_def':    ("🫖", "Iron Brew",       "+1 DEF permanent 🛡️"),
    'scroll_tele':   ("📜", "Teleport Scroll", "Blink to random room ✨"),
    'scroll_reveal': ("📃", "Mapping Scroll",  "Reveal entire floor 🗺️"),
    'gold':          ("💰", "Gold Pouch",      "+15 gold 💰"),
    'gem':           ("💎", "Gemstone",        "+60 gold 💎"),
    'food':          ("🍖", "Meat",            "+10 HP, +2 Max HP 🍖"),
    'bomb':          ("💣", "Bomb",            "Damage all visible foes 💥"),
    'tome':          ("📖", "Tome",            "Instant +30 XP 📚"),
    'broom':         ("🧹", "Broom",           "Teleport to stairs 🧹"),
    'amulet':        ("🧿", "Amulet",          "Cures status effects 🧿"),
    'cat':           ("🐱", "Cat",             "Familiar attacks for you 🐱"),
    'laptop':        ("💻", "Laptop",          "Reveals map, +50 XP 💻"),
    'keyboard':      ("⌨️", "Keyboard",        "+3 ATK, Ranged attack ⌨️"),
    'weapon_axe':    ("🪓", "Battleaxe",       "+4 ATK 🪓"),
    'weapon_spear':  ("🔱", "Trident",         "+3 ATK, +1 DEF 🔱"),
    'weapon_staff':  ("🪄", "Staff",           "+2 ATK, +1 Vision 🪄"),
    'apple':         ("🍎", "Apple",           "Restores 5 HP"),
    'cheese':        ("🧀", "Cheese",          "+8 HP, +1 Max HP"),
    'cake':          ("🎂", "Cake",            "Restores 30 HP"),
    'shield':        ("🛡️", "Wooden Shield",  "+2 DEF permanent"),
    'bow':           ("🏹", "Bow",             "+2 ATK, Ranged attack"),
    'gun':           ("🔫", "Pistol",          "+4 ATK, Ranged attack"),
    'crown':         ("👑", "Crown",           "+50% Gold permanent"),
    'glasses':       ("👓", "Glasses",         "+1 Vision permanent"),
    'ring':          ("💍", "Ring",            "+1 ATK, +1 DEF"),
    'magnet':        ("🧲", "Magnet",          "Pulls gold to you (+Floor*20)"),
    'hourglass':     ("⏳", "Hourglass",       "Freeze visible enemies for 3 turns"),
    'bell':          ("🔔", "Bell",            "Reveal entire floor"),
    'telescope':     ("🔭", "Telescope",       "+2 Vision permanent"),
    'joystick':      ("🕹️", "Joystick",       "+30 XP"),
    'potion_rage':   ("😡", "Rage Potion",    "+50% DMG for 5 turns"),
    'potion_haste':  ("💨", "Haste Potion",    "Enemies skip 50% turns for 5"),
    'potion_shield': ("🛡️", "Shield Potion",   "Absorbs 20 damage"),
    'scroll_earthquake':("🌍", "Earthquake Scroll","Damages & stuns all visible"),
}

# ─── FONTS 🔤 ──────────────────────────────────────────────
class Fonts:
    def __init__(self):
        self.emoji_source = None
        self._find_emoji_font()
        self._ef = {}
        self._ft_cache = {}
        self.ui  = pygame.font.SysFont("consolas,dejavusansmono,monospace", 14, bold=True)
        self.ttl = pygame.font.SysFont("consolas,dejavusansmono,monospace", 48, bold=True)
        self.hud = pygame.font.SysFont("consolas,dejavusansmono,monospace", 16, bold=True)
        self.big = pygame.font.SysFont("consolas,dejavusansmono,monospace", 22, bold=True)
        self.sml = pygame.font.SysFont("consolas,dejavusansmono,monospace", 11)
        self.med = pygame.font.SysFont("consolas,dejavusansmono,monospace", 17, bold=True)

    def _find_emoji_font(self):
        for path in ["C:/Windows/Fonts/seguiemj.ttf",
                      "/System/Library/Fonts/Apple Color Emoji.ttc",
                      "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
                      "/usr/share/fonts/noto-color-emoji/NotoColorEmoji.ttf"]:
            if os.path.exists(path):
                try:
                    f = pygame.font.Font(path, 28)
                    t = f.render("🧙", True, (255,255,255))
                    if t.get_width() > 12 and t.get_height() > 12:
                        self.emoji_source = ("file", path); return
                except Exception: pass
        for name in ["Segoe UI Emoji","Apple Color Emoji","Noto Color Emoji",
                      "Segoe UI Symbol","Symbola"]:
            try:
                f = pygame.font.SysFont(name, 28)
                t = f.render("🧙", True, (255,255,255))
                if t.get_width() > 12 and t.get_height() > 12:
                    self.emoji_source = ("sys", name); return
            except Exception: pass
        self.emoji_source = ("sys", pygame.font.get_default_font())

    def _gef(self, size):
        if size not in self._ef:
            kind, val = self.emoji_source
            self._ef[size] = pygame.font.Font(val, size) if kind == "file" \
                else pygame.font.SysFont(val, size)
        return self._ef[size]

    def emoji(self, char, size=TILE - 6):
        return self._gef(size).render(char, True, (255,255,255)).convert_alpha()

    def ft_font(self, size):
        if size not in self._ft_cache:
            self._ft_cache[size] = pygame.font.SysFont(
                "consolas,dejavusansmono,monospace", size, bold=True)
        return self._ft_cache[size]

# ─── 8-BIT RETRO SOUND SYNTHESIS 🔊 ────────────────────────
def make_tone(freq, dur, vol=0.3, decay=8, noise=0, sweep=0, wave='square', arp_speed=0.0):
    if not HAS_AUDIO: return None
    sr = 22050; n = int(sr * dur); arr = array.array('h')
    for i in range(n):
        t = i / sr; env = math.exp(-t * decay)
        
        # Support for 8-bit arpeggios
        if isinstance(freq, list) and arp_speed > 0:
            idx = int(t / arp_speed) % len(freq)
            f = freq[idx] + sweep * t
        else:
            f = freq + sweep * t
            
        if wave == 'square':
            phase = (f * t) % 1.0
            v = 1.0 if phase < 0.5 else -1.0
        elif wave == 'triangle':
            phase = (f * t) % 1.0
            v = 2 * abs(2 * phase - 1) - 1
        elif wave == 'sine':
            v = math.sin(2 * math.pi * f * t)
        else: # 'noise' channel
            v = random.uniform(-1, 1)

        if noise > 0 and wave != 'noise':
            v = v * (1 - noise) + random.uniform(-1, 1) * noise

        vi = int(max(-1, min(1, v * env * vol)) * 32767)
        arr.append(vi); arr.append(vi)
    try: return pygame.mixer.Sound(buffer=arr.tobytes())
    except Exception: return None

class SFX:
    def __init__(self):
        self.muted = False; self.s = {}
        if HAS_AUDIO:
            # 8-bit Chiptune Sound Effects
            self.s['hit']      = make_tone(180, 0.08, 0.3, 12, 0.1, -100, 'square')
            self.s['crit']     = make_tone(330, 0.15, 0.4, 10, 0.1, -200, 'square')
            self.s['hurt']     = make_tone(140, 0.20, 0.35, 8, 0.1, -50, 'square')
            self.s['pickup']   = make_tone([523, 659, 784], 0.15, 0.25, 8, 0, 0, 'square', arp_speed=0.05)
            self.s['gold']     = make_tone([880, 1046], 0.08, 0.25, 10, 0, 0, 'square', arp_speed=0.04)
            self.s['gem']      = make_tone([659, 880, 1046, 1318], 0.20, 0.3, 6, 0, 0, 'triangle', arp_speed=0.05)
            self.s['levelup']  = make_tone([523, 659, 784, 1046], 0.45, 0.3, 3, 0, 0, 'square', arp_speed=0.12)
            self.s['stairs']   = make_tone([330, 392, 494], 0.30, 0.25, 5, 0, 0, 'triangle', arp_speed=0.1)
            self.s['death']    = make_tone([220, 175, 147, 110], 0.70, 0.35, 2.5, 0, 0, 'triangle', arp_speed=0.18)
            self.s['select']   = make_tone(660, 0.05, 0.15, 20, 0, 0, 'square')
            self.s['victory']  = make_tone([523, 659, 784, 1046, 1318], 0.90, 0.3, 1.5, 0, 0, 'square', arp_speed=0.15)
            self.s['bump']     = make_tone(100, 0.05, 0.2, 20, 0.3, 0, 'square')
            self.s['chest']    = make_tone([440, 554, 659], 0.25, 0.3, 6, 0, 0, 'square', arp_speed=0.08)
            self.s['altar']    = make_tone([330, 392, 494, 587], 0.40, 0.25, 3, 0, 0, 'triangle', arp_speed=0.1)
            self.s['fountain'] = make_tone([784, 880, 988, 1046], 0.30, 0.2, 5, 0, 0, 'triangle', arp_speed=0.08)
            self.s['trap']     = make_tone(120, 0.20, 0.35, 8, 0.2, -60, 'square')
            self.s['poison']   = make_tone(220, 0.12, 0.2, 10, 0.2, -40, 'square')
            self.s['burn']     = make_tone(300, 0.12, 0.2, 10, 0.3, 50, 'square')
            self.s['freeze']   = make_tone([880, 660, 440], 0.20, 0.2, 8, 0, 0, 'triangle', arp_speed=0.07)
            self.s['shock']    = make_tone(1000, 0.08, 0.25, 15, 0.4, -400, 'square')
            self.s['bleed']    = make_tone(200, 0.10, 0.2, 8, 0.1, -100, 'square')
            self.s['stun']     = make_tone([500, 400, 500, 400], 0.25, 0.25, 4, 0, 0, 'square', arp_speed=0.06)
            self.s['weaken']   = make_tone(350, 0.15, 0.25, 6, 0, -150, 'triangle')
            self.s['teleport'] = make_tone([600, 800, 1000, 800, 600], 0.30, 0.2, 4, 0, 0, 'square', arp_speed=0.05)
            self.s['reveal']   = make_tone([440, 554, 659, 784, 880], 0.35, 0.2, 4, 0, 0, 'square', arp_speed=0.06)
            self.s['bomb']     = make_tone(100, 0.40, 0.5, 4, 0.8, -50, 'noise')
            self.s['eat']      = make_tone([300, 350, 400], 0.15, 0.2, 8, 0, 0, 'square', arp_speed=0.05)
            self.s['grave']    = make_tone([110, 140], 0.50, 0.25, 3, 0.1, 0, 'triangle', arp_speed=0.25)
            self.s['shoot']    = make_tone(700, 0.08, 0.2, 12, 0.1, -300, 'square')
            self.s['ai_think'] = make_tone([880, 988, 1046], 0.15, 0.1, 12, 0.1, 0, 'square', arp_speed=0.05)
            self.s['ai_build'] = make_tone([220, 165], 0.25, 0.3, 5, 0.2, 0, 'square', arp_speed=0.12)
    def play(self, name):
        if self.muted: return
        snd = self.s.get(name)
        if snd: snd.play()
    def toggle(self): self.muted = not self.muted

# ─── DATA 📦 ───────────────────────────────────────────────
@dataclass
class Particle:
    x: float; y: float; vx: float; vy: float
    life: float; max_life: float
    color: tuple; size: float; gravity: float = 0
    target_hud: tuple = None

@dataclass
class FloatText:
    x: float; y: float; text: str
    color: tuple; life: float; max_life: float
    vy: float = -45.0; size: int = 16; emoji: str = None

@dataclass
class StatusEffect:
    kind: str
    duration: int
    damage: int

@dataclass
class Buff:
    kind: str
    duration: int
    value: int = 0

@dataclass
class Projectile:
    x: float; y: float
    tx: float; ty: float
    speed: float
    emoji: str
    damage: int
    owner: str
    attacker: any
    target: any
    status: str = None

@dataclass
class Entity:
    x: int; y: int
    emoji: str; name: str
    hp: int; max_hp: int
    atk: int; defense: int
    xp_reward: int = 0; gold_reward: int = 0
    render_x: float = 0.0; render_y: float = 0.0
    sx: float = 1.0; sy: float = 1.0
    flash: float = 0.0; is_player: bool = False
    level: int = 1; xp: int = 0; xp_next: int = 20; gold: int = 0
    dead: bool = False
    lunge_t: float = 0.0; lunge_dx: float = 0.0; lunge_dy: float = 0.0
    bob_t: float = 0.0
    status: list = field(default_factory=list)
    status_t: float = 0.0
    cls_name: str = ""
    regen: int = 0
    crit_chance: float = 0.0
    riposte: float = 0.0
    vision_bonus: int = 0
    gold_bonus: float = 1.0
    lifesteal: float = 0.0
    dodge: float = 0.0
    status_kind: str = None
    frozen: int = 0
    stunned: int = 0
    weapon_emoji: str = "✊"
    bonus_atk: int = 0
    bonus_def: int = 0
    ranged: bool = False
    is_boss: bool = False
    ai_state: str = "IDLE"
    ai_path: list = field(default_factory=list)
    biomes: list = field(default_factory=lambda: ["any"])
    buffs: list = field(default_factory=list)
    shield: int = 0
    is_elite: bool = False

@dataclass
class GameItem:
    x: int; y: int; kind: str; emoji: str; value: int; name: str; bob: float = 0.0

class State(Enum):
    CLASS_SELECT = auto(); PLAYING = auto(); PAUSED = auto()
    GAME_OVER = auto(); VICTORY = auto(); FLOOR_MSG = auto()

# ─── D* LITE PATHFINDING 🧭 ────────────────────────────────
class DStarLite:
    def __init__(self, game, start, goal):
        self.game = game
        self.start = start
        self.goal = goal
        self.km = 0
        self.g = {}
        self.rhs = {}
        self.U = []
        self.rhs[goal] = 0
        self.insert(goal, self.calc_key(goal))
        self.compute_shortest_path()

    def h(self, a, b):
        return abs(a[0]-b[0]) + abs(a[1]-b[1])

    def calc_key(self, s):
        g = self.g.get(s, float('inf'))
        rhs = self.rhs.get(s, float('inf'))
        return (min(g, rhs) + self.h(self.start, s) + self.km, min(g, rhs))

    def insert(self, s, key):
        heapq.heappush(self.U, (key, s))

    def update_vertex(self, u):
        if u != self.goal:
            self.rhs[u] = min(self.cost(u, s) + self.g.get(s, float('inf')) for s in self.succ(u))
        if self.g.get(u, float('inf')) != self.rhs.get(u, float('inf')):
            self.insert(u, self.calc_key(u))

    def cost(self, u, v):
        if not self.game.dungeon.walkable(u[0], u[1]): return float('inf')
        if not self.game.dungeon.walkable(v[0], v[1]): return float('inf')
        if any(e.x == v[0] and e.y == v[1] for e in self.game.enemies if not e.dead): return 5
        return 1

    def succ(self, u):
        x, y = u
        return [(x+dx, y+dy) for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]]

    def compute_shortest_path(self):
        for _ in range(500): 
            if not self.U: break
            k_old, u = heapq.heappop(self.U)
            if k_old < self.calc_key(u):
                self.insert(u, self.calc_key(u))
            elif self.g.get(u, float('inf')) > self.rhs.get(u, float('inf')):
                self.g[u] = self.rhs[u]
                for s in self.succ(u):
                    self.update_vertex(s)
            else:
                g_old = self.g.get(u, float('inf'))
                self.g[u] = float('inf')
                self.update_vertex(u)
                for s in self.succ(u):
                    self.update_vertex(s)

    def get_next_step(self):
        if self.g.get(self.start, float('inf')) == float('inf'): return None
        return min(self.succ(self.start), key=lambda s: self.cost(self.start, s) + self.g.get(s, float('inf')))

# ─── MCTS 🌳 (Monte Carlo Tree Search) ─────────────────────
class MCTSNode:
    def __init__(self, state, parent=None, action=None):
        self.state = state
        self.parent = parent
        self.action = action
        self.children = []
        self.visits = 0
        self.value = 0.0
        self.untried_actions = self.get_valid_actions(state)

    def get_valid_actions(self, state):
        b_x, b_y, p_x, p_y, b_hp, p_hp, walls = state
        actions = []
        if abs(b_x-p_x) + abs(b_y-p_y) > 1 and abs(b_x-p_x) <= 6 and abs(b_y-p_y) <= 6:
            actions.append(("ranged", 0, 0))
        if abs(b_x-p_x) + abs(b_y-p_y) <= 3 and len(walls) < 6:
            actions.append(("wall", 0, 0))
        if b_hp < 60:
            actions.append(("summon", 0, 0))
        dx = 1 if p_x > b_x else (-1 if p_x < b_x else 0)
        dy = 1 if p_y > b_y else (-1 if p_y < b_y else 0)
        if dx != 0: actions.append(("move", dx, 0))
        if dy != 0: actions.append(("move", 0, dy))
        return actions

    def select(self):
        c = 1.414
        best = max(self.children, key=lambda ch: ch.value / (ch.visits + 1e-6) + c * math.sqrt(self.visits / (ch.visits + 1e-6)))
        return best

    def expand(self):
        action = self.untried_actions.pop()
        next_state = apply_action(self.state, action)
        child = MCTSNode(next_state, self, action)
        self.children.append(child)
        return child

    def simulate(self, depth=5):
        state = self.state
        for _ in range(depth):
            state = random_rollout(state)
            b_x, b_y, p_x, p_y, b_hp, p_hp, walls = state
            if p_hp <= 0: return 100.0
            if b_hp <= 0: return -100.0
        return (b_hp - p_hp) * 0.5

def apply_action(state, action):
    b_x, b_y, p_x, p_y, b_hp, p_hp, walls = state
    act, dx, dy = action
    new_walls = set(walls)
    if act == "ranged":
        p_hp -= 15
    elif act == "wall":
        new_walls.add((p_x, p_y)) 
    elif act == "summon":
        pass 
    elif act == "move":
        nx, ny = b_x + dx, b_y + dy
        if 0 <= nx < GRID_W and 0 <= ny < GRID_H and (nx, ny) not in new_walls:
            if not (nx == p_x and ny == p_y): 
                b_x, b_y = nx, ny
            else:
                p_hp -= 10 
    return (b_x, b_y, p_x, p_y, b_hp, p_hp, frozenset(new_walls))

def random_rollout(state):
    node = MCTSNode(state)
    if not node.untried_actions: return state
    action = random.choice(node.untried_actions)
    state = apply_action(state, action)
    b_x, b_y, p_x, p_y, b_hp, p_hp, walls = state
    dx = 1 if b_x > p_x else (-1 if b_x < p_x else 0)
    dy = 1 if b_y > p_y else (-1 if b_y < p_y else 0)
    if random.random() < 0.5 and dx != 0:
        p_x += dx
    elif dy != 0:
        p_y += dy
    if abs(b_x-p_x) + abs(b_y-p_y) <= 1:
        b_hp -= 10 
    return (b_x, b_y, p_x, p_y, b_hp, p_hp, walls)

def mcts_search(boss_state, iterations=50):
    root = MCTSNode(boss_state)
    for _ in range(iterations):
        node = root
        while node.untried_actions == [] and node.children != []:
            node = node.select()
        if node.untried_actions:
            node = node.expand()
        reward = node.simulate()
        while node is not None:
            node.visits += 1
            node.value += reward
            node = node.parent
    if not root.children: return None
    best = max(root.children, key=lambda c: c.visits)
    return best.action

# ─── EXPERT BSP (BINARY SPACE PARTITIONING) MAP GEN 🧠 ─────
class Dungeon:
    def __init__(self, floor_num):
        self.floor = floor_num
        self.grid = [[T_WALL] * GRID_W for _ in range(GRID_H)]
        self.rooms = []
        self.specials = {}
        
        biomes_list = ["overgrown", "crystal", "lava", "frozen", "toxic"]
        self.biome = biomes_list[(floor_num - 1) // 2]
        self.colors = BIOMES[self.biome]
        
        self._bsp_gen()
        self._place_decor()

    def _bsp_split(self, rect, depth):
        x, y, w, h = rect
        if depth == 0 or (w < 8 and h < 6):
            return [rect]
        
        split_h = random.choice([True, False])
        if w > h * 1.25: split_h = True
        if h > w * 1.25: split_h = False
        
        if split_h:
            if w < 8: return [rect]
            split = random.randint(w//3, w*2//3)
            return self._bsp_split((x, y, split, h), depth-1) + self._bsp_split((x+split, y, w-split, h), depth-1)
        else:
            if h < 6: return [rect]
            split = random.randint(h//3, h*2//3)
            return self._bsp_split((x, y, w, split), depth-1) + self._bsp_split((x, y+split, w, h-split), depth-1)

    def _bsp_gen(self):
        root_rect = (1, 1, GRID_W-2, GRID_H-2)
        leaves = self._bsp_split(root_rect, 4) 
        
        for rx, ry, rw, rh in leaves:
            pad_x = random.randint(0, max(0, rw//4))
            pad_y = random.randint(0, max(0, rh//4))
            rx += pad_x; ry += pad_y
            rw -= pad_x * 2; rh -= pad_y * 2
            if rw < 2: rw = 2
            if rh < 2: rh = 2
            
            self.rooms.append((rx, ry, rw, rh))
            for i in range(rx, rx+rw):
                for j in range(ry, ry+rh):
                    if 0 <= i < GRID_W and 0 <= j < GRID_H:
                        self.grid[j][i] = T_FLOOR
                        
        for i in range(len(self.rooms)-1):
            r1 = self.rooms[i]; r2 = self.rooms[i+1]
            x1 = r1[0]+r1[2]//2; y1 = r1[1]+r1[3]//2
            x2 = r2[0]+r2[2]//2; y2 = r2[1]+r2[3]//2
            if random.random() < 0.5: self._ch(x1,x2,y1); self._cv(y1,y2,x2)
            else: self._cv(y1,y2,x1); self._ch(x1,x2,y2)

    def _ch(self, x1, x2, y):
        for x in range(min(x1,x2), max(x1,x2)+1):
            if 0 <= x < GRID_W: self.grid[y][x] = T_FLOOR
    def _cv(self, y1, y2, x):
        for y in range(min(y1,y2), max(y1,y2)+1):
            if 0 <= y < GRID_H: self.grid[y][x] = T_FLOOR

    def _place_decor(self):
        if len(self.rooms) < 2: return
        used = set()
        
        decor_mult = len(self.rooms)
        for tile_type, base_count in self.colors["decor"].items():
            count = max(1, int(base_count * (decor_mult / 5.0)))
            for _ in range(count):
                pos = self.rand_pos(avoid=used)
                if pos: 
                    used.add(pos)
                    self.specials[pos] = globals()[tile_type]
                    
        if random.random() < 0.5:
            pos = self.rand_pos(avoid=used)
            if pos: used.add(pos); self.specials[pos] = T_ALTAR
        if random.random() < 0.4:
            pos = self.rand_pos(avoid=used)
            if pos: used.add(pos); self.specials[pos] = T_FOUNTAIN
        if random.random() < 0.3:
            pos = self.rand_pos(avoid=used)
            if pos: used.add(pos); self.specials[pos] = T_PORTAL

        for _ in range(min(self.floor, 5)):
            pos = self.rand_pos(avoid=used)
            if pos: used.add(pos); self.specials[pos] = T_TRAP
            
        for _ in range(4):
            pos = self.rand_pos(avoid=used)
            if pos:
                wx, wy = pos
                if any(self.grid[wy+dy][wx+dx] == T_WALL for dx in [-1,1,0,0] for dy in [-1,1,0,0] if 0<=wx+dx<GRID_W and 0<=wy+dy<GRID_H):
                    used.add(pos); self.specials[pos] = T_TORCH

    def rand_pos(self, avoid=None):
        if not self.rooms: return None
        for _ in range(300):
            r = random.choice(self.rooms)
            x = random.randint(r[0], r[0]+r[2]-1)
            y = random.randint(r[1], r[1]+r[3]-1)
            if avoid and (x, y) in avoid: continue
            return (x, y)
        return None

    def tile_at(self, x, y):
        if not (0 <= x < GRID_W and 0 <= y < GRID_H): return T_WALL
        if (x, y) in self.specials: return self.specials[(x, y)]
        return self.grid[y][x]

    def walkable(self, x, y):
        if not (0 <= x < GRID_W and 0 <= y < GRID_H): return False
        if self.grid[y][x] == T_WALL: return False
        t = self.tile_at(x, y)
        if t in (T_WATER, T_TREE, T_WALL_TEMP, T_CRYSTAL): return False
        return True

def has_los(dungeon, x0, y0, x1, y1):
    dx = abs(x1 - x0); dy = abs(y1 - y0)
    x, y = x0, y0
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        if not (0 <= x < GRID_W and 0 <= y < GRID_H): return False
        if dungeon.grid[y][x] == T_WALL: return False
        if (x, y) in dungeon.specials and dungeon.specials[(x, y)] in (T_TREE, T_WATER, T_WALL_TEMP, T_CRYSTAL): return False
        if (x, y) == (x1, y1): break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy; x += sx
        if e2 < dx:
            err += dx; y += sy
    return True

def get_path(dungeon, start, goal, blocked):
    queue = collections.deque([start])
    visited = {start: None}
    found = False
    while queue:
        curr = queue.popleft()
        if curr == goal:
            found = True
            break
        x, y = curr
        for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            nx, ny = x+dx, y+dy
            if 0 <= nx < GRID_W and 0 <= ny < GRID_H:
                if (dungeon.walkable(nx, ny) or (nx, ny) == goal) and (nx, ny) not in visited and (nx, ny) not in blocked:
                    visited[(nx, ny)] = curr
                    queue.append((nx, ny))
    if not found: return None
    path = []
    curr = goal
    while curr != start:
        path.append(curr)
        curr = visited[curr]
    return path[-1] if path else None

def compute_fov(dungeon, px, py, radius=VISION_R):
    visible = {(px, py)}
    for deg in range(0, 360, 2):
        ang = math.radians(deg)
        dx = math.cos(ang); dy = math.sin(ang)
        x, y = px + 0.5, py + 0.5
        for _ in range(int(radius * 2)):
            x += dx * 0.5; y += dy * 0.5
            tx, ty = int(x), int(y)
            if not (0 <= tx < GRID_W and 0 <= ty < GRID_H): break
            dist = math.hypot(tx - px, ty - py)
            if dist > radius: break
            visible.add((tx, ty))
            if dungeon.grid[ty][tx] == T_WALL: break
            if (tx, ty) in dungeon.specials and dungeon.specials[(tx, ty)] in (T_TREE, T_CRYSTAL):
                break
    for tx, ty in list(visible):
        if (tx, ty) in dungeon.specials and dungeon.specials[(tx, ty)] in (T_TORCH, T_CRYSTAL, T_LAVA):
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    nx, ny = tx+dx, ty+dy
                    if 0 <= nx < GRID_W and 0 <= ny < GRID_H:
                        if math.hypot(dx, dy) <= 2.5:
                            visible.add((nx, ny))
    return visible

# ─── GAME 🎮 ───────────────────────────────────────────────
class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.SCALED, vsync=1)
        pygame.display.set_caption("Emoji Roguelike 🐉🎮")
        self.clock = pygame.time.Clock()
        self.fonts = Fonts()
        self.sfx = SFX()
        self._ec = {}
        self._tc = {}
        self.weather_particles = []
        self.reset()
        self.state = State.CLASS_SELECT
        self.class_idx = 0
        self.class_anim_t = 0.0
        self.ai_dev_msg = None
        self.ai_dev_msg_t = 0.0

    def _eg(self, char, size=TILE - 6):
        key = (char, size)
        if key not in self._ec:
            self._ec[key] = self.fonts.emoji(char, size)
        return self._ec[key]

    def _tg(self, tile, fog=False):
        key = (tile, fog, self.dungeon.biome if self.dungeon else "none")
        if key not in self._tc:
            self._tc[key] = self._render_tile(tile, fog)
        return self._tc[key]

    def _render_tile(self, tile, fog):
        s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
        c = self.dungeon.colors if self.dungeon else BIOMES["overgrown"]
        
        if tile == T_WALL:
            base = c["wall_fog"] if fog else c["wall"]
            pygame.draw.rect(s, base, (0, 0, TILE, TILE))
            light = tuple(max(0, c_ - 30) for c_ in base) if fog else c["wall_l"]
            pygame.draw.rect(s, light, (0, 0, TILE, 3))
            pygame.draw.rect(s, light, (0, 0, 3, TILE))
            dark = tuple(max(0, c_ - 25) for c_ in base)
            pygame.draw.rect(s, dark, (0, TILE-4, TILE, 4))
            pygame.draw.rect(s, dark, (TILE-4, 0, 4, TILE))
        else:
            base = c["floor_fog"] if fog else c["floor"]
            pygame.draw.rect(s, base, (0, 0, TILE, TILE))
            if not fog:
                pygame.draw.rect(s, c["floor_d"], (0, TILE-1, TILE, 1))
                pygame.draw.rect(s, c["floor_d"], (TILE-1, 0, 1, TILE))
        return s

    def reset(self):
        self.dungeon = None
        self.player = None
        self.familiar = None
        self.enemies = []
        self.items = []
        self.particles = []
        self.projectiles = []
        self.float_texts = []
        self.visible = set()
        self.explored = set()
        self.floor = 1
        self.shake = 0.0
        self.shake_x = 0.0; self.shake_y = 0.0
        self.hit_stop = 0.0
        self.time_scale = 1.0
        self.turn_anim = 0.0
        self.turn_anim_max = 0.18
        self.msg = None; self.msg_t = 0.0
        self.floor_msg_t = 0.0
        self.reduced_motion = False
        self.debug = False
        self.game_over_t = 0.0
        self.victory_t = 0.0
        self.kills = 0
        self.total_gold = 0
        self.turn_count = 0
        self.weather_particles.clear()
        self.ai_dev_msg = None
        self.ai_dev_msg_t = 0.0
        self.boss_dstar = None

    def start_game(self, class_idx):
        cls = CLASSES[class_idx]
        self.player = Entity(
            x=0, y=0, emoji=cls[0], name=cls[1],
            hp=cls[2], max_hp=cls[2], atk=cls[3], defense=cls[4],
            is_player=True, cls_name=cls[1]
        )
        passive = cls[6]
        if passive == "regen":    self.player.regen = 1
        elif passive == "crit":   self.player.crit_chance = 0.25
        elif passive == "riposte":self.player.riposte = 0.15
        elif passive == "vision": self.player.vision_bonus = 1
        elif passive == "gold":   self.player.gold_bonus = 1.5
        elif passive == "lifesteal": self.player.lifesteal = 0.3
        elif passive == "dodge":  self.player.dodge = 0.15
        elif passive == "shock":  self.player.status_kind = "shock"
        elif passive == "ranged": self.player.ranged = True
        self.floor = 1
        self._enter_floor()
        self.state = State.FLOOR_MSG
        self.floor_msg_t = 0.0

    def _enter_floor(self):
        self.dungeon = Dungeon(self.floor)
        self._tc.clear() 
        
        start_room = self.dungeon.rooms[0]
        sx = start_room[0] + start_room[2] // 2
        sy = start_room[1] + start_room[3] // 2
        self.player.x = sx; self.player.y = sy
        self.player.render_x = sx; self.player.render_y = sy
        self.enemies.clear(); self.items.clear()
        self._spawn_enemies(); self._spawn_items(); self._place_stairs()
        self.visible = compute_fov(self.dungeon, sx, sy, VISION_R + self.player.vision_bonus)
        self.explored |= self.visible
        self.turn_anim = 0.0
        self._setup_weather()
        
        if self.floor == 3:
            self.ai_dev_msg = "👨‍💻 AI Dev: My Swamp King 🐊 will poison your data!"
        elif self.floor == 5:
            self.ai_dev_msg = "👨‍💻 AI Dev: The Frost Monarch 🐧 has MCTS-optimized freezing!"
        elif self.floor == 7:
            self.ai_dev_msg = "👨‍💻 AI Dev: You cannot defeat the Crystal Titan's 🗿 logic gates!"
        elif self.floor == 9:
            self.ai_dev_msg = "👨‍💻 AI Dev: Inferno Drake 🐲 will burn your CPU to ashes!"
        elif self.floor == 10:
            self.ai_dev_msg = "👨‍💻 AI Dev: Behold, D* Lite + MCTS. I am invincible. 🤖"
        if self.ai_dev_msg:
            self.ai_dev_msg_t = 4.0

    def _setup_weather(self):
        self.weather_particles.clear()
        emoji = self.dungeon.colors["weather"]
        for _ in range(25):
            self.weather_particles.append([
                random.uniform(0, SCREEN_W),
                random.uniform(0, SCREEN_H),
                random.uniform(-20, 20),
                random.uniform(40, 80),
                emoji
            ])

    def _place_stairs(self):
        if self.floor >= MAX_FLOOR: return
        last_room = self.dungeon.rooms[-1]
        sx = last_room[0] + last_room[2] // 2
        sy = last_room[1] + last_room[3] // 2
        self.dungeon.specials[(sx, sy)] = T_STAIRS

    def _spawn_enemies(self):
        floor_boss_def = next((e for e in ENEMIES if e[11] and e[7] == self.floor), None)
        
        if floor_boss_def:
            count = 0 if self.floor == MAX_FLOOR else 2
        else:
            count = 4 + self.floor + random.randint(0, 2)
            
        candidates = []
        for e in ENEMIES:
            if e[7] <= self.floor and not e[11]:
                if self.dungeon.biome in e[12] or "any" in e[12]:
                    candidates.extend([e] * e[8])
        if not candidates: candidates = [ENEMIES[0]]
        
        occupied = {(self.player.x, self.player.y)}
        
        if floor_boss_def:
            e = floor_boss_def
            pos = (self.dungeon.rooms[-1][0] + self.dungeon.rooms[-1][2]//2, 
                   self.dungeon.rooms[-1][1] + self.dungeon.rooms[-1][3]//2)
            occupied.add(pos)
            hp_scale = 1.0 + (self.floor - e[7]) * 0.15
            hp = int(e[2] * hp_scale)
            atk_scale = 1.0 + (self.floor - e[7]) * 0.1
            atk = int(e[3] * atk_scale)
            enemy = Entity(
                x=pos[0], y=pos[1], emoji=e[1], name=e[0],
                hp=hp, max_hp=hp, atk=atk, defense=e[4],
                xp_reward=e[5], gold_reward=e[6],
                status_kind=e[9] if len(e) > 9 else None,
                ranged=e[10] if len(e) > 10 else False,
                is_boss=e[11] if len(e) > 11 else False,
                biomes=e[12] if len(e) > 12 else ["any"]
            )
            enemy.render_x = pos[0]; enemy.render_y = pos[1]
            self.enemies.append(enemy)
            if enemy.is_boss:
                self.boss_dstar = DStarLite(self, (enemy.x, enemy.y), (self.player.x, self.player.y))

        for _ in range(count):
            e = random.choice(candidates)
            pos = self.dungeon.rand_pos(avoid=occupied)
            if not pos: continue
            occupied.add(pos)
            hp_scale = 1.0 + (self.floor - e[7]) * 0.15
            hp = int(e[2] * hp_scale)
            atk_scale = 1.0 + (self.floor - e[7]) * 0.1
            atk = int(e[3] * atk_scale)
            
            is_elite = random.random() < 0.1 and e[7] > 1
            if is_elite:
                hp = int(hp * 1.6)
                atk = int(atk * 1.3)
                name = "Elite " + e[0]
            else:
                name = e[0]
                
            enemy = Entity(
                x=pos[0], y=pos[1], emoji=e[1], name=name,
                hp=hp, max_hp=hp, atk=atk, defense=e[4],
                xp_reward=e[5] + (10 if is_elite else 0), 
                gold_reward=e[6] + (10 if is_elite else 0),
                status_kind=e[9] if len(e) > 9 else None,
                ranged=e[10] if len(e) > 10 else False,
                is_boss=e[11] if len(e) > 11 else False,
                biomes=e[12] if len(e) > 12 else ["any"],
                is_elite=is_elite
            )
            enemy.render_x = pos[0]; enemy.render_y = pos[1]
            self.enemies.append(enemy)

    def _spawn_items(self):
        occupied = {(self.player.x, self.player.y)}
        for en in self.enemies: occupied.add((en.x, en.y))
        n_items = random.randint(3, 5)
        if self.floor == MAX_FLOOR: n_items = 5
        for _ in range(n_items):
            kind = random.choices(
                ['potion_hp', 'potion_str', 'potion_def',
                 'scroll_tele', 'scroll_reveal', 'gold', 'gem',
                 'food', 'bomb', 'tome', 'broom', 'amulet',
                 'cat', 'laptop', 'keyboard',
                 'weapon_axe', 'weapon_spear', 'weapon_staff',
                 'apple', 'cheese', 'cake', 'shield', 'bow', 'gun',
                 'crown', 'glasses', 'ring', 'magnet', 'hourglass',
                 'bell', 'telescope', 'joystick',
                 'potion_rage', 'potion_haste', 'potion_shield', 'scroll_earthquake'],
                weights=[20, 4, 4, 6, 4, 20, 5, 10, 4, 5, 3, 4, 3, 3, 4, 3, 2, 3,
                         15, 10, 5, 5, 4, 3, 2, 5, 4, 3, 3, 3, 4, 5,
                         6, 6, 6, 4]
            )[0]
            pos = self.dungeon.rand_pos(avoid=occupied)
            if not pos: continue
            occupied.add(pos)
            emoji, name, _ = ITEM_DEFS[kind]
            val = {'potion_hp': 20, 'potion_str': 2, 'potion_def': 1,
                   'gold': random.randint(15, 30), 'gem': 60,
                   'food': 10, 'tome': 30,
                   'weapon_axe': 4, 'weapon_spear': 3, 'weapon_staff': 2,
                   'keyboard': 3, 'apple': 5, 'cheese': 8, 'cake': 30,
                   'shield': 2, 'bow': 2, 'gun': 4, 'glasses': 1, 'ring': 1,
                   'telescope': 2, 'joystick': 30,
                   'potion_rage': 5, 'potion_haste': 5, 'potion_shield': 20, 'scroll_earthquake': 0}.get(kind, 0)
            self.items.append(GameItem(pos[0], pos[1], kind, emoji, val, name))

    def try_move(self, dx, dy):
        if self.state != State.PLAYING: return
        if self.turn_anim > 0: return
        
        if self.player.stunned > 0:
            self.player.stunned -= 1
            self.float_texts.append(FloatText(self.player.x * TILE + TILE//2, self.player.y * TILE - 10, "💫 Stunned!", C_STUN, 1.0, 1.0, vy=-30, size=16))
            self._end_player_turn()
            return

        if self.player.ranged:
            for dist in range(1, 6):
                tx, ty = self.player.x + dx*dist, self.player.y + dy*dist
                if not self.dungeon.walkable(tx, ty): break
                if has_los(self.dungeon, self.player.x, self.player.y, tx, ty):
                    target = next((e for e in self.enemies if e.x == tx and e.y == ty and not e.dead), None)
                    if target:
                        dmg = max(1, (self.player.atk + self.player.bonus_atk) - target.defense)
                        atk_emoji = "🖱️" if self.player.cls_name == "Hacker" else "⌨️"
                        self._ranged_attack(self.player, target, atk_emoji, dmg, self.player.status_kind)
                        return

        nx = self.player.x + dx; ny = self.player.y + dy
        if not self.dungeon.walkable(nx, ny):
            self.sfx.play('bump')
            self._shake(2)
            return
        target = next((e for e in self.enemies if e.x == nx and e.y == ny and not e.dead), None)
        if target:
            self._melee_attack(self.player, target, dx, dy)
        else:
            self.player.x = nx; self.player.y = ny
            self._pickup_items()
            self._check_specials()
            self._end_player_turn()

    def _melee_attack(self, attacker, target, dx=0, dy=0):
        is_crit = (attacker.is_player and random.random() < attacker.crit_chance)
        atk_val = attacker.atk + getattr(attacker, 'bonus_atk', 0)
        def_val = target.defense + getattr(target, 'bonus_def', 0)
        
        shock_mod = 1.5 if any(s.kind == "shock" for s in target.status) else 1.0
        rage_mod = 1.5 if any(b.kind == "rage" for b in attacker.buffs) else 1.0
        weaken_mod = 0.5 if any(s.kind == "weaken" for s in attacker.status) else 1.0
        armor_break_mod = 0 if any(s.kind == "armor_break" for s in target.status) else 1
        
        effective_def = max(0, def_val - 2) if armor_break_mod == 0 else def_val
        
        base_dmg = max(1, atk_val - effective_def)
        dmg = int(base_dmg * (2 if is_crit else 1) * shock_mod * rage_mod * weaken_mod)
        
        if dx or dy:
            attacker.lunge_t = 0.18
            attacker.lunge_dx = dx; attacker.lunge_dy = dy
            
        atk_emoji = getattr(attacker, 'weapon_emoji', "✊")
        self.float_texts.append(FloatText(target.x * TILE - dx*10, target.y * TILE - dy*10, atk_emoji, C_WHITE, 0.4, 0.4, vy=20, size=20))

        if is_crit:
            self.float_texts.append(FloatText(target.x * TILE + TILE//2, target.y * TILE - 10, f"💥{dmg}", C_GOLD, 1.0, 1.0, vy=-55, size=22))
            self._burst(target.x * TILE + TILE//2, target.y * TILE + TILE//2, C_GOLD, 18, speed=200)
            self.sfx.play('crit')
            self._shake(8); self.hit_stop = 0.08
        else:
            self.sfx.play('hit')
            
        self._deal_damage(attacker, target, dmg, getattr(attacker, 'status_kind', None))
        if attacker.is_player:
            self._end_player_turn()

    def _ranged_attack(self, attacker, target, emoji, dmg, status=None):
        sx = attacker.x * TILE + TILE//2
        sy = attacker.y * TILE + TILE//2
        tx = target.x * TILE + TILE//2
        ty = target.y * TILE + TILE//2
        self.projectiles.append(Projectile(sx, sy, tx, ty, 600, emoji, dmg, "player" if attacker.is_player else "enemy", attacker, target, status))
        attacker.lunge_t = 0.1
        self.sfx.play('shoot')
        self.hit_stop = 0.15
        if attacker.is_player:
            self._end_player_turn()

    def _deal_damage(self, attacker, target, dmg, status_kind=None):
        if not attacker.is_player and target.is_player and target.dodge > 0:
            if random.random() < target.dodge:
                self.float_texts.append(FloatText(target.x * TILE + TILE//2, target.y * TILE - 10, "🤸 Dodge!", C_CYAN, 0.8, 0.8, vy=-40, size=16))
                return

        if target.shield > 0:
            absorbed = min(target.shield, dmg)
            target.shield -= absorbed
            dmg -= absorbed
            self.float_texts.append(FloatText(target.x * TILE + TILE//2, target.y * TILE - 10, f"🛡️-{absorbed}", C_BLU, 0.8, 0.8, vy=-40, size=14))
            if dmg <= 0:
                target.flash = 0.5
                return

        target.hp -= dmg
        target.flash = 1.0
        target.sx = 1.35; target.sy = 0.65
        
        hit_x = target.x * TILE + TILE // 2
        hit_y = target.y * TILE + TILE // 2

        self.float_texts.append(FloatText(hit_x, hit_y - 10, str(dmg), C_WHITE, 0.8, 0.8, vy=-45, size=18))
        self._burst(hit_x, hit_y, C_RED, 10, speed=140)
        self._shake(4); self.hit_stop = 0.04

        if attacker.is_player and attacker.lifesteal > 0 and target.hp > 0:
            heal = int(dmg * attacker.lifesteal)
            attacker.hp = min(attacker.max_hp, attacker.hp + heal)
            self.float_texts.append(FloatText(attacker.x*TILE+TILE//2, attacker.y*TILE-10, f"+{heal}❤️", C_HP, 0.8, 0.8, vy=-40, size=14))

        status_chance = 0.6
        if status_kind == "poison" and hasattr(attacker, 'biomes') and "toxic" in attacker.biomes and self.dungeon.biome == "toxic":
            status_chance = 1.0

        if status_kind and random.random() < status_chance:
            duration, s_dmg = 3, 2
            if status_kind == "bleed": duration, s_dmg = 4, 3
            elif status_kind == "stun": duration, s_dmg = 2, 0
            elif status_kind == "weaken": duration, s_dmg = 3, 0
            elif status_kind == "armor_break": duration, s_dmg = 3, 0
            
            target.status.append(StatusEffect(status_kind, duration, s_dmg))
            s_emoji = {"poison":"🟢", "burn":"🔥", "freeze":"🥶", "shock":"⚡", "bleed":"🩸", "stun":"💫", "weaken":"🔻", "armor_break":"🪓"}[status_kind]
            s_col = {"poison":C_POISON, "burn":C_ACC, "freeze":C_ICE, "shock":C_SHOCK, "bleed":C_BLEED, "stun":C_STUN, "weaken":C_PURPLE, "armor_break":C_ACC}[status_kind]
            self.float_texts.append(FloatText(target.x * TILE + TILE//2, target.y * TILE - 10, f"{s_emoji} {status_kind.title()}!", s_col, 1.2, 1.2, vy=-30, size=14))
            self.sfx.play(status_kind)
            
            if status_kind == "freeze": target.frozen = duration
            if status_kind == "stun": target.stunned = duration

        if target.hp <= 0:
            target.dead = True
            self._on_kill(attacker, target)

        if not attacker.is_player and not target.dead:
            if target.is_player and target.riposte > 0 and random.random() < target.riposte:
                rip_dmg = max(1, (target.atk + target.bonus_atk) // 2 - attacker.defense)
                attacker.hp -= rip_dmg
                attacker.flash = 1.0
                self.float_texts.append(FloatText(attacker.x*TILE+TILE//2, attacker.y*TILE-10, f"🤺{rip_dmg}", C_BLU, 0.9, 0.9, vy=-40, size=16))
                self.sfx.play('hit')
                if attacker.hp <= 0:
                    attacker.dead = True
                    self._on_kill(target, attacker)

    def _familiar_attack(self, target):
        dmg = max(1, self.familiar.atk - target.defense)
        target.hp -= dmg
        target.flash = 1.0
        self.float_texts.append(FloatText(target.x*TILE+TILE//2, target.y*TILE-10, f"🐱{dmg}", C_WHITE, 0.6, 0.6, vy=-30, size=14))
        self._burst(target.x*TILE+TILE//2, target.y*TILE+TILE//2, C_WHITE, 5)
        if target.hp <= 0:
            target.dead = True
            self._on_kill(self.player, target)

    def _on_kill(self, killer, victim):
        self.kills += 1
        vx = victim.x * TILE + TILE // 2
        vy = victim.y * TILE + TILE // 2
        self._burst(vx, vy, C_RED, 20, speed=180)
        self._burst(vx, vy, C_GOLD, 8, speed=120)
        self.float_texts.append(FloatText(vx, vy - 20, "💀", C_TXT_D, 1.0, 1.0, vy=-30, size=20))
        self.sfx.play('death')
        self._shake(6); self.hit_stop = 0.06
        
        if killer.is_player or (hasattr(killer, 'is_player') and killer.is_player):
            self.player.xp += victim.xp_reward
            gold_gain = int(victim.gold_reward * self.player.gold_bonus)
            self.player.gold += gold_gain
            self.total_gold += gold_gain
            self.float_texts.append(FloatText(vx + 20, vy, f"+{victim.xp_reward}xp", C_XP, 1.0, 1.0, vy=-35, size=14))
            hud_x = SCREEN_W - 140; hud_y = SCREEN_H - 90
            self.particles.append(Particle(vx, vy, 0, -50, 1.5, 1.5, C_GOLD, 6, gravity=0, target_hud=(hud_x, hud_y)))
            self.sfx.play('gold')
            if self.player.xp >= self.player.xp_next:
                self._level_up()
                
        if victim.is_boss:
            if victim.name != "Dev AI":
                loot = random.choice(['potion_hp', 'potion_str', 'potion_def', 'weapon_axe', 'weapon_spear', 'weapon_staff', 'crown', 'ring', 'hourglass', 'gun'])
                fake = GameItem(victim.x, victim.y, loot, ITEM_DEFS[loot][0], ITEM_DEFS[loot][2], ITEM_DEFS[loot][1])
                self.items.append(fake)
                self.float_texts.append(FloatText(vx, vy - 40, "🎁 Boss Loot!", C_GOLD, 2.0, 2.0, vy=-30, size=18))
            
            if victim.name == "Dev AI" and self.floor == MAX_FLOOR:
                self.state = State.VICTORY
                self.victory_t = 0.0
                self.sfx.play('victory')
            else:
                self.float_texts.append(FloatText(vx, vy - 20, "🏆 Boss Defeated!", C_GOLD, 2.0, 2.0, vy=-30, size=22))
                self._burst(vx, vy, C_GOLD, 40, speed=200)

    def _level_up(self):
        self.player.level += 1
        self.player.xp -= self.player.xp_next
        self.player.xp_next = int(self.player.xp_next * 1.4)
        self.player.max_hp += 8
        self.player.hp = self.player.max_hp
        self.player.atk += 2
        self.player.defense += 1
        px = self.player.x * TILE + TILE // 2
        py = self.player.y * TILE + TILE // 2
        self.float_texts.append(FloatText(px, py - 30, "⭐ LEVEL UP! ⭐", C_GOLD, 1.8, 1.8, vy=-50, size=20))
        self._burst(px, py, C_GOLD, 30, speed=200)
        self._burst(px, py, C_BLU, 15, speed=150)
        self.sfx.play('levelup')
        self._shake(5)

    def _pickup_items(self):
        px, py = self.player.x, self.player.y
        remaining = []
        for item in self.items:
            if item.x == px and item.y == py:
                self._apply_item(item)
            else:
                remaining.append(item)
        self.items = remaining

    def _apply_item(self, item):
        ix = item.x * TILE + TILE // 2
        iy = item.y * TILE + TILE // 2
        if item.kind == 'potion_hp':
            heal = min(item.value, self.player.max_hp - self.player.hp)
            self.player.hp += heal
            self.float_texts.append(FloatText(ix, iy, f"❤️ +{heal}", C_HP, 1.2, 1.2, size=18))
            self._burst(ix, iy, C_HP, 12, speed=100)
            self.sfx.play('pickup')
        elif item.kind == 'potion_str':
            self.player.atk += item.value
            self.float_texts.append(FloatText(ix, iy, f"⚔️ +{item.value} ATK", C_ACC, 1.5, 1.5, size=16))
            self._burst(ix, iy, C_ACC, 15, speed=130)
            self.sfx.play('pickup')
        elif item.kind == 'potion_def':
            self.player.defense += item.value
            self.float_texts.append(FloatText(ix, iy, f"🛡️ +{item.value} DEF", C_BLU, 1.5, 1.5, size=16))
            self._burst(ix, iy, C_BLU, 15, speed=130)
            self.sfx.play('pickup')
        elif item.kind == 'food':
            self.player.max_hp += 2
            self.player.hp = min(self.player.max_hp, self.player.hp + item.value)
            self.float_texts.append(FloatText(ix, iy, f"🍖 +{item.value} HP, +2 Max", C_GRN, 1.5, 1.5, size=14))
            self._burst(ix, iy, C_GRN, 15, speed=120)
            self.sfx.play('eat')
        elif item.kind == 'bomb':
            self.sfx.play('bomb'); self._shake(10)
            for e in self.enemies:
                if not e.dead and (e.x, e.y) in self.visible:
                    dmg = 20 + self.player.level * 2
                    e.hp -= dmg
                    e.flash = 1.0
                    self._burst(e.x*TILE+TILE//2, e.y*TILE+TILE//2, C_ACC, 15, speed=200)
                    self.float_texts.append(FloatText(e.x*TILE+TILE//2, e.y*TILE-10, f"💥{dmg}", C_ACC, 0.8, 0.8, size=16))
                    if e.hp <= 0:
                        e.dead = True
                        self._on_kill(self.player, e)
        elif item.kind == 'tome':
            self.player.xp += item.value
            self.float_texts.append(FloatText(ix, iy, f"📖 +{item.value} XP", C_XP, 1.5, 1.5, size=16))
            self._burst(ix, iy, C_XP, 20, speed=150)
            self.sfx.play('reveal')
            if self.player.xp >= self.player.xp_next:
                self._level_up()
        elif item.kind == 'broom':
            stairs_pos = next((pos for pos, t in self.dungeon.specials.items() if t == T_STAIRS), None)
            if stairs_pos:
                self._burst(self.player.x*TILE+TILE//2, self.player.y*TILE+TILE//2, C_PURPLE, 20, speed=200)
                self.player.x, self.player.y = stairs_pos
                self.player.render_x, self.player.render_y = stairs_pos
                self._burst(stairs_pos[0]*TILE+TILE//2, stairs_pos[1]*TILE+TILE//2, C_PURPLE, 20, speed=200)
                self.float_texts.append(FloatText(stairs_pos[0]*TILE+TILE//2, stairs_pos[1]*TILE, "🧹 Zoom!", C_PURPLE, 1.2, 1.2, size=16))
                self.sfx.play('teleport')
        elif item.kind == 'amulet':
            self.player.status.clear()
            self.float_texts.append(FloatText(ix, iy, "🧿 Cleansed!", C_CYAN, 1.5, 1.5, size=16))
            self._burst(ix, iy, C_CYAN, 25, speed=140)
            self.sfx.play('altar')
        elif item.kind == 'cat':
            if not self.familiar:
                self.familiar = Entity(x=self.player.x, y=self.player.y, emoji="🐱", name="Cat", hp=1, max_hp=1, atk=3, defense=0)
                self.familiar.render_x, self.familiar.render_y = self.player.x, self.player.y
                self.float_texts.append(FloatText(ix, iy, "🐱 Meow!", C_TXT, 1.5, 1.5, size=18))
                self._burst(ix, iy, C_WHITE, 20, speed=120)
                self.sfx.play('pickup')
        elif item.kind == 'laptop':
            for y in range(GRID_H):
                for x in range(GRID_W):
                    if self.dungeon.grid[y][x] != T_WALL or (x,y) in self.dungeon.specials:
                        self.explored.add((x, y))
            self.player.xp += 50
            self.float_texts.append(FloatText(ix, iy, "💻 Hacked! +50 XP", C_CYAN, 1.5, 1.5, size=16))
            self._burst(ix, iy, C_CYAN, 25, speed=150)
            self.sfx.play('reveal')
            if self.player.xp >= self.player.xp_next:
                self._level_up()
        elif item.kind == 'keyboard':
            self.player.bonus_atk += item.value
            self.player.ranged = True
            self.player.weapon_emoji = "⌨️"
            self.float_texts.append(FloatText(ix, iy, f"⌨️ +{item.value} ATK, Ranged!", C_CYAN, 1.5, 1.5, size=14))
            self._burst(ix, iy, C_CYAN, 15, speed=130)
            self.sfx.play('pickup')
        elif item.kind == 'weapon_axe':
            self.player.bonus_atk = max(self.player.bonus_atk, item.value)
            self.player.weapon_emoji = "🪓"
            self.float_texts.append(FloatText(ix, iy, f"🪓 +{item.value} ATK", C_ACC, 1.5, 1.5, size=16))
            self._burst(ix, iy, C_ACC, 15, speed=130)
            self.sfx.play('pickup')
        elif item.kind == 'weapon_spear':
            self.player.bonus_atk = max(self.player.bonus_atk, item.value)
            self.player.bonus_def = max(self.player.bonus_def, 1)
            self.player.weapon_emoji = "🔱"
            self.float_texts.append(FloatText(ix, iy, f"🔱 +{item.value} ATK, +1 DEF", C_CYAN, 1.5, 1.5, size=14))
            self._burst(ix, iy, C_CYAN, 15, speed=130)
            self.sfx.play('pickup')
        elif item.kind == 'weapon_staff':
            self.player.bonus_atk = max(self.player.bonus_atk, item.value)
            self.player.vision_bonus += 1
            self.player.weapon_emoji = "🪄"
            self.float_texts.append(FloatText(ix, iy, f"🪄 +{item.value} ATK, +1 Vis", C_PURPLE, 1.5, 1.5, size=14))
            self._burst(ix, iy, C_PURPLE, 15, speed=130)
            self.sfx.play('pickup')
        elif item.kind == 'gold':
            gold_gain = int(item.value * self.player.gold_bonus)
            self.player.gold += gold_gain
            self.total_gold += gold_gain
            self.float_texts.append(FloatText(ix, iy, f"💰 +{gold_gain}", C_GOLD, 1.2, 1.2, size=18))
            self._burst(ix, iy, C_GOLD, 12, speed=120)
            hud_x = SCREEN_W - 140; hud_y = SCREEN_H - 90
            for _ in range(3):
                self.particles.append(Particle(ix, iy, random.uniform(-50,50), random.uniform(-100,-50), 1.5, 1.5, C_GOLD, 5, gravity=100, target_hud=(hud_x, hud_y)))
            self.sfx.play('gold')
        elif item.kind == 'gem':
            gold_gain = int(item.value * self.player.gold_bonus)
            self.player.gold += gold_gain
            self.total_gold += gold_gain
            self.float_texts.append(FloatText(ix, iy, f"💎 +{gold_gain}", C_CYAN, 1.5, 1.5, size=20))
            self._burst(ix, iy, C_CYAN, 20, speed=150)
            self._burst(ix, iy, C_WHITE, 8, speed=100)
            hud_x = SCREEN_W - 140; hud_y = SCREEN_H - 90
            for _ in range(5):
                self.particles.append(Particle(ix, iy, random.uniform(-70,70), random.uniform(-120,-60), 1.8, 1.8, C_CYAN, 6, gravity=100, target_hud=(hud_x, hud_y)))
            self.sfx.play('gem')
            
        elif item.kind == 'apple':
            heal = min(item.value, self.player.max_hp - self.player.hp)
            self.player.hp += heal
            self.float_texts.append(FloatText(ix, iy, f"🍎 +{heal}", C_HP, 1.2, 1.2, size=18))
            self._burst(ix, iy, C_HP, 8, speed=80)
            self.sfx.play('pickup')
        elif item.kind == 'cheese':
            self.player.max_hp += 1
            heal = min(item.value, self.player.max_hp - self.player.hp)
            self.player.hp += heal
            self.float_texts.append(FloatText(ix, iy, f"🧀 +{heal} HP, +1 Max", C_GRN, 1.5, 1.5, size=14))
            self._burst(ix, iy, C_GRN, 10, speed=100)
            self.sfx.play('eat')
        elif item.kind == 'cake':
            heal = min(item.value, self.player.max_hp - self.player.hp)
            self.player.hp += heal
            self.float_texts.append(FloatText(ix, iy, f"🎂 +{heal}", C_HP, 1.5, 1.5, size=20))
            self._burst(ix, iy, C_HP, 15, speed=120)
            self.sfx.play('pickup')
        elif item.kind == 'shield':
            self.player.bonus_def += item.value
            self.float_texts.append(FloatText(ix, iy, f"🛡️ +{item.value} DEF", C_BLU, 1.5, 1.5, size=16))
            self._burst(ix, iy, C_BLU, 15, speed=130)
            self.sfx.play('pickup')
        elif item.kind == 'bow':
            self.player.bonus_atk += item.value
            self.player.ranged = True
            self.player.weapon_emoji = "🏹"
            self.float_texts.append(FloatText(ix, iy, f"🏹 +{item.value} ATK, Ranged!", C_ACC, 1.5, 1.5, size=14))
            self._burst(ix, iy, C_ACC, 15, speed=130)
            self.sfx.play('pickup')
        elif item.kind == 'gun':
            self.player.bonus_atk += item.value
            self.player.ranged = True
            self.player.weapon_emoji = "🔫"
            self.float_texts.append(FloatText(ix, iy, f"🔫 +{item.value} ATK, Ranged!", C_ACC, 1.5, 1.5, size=14))
            self._burst(ix, iy, C_ACC, 20, speed=150)
            self.sfx.play('pickup')
        elif item.kind == 'crown':
            self.player.gold_bonus += 0.5
            self.float_texts.append(FloatText(ix, iy, "👑 +50% Gold!", C_GOLD, 1.5, 1.5, size=16))
            self._burst(ix, iy, C_GOLD, 25, speed=140)
            self.sfx.play('gold')
        elif item.kind == 'glasses':
            self.player.vision_bonus += item.value
            self.float_texts.append(FloatText(ix, iy, f"👓 +{item.value} Vision", C_CYAN, 1.5, 1.5, size=16))
            self._burst(ix, iy, C_CYAN, 15, speed=130)
            self.sfx.play('pickup')
        elif item.kind == 'ring':
            self.player.bonus_atk += item.value
            self.player.bonus_def += item.value
            self.float_texts.append(FloatText(ix, iy, f"💍 +{item.value} ATK, +{item.value} DEF", C_PURPLE, 1.5, 1.5, size=14))
            self._burst(ix, iy, C_PURPLE, 15, speed=130)
            self.sfx.play('pickup')
        elif item.kind == 'magnet':
            gold_gain = self.floor * 20
            self.player.gold += gold_gain
            self.total_gold += gold_gain
            self.float_texts.append(FloatText(ix, iy, f"🧲 +{gold_gain} Gold!", C_GOLD, 1.5, 1.5, size=18))
            self._burst(ix, iy, C_GOLD, 20, speed=150)
            self.sfx.play('gem')
        elif item.kind == 'hourglass':
            for e in self.enemies:
                if not e.dead and (e.x, e.y) in self.visible:
                    e.frozen = 3
            self.float_texts.append(FloatText(ix, iy, "⏳ Enemies Frozen!", C_ICE, 1.8, 1.8, size=16))
            self._burst(ix, iy, C_ICE, 30, speed=140)
            self.sfx.play('freeze')
        elif item.kind == 'bell':
            for y in range(GRID_H):
                for x in range(GRID_W):
                    if self.dungeon.grid[y][x] != T_WALL or (x,y) in self.dungeon.specials:
                        self.explored.add((x, y))
            self.float_texts.append(FloatText(ix, iy, "🔔 Map Revealed!", C_CYAN, 1.5, 1.5, size=16))
            self._burst(ix, iy, C_CYAN, 25, speed=140)
            self.sfx.play('reveal')
        elif item.kind == 'telescope':
            self.player.vision_bonus += item.value
            self.float_texts.append(FloatText(ix, iy, f"🔭 +{item.value} Vision", C_CYAN, 1.5, 1.5, size=16))
            self._burst(ix, iy, C_CYAN, 15, speed=130)
            self.sfx.play('pickup')
        elif item.kind == 'joystick':
            self.player.xp += item.value
            self.float_texts.append(FloatText(ix, iy, f"🕹️ +{item.value} XP", C_XP, 1.5, 1.5, size=16))
            self._burst(ix, iy, C_XP, 20, speed=150)
            self.sfx.play('pickup')
            if self.player.xp >= self.player.xp_next:
                self._level_up()

        elif item.kind == 'potion_rage':
            self.player.buffs.append(Buff("rage", 5, 0))
            self.float_texts.append(FloatText(ix, iy, "😡 +50% DMG!", C_RED, 1.5, 1.5, size=16))
            self._burst(ix, iy, C_RED, 15, speed=130)
            self.sfx.play('pickup')
        elif item.kind == 'potion_haste':
            self.player.buffs.append(Buff("haste", 5, 0))
            self.float_texts.append(FloatText(ix, iy, "💨 Haste!", C_GRN, 1.5, 1.5, size=16))
            self._burst(ix, iy, C_GRN, 15, speed=130)
            self.sfx.play('pickup')
        elif item.kind == 'potion_shield':
            self.player.shield += item.value
            self.float_texts.append(FloatText(ix, iy, f"🛡️ +{item.value} Shield", C_BLU, 1.5, 1.5, size=16))
            self._burst(ix, iy, C_BLU, 15, speed=130)
            self.sfx.play('pickup')
        elif item.kind == 'scroll_earthquake':
            self.sfx.play('bomb'); self._shake(12)
            for e in self.enemies:
                if not e.dead and (e.x, e.y) in self.visible:
                    dmg = 30 + self.player.level * 3
                    e.hp -= dmg
                    e.flash = 1.0
                    e.frozen = max(e.frozen, 2)
                    self._burst(e.x*TILE+TILE//2, e.y*TILE+TILE//2, C_ACC, 20, speed=200)
                    self.float_texts.append(FloatText(e.x*TILE+TILE//2, e.y*TILE-10, f"🌍{dmg}", C_ACC, 0.8, 0.8, size=16))
                    if e.hp <= 0:
                        e.dead = True
                        self._on_kill(self.player, e)

    def _check_specials(self):
        px, py = self.player.x, self.player.y
        tile = self.dungeon.tile_at(px, py)
        cx = px * TILE + TILE // 2; cy = py * TILE + TILE // 2
        if tile == T_STAIRS:
            pass
        elif tile == T_CHEST:
            del self.dungeon.specials[(px, py)]
            loot = random.choice(['gold', 'gem', 'potion_hp', 'potion_str', 'potion_def', 'food', 'tome', 'bomb', 'amulet', 'cat', 'laptop', 'keyboard',
                                   'apple', 'cheese', 'cake', 'shield', 'bow', 'gun', 'crown', 'glasses', 'ring', 'magnet', 'hourglass', 'bell', 'telescope', 'joystick',
                                   'potion_rage', 'potion_haste', 'potion_shield', 'scroll_earthquake'])
            fake = GameItem(px, py, loot, ITEM_DEFS[loot][0],
                            {'gold': random.randint(20,50), 'gem': 60,
                             'potion_hp': 20, 'potion_str': 2, 'potion_def': 1,
                             'food': 10, 'tome': 30, 'bomb': 0, 'amulet': 0,
                             'cat': 0, 'laptop': 0, 'keyboard': 3,
                             'apple': 5, 'cheese': 8, 'cake': 30, 'shield': 2, 'bow': 2, 'gun': 4, 'glasses': 1, 'ring': 1,
                             'magnet': 0, 'hourglass': 0, 'bell': 0, 'telescope': 2, 'joystick': 30,
                             'potion_rage': 5, 'potion_haste': 5, 'potion_shield': 20, 'scroll_earthquake': 0}.get(loot, 0),
                            ITEM_DEFS[loot][1])
            self._burst(cx, cy, C_GOLD, 20, speed=150)
            self.sfx.play('chest')
            self._apply_item(fake)
            self.float_texts.append(FloatText(cx, cy - 15, "📦 Opened!", C_GOLD, 1.0, 1.0, size=14))
        elif tile == T_ALTAR:
            del self.dungeon.specials[(px, py)]
            buff = random.choice(['hp', 'atk', 'def'])
            if buff == 'hp':
                self.player.max_hp += 5; self.player.hp += 5
                self.float_texts.append(FloatText(cx, cy, "⛩️ +5 Max HP", C_HP, 1.5, 1.5, size=16))
            elif buff == 'atk':
                self.player.atk += 1
                self.float_texts.append(FloatText(cx, cy, "⛩️ +1 ATK", C_ACC, 1.5, 1.5, size=16))
            else:
                self.player.defense += 1
                self.float_texts.append(FloatText(cx, cy, "⛩️ +1 DEF", C_BLU, 1.5, 1.5, size=16))
            self._burst(cx, cy, C_PURPLE, 25, speed=140)
            self.sfx.play('altar')
        elif tile == T_FOUNTAIN:
            del self.dungeon.specials[(px, py)]
            self.player.hp = self.player.max_hp
            self.float_texts.append(FloatText(cx, cy, "⛲ Full Heal!", C_GRN, 1.5, 1.5, size=18))
            self._burst(cx, cy, C_CYAN, 30, speed=120)
            self.sfx.play('fountain')
        elif tile == T_GRAVE:
            if random.random() < 0.5:
                e = next(en for en in ENEMIES if en[0] == "Zombie")
                enemy = Entity(x=px, y=py, emoji=e[1], name=e[0], hp=e[2], max_hp=e[2], atk=e[3], defense=e[4], xp_reward=e[5], gold_reward=e[6])
                enemy.render_x, enemy.render_y = px, py
                self.enemies.append(enemy)
                self.float_texts.append(FloatText(cx, cy, "🧟 Risen!", C_POISON, 1.2, 1.2, size=16))
                self._burst(cx, cy, C_POISON, 20, speed=120)
                self.sfx.play('grave')
            else:
                self.float_texts.append(FloatText(cx, cy, "🪦 Empty...", C_TXT_D, 1.0, 1.0, size=14))
            del self.dungeon.specials[(px, py)]
        elif tile == T_TRAP:
            del self.dungeon.specials[(px, py)]
            dmg = random.randint(3, 6) + self.floor
            self.player.hp -= dmg
            self.player.flash = 1.0
            self.float_texts.append(FloatText(cx, cy - 10, f"🪤 -{dmg}", C_RED, 1.2, 1.2, size=18))
            self._burst(cx, cy, C_RED, 15, speed=130)
            self.sfx.play('trap')
            self._shake(7); self.hit_stop = 0.05
            if self.player.hp <= 0:
                self._player_death()
                
        elif tile == T_MUSHROOM:
            del self.dungeon.specials[(px, py)]
            heal = 2
            self.player.hp = min(self.player.max_hp, self.player.hp + heal)
            self.float_texts.append(FloatText(cx, cy, f"🍄 +{heal} HP", C_GRN, 1.0, 1.0, size=14))
            self.sfx.play('pickup')
        elif tile == T_PORTAL:
            for _ in range(100):
                r = random.choice(self.dungeon.rooms)
                tx = random.randint(r[0], r[0]+r[2]-1)
                ty = random.randint(r[1], r[1]+r[3]-1)
                if self.dungeon.walkable(tx, ty) and not any(e.x == tx and e.y == ty for e in self.enemies if not e.dead):
                    self._burst(cx, cy, C_PURPLE, 20, speed=200)
                    self.player.x, self.player.y = tx, ty
                    self.player.render_x, self.player.render_y = tx, ty
                    self._burst(tx*TILE+TILE//2, ty*TILE+TILE//2, C_PURPLE, 20, speed=200)
                    self.float_texts.append(FloatText(tx*TILE+TILE//2, ty*TILE, "🌀 Teleport!", C_PURPLE, 1.2, 1.2, size=16))
                    self.sfx.play('teleport')
                    break

    def _descend(self):
        if self.state != State.PLAYING: return
        tile = self.dungeon.tile_at(self.player.x, self.player.y)
        if tile != T_STAIRS:
            self.msg = "Stand on 🪜 to descend!"; self.msg_t = 2.0
            return
        self.floor += 1
        self.sfx.play('stairs')
        if self.floor > MAX_FLOOR:
            self.state = State.VICTORY; self.victory_t = 0.0
            self.sfx.play('victory')
            return
        self._enter_floor()
        self.state = State.FLOOR_MSG
        self.floor_msg_t = 0.0

    def _end_player_turn(self):
        self.turn_count += 1
        
        for st in self.player.status[:]:
            if st.damage > 0:
                self.player.hp -= st.damage
                px = self.player.x * TILE + TILE // 2
                py = self.player.y * TILE + TILE // 2
                color = {"poison":C_POISON, "burn":C_ACC, "freeze":C_ICE, "shock":C_SHOCK, "bleed":C_BLEED}.get(st.kind, C_TXT)
                self.float_texts.append(FloatText(px, py - 10, f"-{st.damage}", color, 0.6, 0.6, vy=-30, size=14))
                self._burst(px, py, color, 5, speed=60)
            st.duration -= 1
            if st.duration <= 0:
                self.player.status.remove(st)
            if self.player.hp <= 0:
                self._player_death(); return
                
        if self.player.regen > 0 and self.player.hp < self.player.max_hp:
            self.player.hp = min(self.player.max_hp, self.player.hp + self.player.regen)
            
        tile = self.dungeon.tile_at(self.player.x, self.player.y)
        if tile == T_LAVA:
            self.player.hp -= 5
            self.float_texts.append(FloatText(self.player.x * TILE + TILE//2, self.player.y * TILE - 10, "-5 🔥", C_ACC, 0.8, 0.8, vy=-30, size=16))
            self.sfx.play('burn')
            if self.player.hp <= 0:
                self._player_death(); return

        for b in self.player.buffs[:]:
            b.duration -= 1
            if b.duration <= 0:
                self.player.buffs.remove(b)
                
        if self.familiar:
            closest = None
            min_dist = 999
            for e in self.enemies:
                if not e.dead:
                    d = abs(e.x - self.familiar.x) + abs(e.y - self.familiar.y)
                    if d < min_dist:
                        min_dist = d
                        closest = e
            if closest and min_dist <= 5:
                if min_dist <= 1:
                    self._familiar_attack(closest)
                else:
                    blocked = {(en.x, en.y) for en in self.enemies if not en.dead}
                    nxt = get_path(self.dungeon, (self.familiar.x, self.familiar.y), (closest.x, closest.y), blocked)
                    if nxt:
                        self.familiar.x, self.familiar.y = nxt
            elif abs(self.familiar.x - self.player.x) + abs(self.familiar.y - self.player.y) > 1:
                blocked = {(en.x, en.y) for en in self.enemies if not en.dead}
                nxt = get_path(self.dungeon, (self.familiar.x, self.familiar.y), (self.player.x, self.player.y), blocked)
                if nxt:
                    self.familiar.x, self.familiar.y = nxt
                    
        is_haste = any(b.kind == "haste" for b in self.player.buffs)
        
        for e in self.enemies:
            if e.dead: continue
            if e.frozen > 0:
                e.frozen -= 1
                continue
            if e.stunned > 0:
                e.stunned -= 1
                continue
                
            for st in e.status[:]:
                if st.damage > 0:
                    e.hp -= st.damage
                    e.flash = 0.5
                    px = e.x * TILE + TILE // 2
                    py = e.y * TILE + TILE // 2
                    color = {"poison":C_POISON, "burn":C_ACC, "freeze":C_ICE, "shock":C_SHOCK, "bleed":C_BLEED}.get(st.kind, C_TXT)
                    self.float_texts.append(FloatText(px, py - 10, f"-{st.damage}", color, 0.6, 0.6, vy=-30, size=14))
                st.duration -= 1
                if st.duration <= 0:
                    e.status.remove(st)
                    
            if e.hp <= 0:
                e.dead = True
                self._on_kill(self.player, e)
                continue
                    
            if self.dungeon.tile_at(e.x, e.y) == T_LAVA and "lava" not in e.biomes:
                e.hp -= 5
                e.flash = 1.0
                self.float_texts.append(FloatText(e.x * TILE + TILE//2, e.y * TILE - 10, "-5 🔥", C_ACC, 0.6, 0.6, vy=-30, size=14))
                if e.hp <= 0:
                    e.dead = True
                    self._on_kill(self.player, e)
                    continue
                    
            if is_haste and random.random() < 0.5:
                continue
                
            self._enemy_turn(e)
            if self.player.hp <= 0:
                self._player_death(); return
                
        self.enemies = [e for e in self.enemies if not e.dead]
        self.visible = compute_fov(self.dungeon, self.player.x, self.player.y, VISION_R + self.player.vision_bonus)
        self.explored |= self.visible
        self.turn_anim = self.turn_anim_max

    def _enemy_can_move(self, nx, ny, enemy, can_phase=False):
        if not (0 <= nx < GRID_W and 0 <= ny < GRID_H): return False
        if self.dungeon.grid[ny][nx] == T_WALL: return False
        if (nx, ny) == (self.player.x, self.player.y): return False 
        if any(o.x==nx and o.y==ny for o in self.enemies if o is not enemy and not o.dead): return False
        
        t = self.dungeon.tile_at(nx, ny)
        if t in (T_WATER, T_TREE, T_WALL_TEMP, T_CRYSTAL):
            return False
        return True

    def _enemy_turn(self, enemy):
        dx = self.player.x - enemy.x; dy = self.player.y - enemy.y
        dist = abs(dx) + abs(dy)
        biome = self.dungeon.biome
        
        if enemy.is_boss:
            self._boss_ai_turn(enemy)
            return

        if "lava" in enemy.biomes and biome == "lava":
            if 3 < dist <= 6:
                blocked = {(e.x, e.y) for e in self.enemies if e is not enemy and not e.dead}
                nxt = get_path(self.dungeon, (enemy.x, enemy.y), (self.player.x, self.player.y), blocked)
                if nxt and self._enemy_can_move(nxt[0], nxt[1], enemy):
                    enemy.x, enemy.y = nxt
                    nxt2 = get_path(self.dungeon, (enemy.x, enemy.y), (self.player.x, self.player.y), blocked)
                    if nxt2 and self._enemy_can_move(nxt2[0], nxt2[1], enemy):
                        if nxt2 != (self.player.x, self.player.y):
                            enemy.x, enemy.y = nxt2
                    return 

        if "frozen" in enemy.biomes and biome == "frozen":
            if random.random() < 0.25:
                return

        if "overgrown" in enemy.biomes and biome == "overgrown":
            if random.random() < 0.35:
                dirs = [(0,1), (0,-1), (1,0), (-1,0)]
                random.shuffle(dirs)
                for mx, my in dirs:
                    if self._enemy_can_move(enemy.x+mx, enemy.y+my, enemy):
                        enemy.x += mx; enemy.y += my
                        return

        can_phase = "crystal" in enemy.biomes and biome == "crystal"

        if enemy.hp < enemy.max_hp * 0.3 and random.random() < 0.7:
            mx = -1 if dx > 0 else (1 if dx < 0 else 0)
            my = -1 if dy > 0 else (1 if dy < 0 else 0)
            moves = [(mx, 0), (0, my)]
            for mx, my in moves:
                nx, ny = enemy.x+mx, enemy.y+my
                if self._enemy_can_move(nx, ny, enemy, can_phase):
                    enemy.x, enemy.y = nx, ny
                    return
                    
        if enemy.ranged and 2 <= dist <= 6:
            if has_los(self.dungeon, enemy.x, enemy.y, self.player.x, self.player.y):
                atk_emoji = "✨"
                self._ranged_attack(enemy, self.player, atk_emoji, enemy.atk, enemy.status_kind)
                return
                
        if dist == 1:
            edx = 1 if dx > 0 else (-1 if dx < 0 else 0)
            edy = 1 if dy > 0 else (-1 if dy < 0 else 0)
            self._melee_attack(enemy, self.player, edx, edy)
            return
            
        if dist > 8: return
        
        blocked = {(e.x, e.y) for e in self.enemies if e is not enemy and not e.dead}
        
        if can_phase:
            nx = enemy.x + (1 if dx > 0 else (-1 if dx < 0 else 0))
            ny = enemy.y + (1 if dy > 0 else (-1 if dy < 0 else 0))
            if dx != 0 and self._enemy_can_move(enemy.x + (1 if dx>0 else -1), enemy.y, enemy, True):
                enemy.x += (1 if dx>0 else -1); return
            if dy != 0 and self._enemy_can_move(enemy.x, enemy.y + (1 if dy>0 else -1), enemy, True):
                enemy.y += (1 if dy>0 else -1); return
        else:
            nxt = get_path(self.dungeon, (enemy.x, enemy.y), (self.player.x, self.player.y), blocked)
            if nxt:
                enemy.x, enemy.y = nxt

    def _boss_ai_turn(self, boss):
        self.boss_dstar.start = (boss.x, boss.y)
        
        boss.ai_state = "MCTS"
        self.float_texts.append(FloatText(boss.x*TILE+TILE//2, boss.y*TILE-15, "🤔 MCTS", C_CYAN, 0.5, 0.5, vy=-20, size=12))
        self.sfx.play('ai_think')
        
        walls = frozenset(k for k, v in self.dungeon.specials.items() if v == T_WALL_TEMP)
        sim_state = (boss.x, boss.y, self.player.x, self.player.y, boss.hp, self.player.hp, walls)
        best_action = mcts_search(sim_state, iterations=50)
        
        proj_emoji = {
            "Dev AI": "💾", 
            "Swamp King": "🦠", 
            "Frost Monarch": "🧊", 
            "Crystal Titan": "🔮", 
            "Inferno Drake": "🔥"
        }.get(boss.name, "💾")
        
        if best_action:
            act, dx, dy = best_action
            if act == "ranged":
                boss.ai_state = "RANGED"
                self._ranged_attack(boss, self.player, proj_emoji, boss.atk, boss.status_kind)
                return
            elif act == "wall":
                boss.ai_state = "BUILD"
                wx = boss.x + (1 if self.player.x > boss.x else (-1 if self.player.x < boss.x else 0))
                wy = boss.y + (1 if self.player.y > boss.y else (-1 if self.player.y < boss.y else 0))
                if self.dungeon.walkable(wx, wy):
                    self.dungeon.specials[(wx, wy)] = T_WALL_TEMP
                    self.float_texts.append(FloatText(wx*TILE+TILE//2, wy*TILE, "🧱 Wall!", C_HUD_LN, 1.0, 1.0, size=16))
                    self._burst(wx*TILE+TILE//2, wy*TILE+TILE//2, C_HUD_LN, 15)
                    self.sfx.play('ai_build')
                    self._shake(4)
                    self.boss_dstar = DStarLite(self, (boss.x, boss.y), (self.player.x, self.player.y))
            elif act == "summon":
                boss.ai_state = "SUMMON"
                self.float_texts.append(FloatText(boss.x*TILE+TILE//2, boss.y*TILE-15, "🤖 Summon!", C_PURPLE, 1.0, 1.0, vy=-30, size=14))
                self.sfx.play('ai_build')
                self._burst(boss.x*TILE+TILE//2, boss.y*TILE+TILE//2, C_PURPLE, 25)
                
                occupied = {(e.x, e.y) for e in self.enemies if not e.dead}
                occupied.add((boss.x, boss.y))
                occupied.add((self.player.x, self.player.y))
                
                for _ in range(2):
                    pos = self.dungeon.rand_pos(avoid=occupied)
                    if pos:
                        e = next(en for en in ENEMIES if en[0] == "Virus")
                        hp_scale = 1.0 + (self.floor - e[7]) * 0.15
                        hp = int(e[2] * hp_scale)
                        atk = int(e[3] * (1.0 + (self.floor - e[7]) * 0.1))
                        minion = Entity(x=pos[0], y=pos[1], emoji=e[1], name=e[0], hp=hp, max_hp=hp, atk=atk, defense=e[4], xp_reward=e[5], gold_reward=e[6], status_kind=e[9], ranged=e[10], is_boss=False, biomes=e[12])
                        minion.render_x, minion.render_y = pos[0], pos[1]
                        self.enemies.append(minion)
                        self._burst(pos[0]*TILE+TILE//2, pos[1]*TILE+TILE//2, C_POISON, 15)
                        occupied.add(pos)
            elif act == "move":
                boss.ai_state = "D* MOVE"
                self.boss_dstar.goal = (self.player.x, self.player.y)
                nxt = self.boss_dstar.get_next_step()
                if nxt and self.dungeon.walkable(nxt[0], nxt[1]):
                    if nxt == (self.player.x, self.player.y):
                        self._melee_attack(boss, self.player, 1 if nxt[0]>boss.x else -1, 1 if nxt[1]>boss.y else -1)
                    else:
                        boss.x, boss.y = nxt
                boss.ai_path = []
                curr = (boss.x, boss.y)
                while curr != (self.player.x, self.player.y):
                    self.boss_dstar.start = curr
                    nxt = self.boss_dstar.get_next_step()
                    if not nxt: break
                    boss.ai_path.append(nxt)
                    curr = nxt
                    if len(boss.ai_path) > 20: break

    def _player_death(self):
        self.player.dead = True
        self.state = State.GAME_OVER
        self.game_over_t = 0.0
        self.sfx.play('death')
        px = self.player.x * TILE + TILE // 2
        py = self.player.y * TILE + TILE // 2
        self._burst(px, py, C_RED, 40, speed=250)
        self._shake(12)

    def _burst(self, x, y, color, count, speed=150):
        if self.reduced_motion: count = max(2, count // 3)
        for _ in range(count):
            ang = random.uniform(0, math.tau)
            sp = random.uniform(speed * 0.3, speed)
            life = random.uniform(0.25, 0.5)
            self.particles.append(Particle(x, y, math.cos(ang) * sp, math.sin(ang) * sp, life, life, color, random.uniform(2, 5), gravity=200))

    def _shake(self, amount):
        if self.reduced_motion: return
        self.shake = min(10, self.shake + amount)

    def wait_turn(self):
        if self.state != State.PLAYING: return
        self._end_player_turn()

    def update(self, dt):
        dt *= self.time_scale
        if self.hit_stop > 0:
            self.hit_stop -= dt
            sim_dt = 0
        else:
            sim_dt = dt
        if self.shake > 0:
            self.shake = max(0, self.shake - dt * 40)
            self.shake_x = random.uniform(-1, 1) * self.shake
            self.shake_y = random.uniform(-1, 1) * self.shake
        else:
            self.shake_x = self.shake_y = 0

        for proj in self.projectiles[:]:
            dx = proj.tx - proj.x; dy = proj.ty - proj.y
            dist = math.hypot(dx, dy)
            if dist < 10:
                tx, ty = int(proj.tx / TILE), int(proj.ty / TILE)
                hit = False
                if proj.owner == "player":
                    for e in self.enemies:
                        if not e.dead and e.x == tx and e.y == ty:
                            self._deal_damage(proj.attacker, e, proj.damage, proj.status)
                            hit = True
                            break
                else:
                    if self.player.x == tx and self.player.y == ty:
                        self._deal_damage(proj.attacker, self.player, proj.damage, proj.status)
                        hit = True
                self.projectiles.remove(proj)
            else:
                proj.x += dx / dist * proj.speed * dt
                proj.y += dy / dist * proj.speed * dt

        self.particles = [p for p in self.particles if p.life > 0]
        for p in self.particles:
            p.life -= dt
            if p.target_hud:
                tx, ty = p.target_hud
                dx, dy = tx - p.x, ty - p.y
                dist = math.hypot(dx, dy)
                if dist < 15:
                    p.life = 0
                else:
                    p.vx += dx * 5 * dt
                    p.vy += dy * 5 * dt
                    p.x += p.vx * dt; p.y += p.vy * dt
            else:
                p.x += p.vx * dt; p.y += p.vy * dt
                p.vy += p.gravity * dt
                p.vx *= 0.94; p.vy *= 0.96

        self.float_texts = [f for f in self.float_texts if f.life > 0]
        for f in self.float_texts:
            f.life -= dt
            f.y += f.vy * dt
            f.vy *= 0.93

        if self.turn_anim > 0:
            self.turn_anim -= dt

        all_entities = self.enemies + ([self.player] if self.player else []) + ([self.familiar] if self.familiar else [])
        for e in all_entities:
            if e.dead: continue
            e.render_x += (e.x - e.render_x) * min(1, sim_dt * 18)
            e.render_y += (e.y - e.render_y) * min(1, sim_dt * 18)
            e.sx += (1.0 - e.sx) * min(1, sim_dt * 12)
            e.sy += (1.0 - e.sy) * min(1, sim_dt * 12)
            e.flash = max(0, e.flash - dt * 5)
            e.bob_t += dt
            e.status_t += dt
            if e.lunge_t > 0:
                e.lunge_t -= dt

        for item in self.items:
            item.bob += dt * 3

        for wp in self.weather_particles:
            wp[0] += wp[2] * dt
            wp[1] += wp[3] * dt
            if wp[1] > SCREEN_H:
                wp[0] = random.uniform(0, SCREEN_W)
                wp[1] = -10

        if self.msg_t > 0:
            self.msg_t -= dt
        if self.ai_dev_msg_t > 0:
            self.ai_dev_msg_t -= dt
        if self.state == State.FLOOR_MSG:
            self.floor_msg_t += dt
            if self.floor_msg_t > 1.5:
                self.state = State.PLAYING
        if self.state == State.GAME_OVER:
            self.game_over_t += dt
        if self.state == State.VICTORY:
            self.victory_t += dt
            if self.victory_t < 3 and random.random() < 0.2:
                self._burst(random.randint(100, SCREEN_W-100), random.randint(100, SCREEN_H-200), random.choice([C_GOLD, C_BLU, C_GRN, C_RED, C_PURPLE]), 8, speed=100)
        if self.state == State.CLASS_SELECT:
            self.class_anim_t += dt

    def render(self):
        self.screen.fill(C_BG)
        if self.state == State.CLASS_SELECT:
            self._render_class_select()
        else:
            self._render_game()
        pygame.display.flip()

    def _render_game(self):
        ox = int(self.shake_x); oy = int(self.shake_y)
        for y in range(GRID_H):
            for x in range(GRID_W):
                vis = (x, y) in self.visible
                exp = (x, y) in self.explored
                if not exp: continue
                tile = self.dungeon.tile_at(x, y)
                if tile == T_WALL:
                    ts = self._tg(T_WALL, fog=not vis)
                    self.screen.blit(ts, (x * TILE + ox, y * TILE + oy))
                else:
                    if tile == T_WATER:
                        if self.dungeon.biome == "toxic":
                            col = (40, 80, 30) if vis else (20, 40, 15)
                            wave = (80, 160, 60)
                        elif self.dungeon.biome == "frozen":
                            col = (80, 120, 160) if vis else (40, 60, 80)
                            wave = (150, 200, 255)
                        else:
                            col = (40, 60, 100) if vis else (20, 30, 50)
                            wave = (80, 120, 160)
                        pygame.draw.rect(self.screen, col, (x * TILE + ox, y * TILE + oy, TILE, TILE))
                        if vis:
                            offset = int(math.sin(pygame.time.get_ticks() * 0.003 + x * 0.5) * 2)
                            pygame.draw.rect(self.screen, wave, (x * TILE + ox + 4, y * TILE + oy + TILE//2 + offset, TILE - 8, 2))
                    elif tile == T_TREE:
                        pygame.draw.rect(self.screen, self.dungeon.colors["floor"] if vis else self.dungeon.colors["floor_fog"], (x * TILE + ox, y * TILE + oy, TILE, TILE))
                        if vis: self._blit_emoji("🌳", x * TILE + ox, y * TILE + oy, TILE - 2)
                    elif tile == T_WALL_TEMP:
                        col = (100, 90, 110) if vis else (40, 35, 45)
                        pygame.draw.rect(self.screen, col, (x * TILE + ox, y * TILE + oy, TILE, TILE))
                        pygame.draw.rect(self.screen, (130, 120, 140), (x * TILE + ox+2, y * TILE + oy+2, TILE-4, TILE-4))
                        if vis: self._blit_emoji("🧱", x * TILE + ox, y * TILE + oy, TILE - 2)
                    elif tile == T_LAVA:
                        col = (100, 30, 20) if vis else (50, 15, 10)
                        pygame.draw.rect(self.screen, col, (x * TILE + ox, y * TILE + oy, TILE, TILE))
                        if vis: self._blit_emoji("🌋", x * TILE + ox, y * TILE + oy, TILE - 2)
                    elif tile == T_MUSHROOM:
                        pygame.draw.rect(self.screen, self.dungeon.colors["floor"] if vis else self.dungeon.colors["floor_fog"], (x * TILE + ox, y * TILE + oy, TILE, TILE))
                        if vis: self._blit_emoji("🍄", x * TILE + ox, y * TILE + oy, TILE - 4)
                    elif tile == T_CRYSTAL:
                        col = (60, 50, 80) if vis else (30, 25, 40)
                        pygame.draw.rect(self.screen, col, (x * TILE + ox, y * TILE + oy, TILE, TILE))
                        if vis: self._blit_emoji("🔮", x * TILE + ox, y * TILE + oy, TILE - 4)
                    elif tile == T_FLOWER:
                        pygame.draw.rect(self.screen, self.dungeon.colors["floor"] if vis else self.dungeon.colors["floor_fog"], (x * TILE + ox, y * TILE + oy, TILE, TILE))
                        if vis: self._blit_emoji("🌸", x * TILE + ox, y * TILE + oy, TILE - 6)
                    elif tile == T_PORTAL:
                        pygame.draw.rect(self.screen, self.dungeon.colors["floor"] if vis else self.dungeon.colors["floor_fog"], (x * TILE + ox, y * TILE + oy, TILE, TILE))
                        if vis:
                            self._blit_emoji("🌀", x * TILE + ox, y * TILE + oy, TILE - 2)
                            glow = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
                            pygame.draw.circle(glow, (180, 100, 220, 50), (TILE//2, TILE//2), TILE//2)
                            self.screen.blit(glow, (x * TILE + ox, y * TILE + oy))
                    else:
                        ts = self._tg(T_FLOOR, fog=not vis)
                        self.screen.blit(ts, (x * TILE + ox, y * TILE + oy))
                        
                        if vis and tile == T_STAIRS:
                            self._blit_emoji("🪜", x * TILE + ox, y * TILE + oy, TILE - 6)
                        elif vis and tile == T_CHEST:
                            self._blit_emoji("📦", x * TILE + ox, y * TILE + oy, TILE - 6)
                        elif vis and tile == T_ALTAR:
                            self._blit_emoji("⛩️", x * TILE + ox, y * TILE + oy, TILE - 4)
                        elif vis and tile == T_FOUNTAIN:
                            self._blit_emoji("⛲", x * TILE + ox, y * TILE + oy, TILE - 4)
                        elif exp and tile == T_TRAP:
                            if vis: self._blit_emoji("🪤", x * TILE + ox, y * TILE + oy, TILE - 8)
                        elif vis and tile == T_TORCH:
                            flicker = 0.8 + random.uniform(-0.1, 0.1)
                            es = self._eg("🕯️", TILE - 4)
                            if flicker != 1.0:
                                es = pygame.transform.scale(es, (int(es.get_width()*flicker), int(es.get_height()*flicker)))
                            rect = es.get_rect(center=(x * TILE + ox + TILE // 2, y * TILE + oy + TILE // 2))
                            self.screen.blit(es, rect)
                            glow = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
                            pygame.draw.circle(glow, (255, 200, 100, 40), (TILE//2, TILE//2), TILE//2)
                            self.screen.blit(glow, (x * TILE + ox, y * TILE + oy))
                        elif exp and tile == T_GRAVE:
                            if vis: self._blit_emoji("🪦", x * TILE + ox, y * TILE + oy, TILE - 4)

        if self.state in (State.PLAYING, State.PAUSED, State.FLOOR_MSG):
            for wp in self.weather_particles:
                es = self._eg(wp[4], 16)
                self.screen.blit(es, (int(wp[0]), int(wp[1])))

        for e in self.enemies:
            if e.is_boss and not e.dead and e.ai_path:
                for i, (px, py) in enumerate(e.ai_path):
                    alpha = 1.0 - (i / len(e.ai_path))
                    es = self._eg("·", 24)
                    es.set_alpha(int(150 * alpha))
                    self.screen.blit(es, es.get_rect(center=(px * TILE + TILE//2 + ox, py * TILE + TILE//2 + oy)))

        for item in self.items:
            if (item.x, item.y) not in self.visible: continue
            bob_y = math.sin(item.bob) * 3
            self._blit_emoji(item.emoji, item.x * TILE + ox, item.y * TILE + oy + bob_y, TILE - 6)

        entities = [e for e in self.enemies if not e.dead and (e.x, e.y) in self.visible]
        if self.player and not self.player.dead:
            entities.append(self.player)
        if self.familiar:
            entities.append(self.familiar)
        entities.sort(key=lambda e: e.render_y)
        for e in entities:
            self._render_entity(e, ox, oy)

        for proj in self.projectiles:
            es = self._eg(proj.emoji, 20)
            self.screen.blit(es, es.get_rect(center=(proj.x + ox, proj.y + oy)))

        for p in self.particles:
            alpha = max(0, p.life / p.max_life)
            r = max(1, int(p.size * alpha))
            col = (*p.color, int(255 * alpha))
            ps = pygame.Surface((r*2+2, r*2+2), pygame.SRCALPHA)
            pygame.draw.circle(ps, col, (r+1, r+1), r)
            self.screen.blit(ps, (p.x - r + ox, p.y - r + oy))

        for f in self.float_texts:
            alpha = max(0, min(1, f.life / f.max_life))
            font = self.fonts.ft_font(f.size)
            surf = font.render(f.text, True, f.color)
            surf.set_alpha(int(255 * alpha))
            rect = surf.get_rect(center=(f.x + ox, f.y + oy))
            self.screen.blit(surf, rect)

        self._render_hud()

        if self.state == State.FLOOR_MSG:
            self._render_floor_msg()
        elif self.state == State.PAUSED:
            self._render_pause()
        elif self.state == State.GAME_OVER:
            self._render_game_over()
        elif self.state == State.VICTORY:
            self._render_victory()

        if self.msg and self.msg_t > 0:
            alpha = min(1, self.msg_t / 0.5) if self.msg_t < 0.5 else 1
            surf = self.fonts.med.render(self.msg, True, C_ACC)
            surf.set_alpha(int(255 * alpha))
            rect = surf.get_rect(center=(SCREEN_W // 2, 40))
            self.screen.blit(surf, rect)
            
        if self.ai_dev_msg and self.ai_dev_msg_t > 0:
            alpha = min(1, self.ai_dev_msg_t / 1.0) if self.ai_dev_msg_t < 1.0 else 1
            surf = self.fonts.med.render(self.ai_dev_msg, True, C_CYAN)
            surf.set_alpha(int(255 * alpha))
            rect = surf.get_rect(center=(SCREEN_W // 2, 20))
            self.screen.blit(surf, rect)

        if self.debug:
            self._render_debug()

    def _blit_emoji(self, char, x, y, size=TILE - 6):
        es = self._eg(char, size)
        rect = es.get_rect(center=(x + TILE // 2, y + TILE // 2))
        self.screen.blit(es, rect)

    def _render_entity(self, e, ox, oy):
        rx = e.render_x * TILE + TILE // 2 + ox
        ry = e.render_y * TILE + TILE // 2 + oy
        sh = pygame.Surface((TILE - 8, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 80), sh.get_rect())
        self.screen.blit(sh, (rx - (TILE - 8) // 2, ry + TILE // 2 - 8))
        
        if e.is_elite:
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.008)
            r = int(TILE // 2 + 4 + pulse * 3)
            aura = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
            pygame.draw.circle(aura, (255, 50, 255, int(60 * pulse)), (r, r), r)
            self.screen.blit(aura, (rx - r, ry - r))
            
        if e.status:
            for i, st in enumerate(e.status):
                pulse = 0.5 + 0.5 * math.sin(e.status_t * 6 + i)
                color = {"poison":C_POISON, "burn":C_ACC, "freeze":C_ICE, "shock":C_SHOCK, "bleed":C_BLEED, "stun":C_STUN, "weaken":C_PURPLE, "armor_break":C_ACC}.get(st.kind, C_TXT)
                r = int(TILE // 2 + 4 + pulse * 3)
                aura = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
                pygame.draw.circle(aura, (*color, int(60 * pulse)), (r, r), r)
                self.screen.blit(aura, (rx - r, ry - r))
                
        if e.is_boss:
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.005)
            r = int(TILE // 2 + 6 + pulse * 4)
            aura = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
            pygame.draw.circle(aura, (100, 200, 255, int(40 * pulse)), (r, r), r)
            self.screen.blit(aura, (rx - r, ry - r))
            
        if e.frozen > 0:
            es = self._eg("🧊", TILE - 4)
            self.screen.blit(es, es.get_rect(center=(rx, ry)))

        if e.stunned > 0:
            es = self._eg("💫", TILE - 10)
            self.screen.blit(es, es.get_rect(center=(rx, ry - TILE//2 - 4)))

        bob = math.sin(e.bob_t * 3 + hash(e.name) % 100) * 2
        ry += bob
        
        es = self._eg(e.emoji, TILE - 6)
        ew, eh = es.get_size()
        sw = max(1, int(ew * e.sx)); sh2 = max(1, int(eh * e.sy))
        if sw != ew or sh2 != eh:
            es = pygame.transform.smoothscale(es, (sw, sh2))
        rect = es.get_rect(center=(rx, ry))
        self.screen.blit(es, rect)

        if e.flash > 0:
            fs = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
            fs.fill((255, 255, 255, int(180 * e.flash)))
            self.screen.blit(fs, (rx - TILE // 2, ry - TILE // 2), special_flags=pygame.BLEND_RGB_ADD)

        if e.is_player and e.shield > 0:
            pygame.draw.circle(self.screen, C_BLU, (rx, ry), TILE//2 + 2, 2)

        if not e.is_player and not e.is_boss and e.hp < e.max_hp:
            bw = TILE - 8; bh = 3
            bx = rx - bw // 2; by = ry - TILE // 2 + 2
            pygame.draw.rect(self.screen, C_HP_D, (bx, by, bw, bh))
            pct = max(0, e.hp / e.max_hp)
            pygame.draw.rect(self.screen, C_HP, (bx, by, int(bw * pct), bh))
        elif e.is_boss:
            bw = TILE * 2; bh = 6
            bx = rx - bw // 2; by = ry - TILE // 2 - 5
            pygame.draw.rect(self.screen, C_HP_D, (bx, by, bw, bh))
            pct = max(0, e.hp / e.max_hp)
            pygame.draw.rect(self.screen, C_RED, (bx, by, int(bw * pct), bh))
            pygame.draw.rect(self.screen, C_HUD_LN, (bx, by, bw, bh), 1)

    def _render_minimap(self):
        mx = SCREEN_W - 100
        my = SCREEN_H - HUD_H + 10
        mw = GRID_W * 3
        mh = GRID_H * 3
        pygame.draw.rect(self.screen, (0,0,0), (mx-2, my-2, mw+4, mh+4))
        pygame.draw.rect(self.screen, C_HUD_LN, (mx-2, my-2, mw+4, mh+4), 1)
        for y in range(GRID_H):
            for x in range(GRID_W):
                if (x, y) in self.explored:
                    col = C_HUD_LN
                    tile = self.dungeon.tile_at(x, y)
                    if tile == T_WALL:
                        col = (50, 45, 60)
                    else:
                        col = (90, 85, 100)
                    if (x, y) in self.visible:
                        col = tuple(min(255, c+40) for c in col)
                    pygame.draw.rect(self.screen, col, (mx + x*3, my + y*3, 3, 3))
        if self.player:
            pygame.draw.rect(self.screen, C_CYAN, (mx + self.player.x*3, my + self.player.y*3, 3, 3))
        stairs = next((pos for pos, t in self.dungeon.specials.items() if t == T_STAIRS), None)
        if stairs and stairs in self.explored:
            pygame.draw.rect(self.screen, C_GOLD, (mx + stairs[0]*3, my + stairs[1]*3, 3, 3))

    def _render_hud(self):
        hy = SCREEN_H - HUD_H
        pygame.draw.rect(self.screen, C_HUD, (0, hy, SCREEN_W, HUD_H))
        pygame.draw.line(self.screen, C_HUD_LN, (0, hy), (SCREEN_W, hy))
        if not self.player: return
        p = self.player
        x = 16; y = hy + 10
        es = self._eg(p.emoji, 36)
        self.screen.blit(es, (x, y))
        x += 44
        self.screen.blit(self.fonts.hud.render(f"{p.name} Lv.{p.level}", True, C_TXT), (x, y))
        self.screen.blit(self.fonts.sml.render(f"Floor {self.floor}/{MAX_FLOOR}  Kills: {self.kills}  Biome: {self.dungeon.biome.title()} {BIOMES[self.dungeon.biome]['weather']}", True, C_TXT_D), (x, y + 22))
        
        bx = x; by = y + 40; bw = 180; bh = 16
        pygame.draw.rect(self.screen, C_HP_D, (bx, by, bw, bh))
        pct = max(0, p.hp / p.max_hp)
        pygame.draw.rect(self.screen, C_HP, (bx, by, int(bw * pct), bh))
        pygame.draw.rect(self.screen, C_HUD_LN, (bx, by, bw, bh), 1)
        self.screen.blit(self.fonts.sml.render(f"❤️ {p.hp}/{p.max_hp}", True, C_TXT), (bx + 4, by + 1))
        
        if p.shield > 0:
            sh_x = bx + int(bw * pct) + 5
            self.screen.blit(self.fonts.sml.render(f"🛡️ {p.shield}", True, C_BLU), (sh_x, by + 1))
        
        by2 = by + 20
        pygame.draw.rect(self.screen, C_XP_D, (bx, by2, bw, 10))
        xp_pct = p.xp / p.xp_next if p.xp_next > 0 else 0
        pygame.draw.rect(self.screen, C_XP, (bx, by2, int(bw * xp_pct), 10))
        pygame.draw.rect(self.screen, C_HUD_LN, (bx, by2, bw, 10), 1)
        self.screen.blit(self.fonts.sml.render(f"📊 {p.xp}/{p.xp_next}", True, C_TXT_D), (bx + 4, by2 - 1))
        
        rx = SCREEN_W - 330; ry = hy + 14
        stats = [
            (f"⚔️ ATK: {p.atk + p.bonus_atk}", C_ACC),
            (f"🛡️ DEF: {p.defense + p.bonus_def}", C_BLU),
            (f"💰 Gold: {p.gold}", C_GOLD),
        ]
        if p.crit_chance > 0: stats.append((f"🎯 Crit: {int(p.crit_chance*100)}%", C_GOLD))
        if p.regen > 0: stats.append((f"✨ Regen: +{p.regen}", C_GRN))
        if p.riposte > 0: stats.append((f"🤺 Riposte: {int(p.riposte*100)}%", C_CYAN))
        if p.vision_bonus > 0: stats.append((f"👁️ Vision: +{p.vision_bonus}", C_CYAN))
        if p.lifesteal > 0: stats.append((f"🩸 Lifesteal: {int(p.lifesteal*100)}%", C_HP))
        if p.dodge > 0: stats.append((f"🤸 Dodge: {int(p.dodge*100)}%", C_CYAN))
        if p.gold_bonus > 1.0: stats.append((f"👑 Gold: +{int((p.gold_bonus-1)*100)}%", C_GOLD))
        if p.ranged: stats.append((f"🖱️ Ranged", C_CYAN))
        for i, (txt, col) in enumerate(stats):
            self.screen.blit(self.fonts.hud.render(txt, True, col), (rx, ry + i * 20))
            
        sx = 250; sy = hy + 14
        for i, st in enumerate(p.status):
            s_emoji = {"poison":"🟢", "burn":"🔥", "freeze":"🥶", "shock":"⚡", "bleed":"🩸", "stun":"💫", "weaken":"🔻", "armor_break":"🪓"}.get(st.kind, "❓")
            label = st.kind.title()
            s_col = {"poison":C_POISON, "burn":C_ACC, "freeze":C_ICE, "shock":C_SHOCK, "bleed":C_BLEED, "stun":C_STUN, "weaken":C_PURPLE, "armor_break":C_ACC}.get(st.kind, C_TXT)
            es = self._eg(s_emoji, 20)
            self.screen.blit(es, (sx + i * 70, sy))
            self.screen.blit(self.fonts.sml.render(f"{label} {st.duration}t", True, s_col), (sx + 24 + i * 70, sy + 4))
            
        bx2 = sx; by2 = hy + 40
        if p.buffs:
            for i, b in enumerate(p.buffs):
                b_emoji = {"rage": "😡", "haste": "💨"}.get(b.kind, "✨")
                b_col = C_RED if b.kind == "rage" else C_GRN
                es = self._eg(b_emoji, 20)
                self.screen.blit(es, (bx2 + i * 70, by2))
                self.screen.blit(self.fonts.sml.render(f"{b.kind.title()} {b.duration}t", True, b_col), (bx2 + 24 + i * 70, by2 + 4))

        self._render_minimap()
            
        ctrl = "WASD/Arrows: Move  .:Wait  >:Stairs  P:Pause  M:Mute  R:Reduce"
        self.screen.blit(self.fonts.sml.render(ctrl, True, C_TXT_D), (16, SCREEN_H - 18))

    def _render_class_select(self):
        self.screen.fill(C_BG)
        t = self.class_anim_t
        title_y = 40 + math.sin(t * 2) * 3
        title = self.fonts.ttl.render("⚔️ EMOJI ROGUELIKE ⚔️", True, C_GOLD)
        self.screen.blit(title, title.get_rect(center=(SCREEN_W // 2, int(title_y))))
        sub = self.fonts.med.render("Choose your hero: 🦸", True, C_TXT)
        self.screen.blit(sub, sub.get_rect(center=(SCREEN_W // 2, 100)))
        
        card_w = 130; card_h = 190; gap = 8
        total_w = len(CLASSES) * card_w + (len(CLASSES) - 1) * gap
        start_x = (SCREEN_W - total_w) // 2
        for i, (emoji, name, hp, atk, df, desc, _) in enumerate(CLASSES):
            cx = start_x + i * (card_w + gap)
            cy = 150
            is_sel = (i == self.class_idx)
            bob = math.sin(t * 3 + i * 0.5) * 4 if is_sel else 0
            card_rect = pygame.Rect(cx, cy + bob, card_w, card_h)
            bg_col = (40, 35, 55) if is_sel else (22, 20, 32)
            pygame.draw.rect(self.screen, bg_col, card_rect, border_radius=12)
            border_col = C_GOLD if is_sel else C_HUD_LN
            pygame.draw.rect(self.screen, border_col, card_rect, 3, border_radius=12)
            es = self._eg(emoji, 44)
            self.screen.blit(es, es.get_rect(center=(cx + card_w // 2, cy + 45 + bob)))
            nm = self.fonts.med.render(name, True, C_TXT if is_sel else C_TXT_D)
            self.screen.blit(nm, nm.get_rect(center=(cx + card_w // 2, cy + 90 + bob)))
            stats = [(f"❤️ {hp}", C_HP), (f"⚔️ {atk}", C_ACC), (f"🛡️ {df}", C_BLU)]
            for j, (s, c) in enumerate(stats):
                sf = self.fonts.ui.render(s, True, c)
                self.screen.blit(sf, sf.get_rect(center=(cx + card_w // 2, cy + 120 + j * 20 + bob)))
            df2 = self.fonts.sml.render(desc, True, C_TXT_D)
            self.screen.blit(df2, df2.get_rect(center=(cx + card_w // 2, cy + card_h - 15 + bob)))
            
        inst = "← → Select    Space/Enter: Confirm    Esc: Quit"
        ins = self.fonts.med.render(inst, True, C_TXT_D)
        self.screen.blit(ins, ins.get_rect(center=(SCREEN_W // 2, SCREEN_H - 50)))

    def _render_floor_msg(self):
        alpha = min(1, self.floor_msg_t / 0.3)
        if self.floor_msg_t > 1.2:
            alpha = max(0, 1.0 - (self.floor_msg_t - 1.2) / 0.3)
        ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, int(120 * alpha)))
        self.screen.blit(ov, (0, 0))
        
        floor_boss_def = next((e for e in ENEMIES if e[11] and e[7] == self.floor), None)
        if floor_boss_def:
            txt = f"⚠️ FLOOR {self.floor} — {self.dungeon.biome.title()} BOSS: {floor_boss_def[0]} {floor_boss_def[1]}"
            col = C_RED
        else:
            txt = f"🗺️ FLOOR {self.floor} — {self.dungeon.biome.title()} BIOME"
            col = C_TXT
            
        s = self.fonts.ttl.render(txt, True, col)
        s.set_alpha(int(255 * alpha))
        self.screen.blit(s, s.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2)))

    def _render_pause(self):
        ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 160))
        self.screen.blit(ov, (0, 0))
        t = self.fonts.ttl.render("⏸️ PAUSED", True, C_TXT)
        self.screen.blit(t, t.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 30)))
        inst = self.fonts.med.render("P: Resume   Esc: Quit", True, C_TXT_D)
        self.screen.blit(inst, inst.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 30)))

    def _render_game_over(self):
        t = min(1, self.game_over_t / 0.5)
        ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        ov.fill((40, 0, 0, int(180 * t)))
        self.screen.blit(ov, (0, 0))
        scale = 0.5 + 0.5 * min(1, self.game_over_t / 0.4)
        font = self.fonts.ft_font(int(48 * scale))
        txt = font.render("☠️ YOU DIED ☠️", True, C_RED)
        self.screen.blit(txt, txt.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 60)))
        if self.game_over_t > 0.5:
            stats = [f"🏛️ Floor reached: {self.floor}", f"💀 Enemies slain: {self.kills}",
                     f"💰 Gold earned: {self.total_gold}", f"📊 Level: {self.player.level}"]
            for i, s in enumerate(stats):
                sf = self.fonts.med.render(s, True, C_TXT_D)
                self.screen.blit(sf, sf.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + i * 28)))
        if self.game_over_t > 1.5:
            inst = self.fonts.med.render("Space: New Game   Esc: Quit", True, C_ACC)
            self.screen.blit(inst, inst.get_rect(center=(SCREEN_W // 2, SCREEN_H - 60)))

    def _render_victory(self):
        t = min(1, self.victory_t / 0.5)
        ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        ov.fill((0, 20, 40, int(160 * t)))
        self.screen.blit(ov, (0, 0))
        scale = 0.5 + 0.5 * min(1, self.victory_t / 0.4)
        font = self.fonts.ft_font(int(48 * scale))
        txt = font.render("🏆 VICTORY! 🏆", True, C_GOLD)
        self.screen.blit(txt, txt.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 60)))
        if self.victory_t > 0.5:
            stats = [f"🏰 Floors cleared: {MAX_FLOOR}", f"💀 Enemies slain: {self.kills}",
                     f"💰 Gold earned: {self.total_gold}", f"🧝 Class: {self.player.name}"]
            for i, s in enumerate(stats):
                sf = self.fonts.med.render(s, True, C_TXT)
                self.screen.blit(sf, sf.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + i * 28)))
        if self.victory_t > 1.5:
            inst = self.fonts.med.render("Space: New Game   Esc: Quit", True, C_ACC)
            self.screen.blit(inst, inst.get_rect(center=(SCREEN_W // 2, SCREEN_H - 60)))

    def _render_debug(self):
        fps = self.clock.get_fps()
        info = [f"FPS: {fps:.0f} 📊", f"Particles: {len(self.particles)} ✨", f"Projectiles: {len(self.projectiles)} 🎯",
                f"Enemies: {len([e for e in self.enemies if not e.dead])} 👾", f"Turn: {self.turn_count} ⏱️"]
        boss = next((e for e in self.enemies if e.is_boss), None)
        if boss:
            info.append(f"Boss State: {boss.ai_state} 🤖")
            info.append(f"Boss Path Len: {len(boss.ai_path)} 🧭")
        for i, s in enumerate(info):
            self.screen.blit(self.fonts.sml.render(s, True, C_GRN), (SCREEN_W - 180, 10 + i * 16))

    def handle_key(self, key):
        if self.state == State.CLASS_SELECT:
            if key in (pygame.K_LEFT, pygame.K_a):
                self.class_idx = (self.class_idx - 1) % len(CLASSES)
                self.sfx.play('select')
            elif key in (pygame.K_RIGHT, pygame.K_d):
                self.class_idx = (self.class_idx + 1) % len(CLASSES)
                self.sfx.play('select')
            elif key in (pygame.K_SPACE, pygame.K_RETURN):
                self.sfx.play('pickup')
                self.start_game(self.class_idx)
            elif key == pygame.K_ESCAPE:
                pygame.quit(); sys.exit()
            return
        if self.state == State.GAME_OVER or self.state == State.VICTORY:
            if key in (pygame.K_SPACE, pygame.K_RETURN):
                self.reset()
                self.state = State.CLASS_SELECT
            elif key == pygame.K_ESCAPE:
                pygame.quit(); sys.exit()
            return
        if key == pygame.K_p or (key == pygame.K_ESCAPE and self.state == State.PLAYING):
            if self.state == State.PLAYING: self.state = State.PAUSED
            elif self.state == State.PAUSED: self.state = State.PLAYING
            return
        if key == pygame.K_ESCAPE and self.state == State.PAUSED:
            pygame.quit(); sys.exit()
        if key == pygame.K_m: self.sfx.toggle(); return
        if key == pygame.K_r: self.reduced_motion = not self.reduced_motion; return
        if key == pygame.K_F1: self.debug = not self.debug; return
        if key == pygame.K_F2: self.time_scale = 0.2 if self.time_scale == 1.0 else 1.0; return
        if self.state != State.PLAYING: return
        if key in (pygame.K_w, pygame.K_UP):    self.try_move(0, -1)
        elif key in (pygame.K_s, pygame.K_DOWN):  self.try_move(0, 1)
        elif key in (pygame.K_a, pygame.K_LEFT):  self.try_move(-1, 0)
        elif key in (pygame.K_d, pygame.K_RIGHT): self.try_move(1, 0)
        elif key == pygame.K_PERIOD:
            if pygame.key.get_mods() & pygame.KMOD_SHIFT: self._descend()
            else: self.wait_turn()
        elif key == pygame.K_GREATER: self._descend()

# ─── MAIN 🚀 ───────────────────────────────────────────────
def main():
    game = Game()
    running = True
    while running:
        dt = min(game.clock.tick(FPS) / 1000.0, 1 / 30)
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            elif event.type == pygame.KEYDOWN: game.handle_key(event.key)
        game.update(dt)
        game.render()
    pygame.quit()

if __name__ == "__main__":
    main()