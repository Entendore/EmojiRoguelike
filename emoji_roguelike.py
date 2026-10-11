#!/usr/bin/env python3
"""
Emoji Roguelike v3 — Classes, Skills, Progression, 50 enemies, advanced AI, 6 map gen algorithms.
Controls: WASD/Arrows move, 1-4 skills, P potion, SPACE wait, R restart.
"""

import pygame, random, math, sys, heapq
from collections import deque
from PIL import Image, ImageDraw, ImageFont

# ── Constants ────────────────────────────────────────────────────────────────
TILE = 40
MW, MH = 50, 35
SBW = 280
SW = MW * TILE + SBW
SH = MH * TILE
FPS = 30
WALL, FLOOR, DOOR, STAIRS = 0, 1, 2, 3
PILLAR, WATER, LAVA = 4, 5, 6
# Decorative (non-blocking, walkable) tile types
DECO_BONES, DECO_WEB, DECO_CRYSTAL, DECO_MUSHROOM = 7, 8, 9, 10
DECO_GRASS, DECO_ICE, DECO_FLOWERS = 11, 12, 13
WALKABLE = {FLOOR, DOOR, STAIRS, DECO_BONES, DECO_WEB, DECO_CRYSTAL,
             DECO_MUSHROOM, DECO_GRASS, DECO_ICE, DECO_FLOWERS}

EMOJI = {
    "warrior": "\U0001f9cd", "mage": "\U0001f9d9", "rogue": "\U0001f977",
    "cleric": "\u271d\ufe0f",
    "rat": "\U0001f400", "bat": "\U0001f987", "spider": "\U0001f577",
    "snake": "\U0001f40d", "wolf": "\U0001f43a", "goblin": "\U0001f47a",
    "slime": "\U0001f7e2", "skeleton": "\U0001f480", "orc": "\U0001f47d",
    "ghost": "\U0001f47b", "vampire": "\U0001f9db", "demon": "\U0001f479",
    "golem": "\U0001f5ff", "lich": "\u2620\ufe0f", "wraith": "\U0001f441",
    "dragon": "\U0001f409", "kraken": "\U0001f419", "phoenix": "\U0001f525",
    "mimic": "\U0001f4e6",
    # New enemies
    "scorpion": "\U0001f982", "bee": "\U0001f41d", "ant": "\U0001f41c",
    "mosquito": "\U0001f99f", "turtle": "\U0001f422", "crab": "\U0001f980",
    "octopus": "\U0001f419", "shark": "\U0001f988", "whale": "\U0001f40b",
    "crocodile": "\U0001f40a", "tiger": "\U0001f42f", "lion": "\U0001f981",
    "bear": "\U0001f43b", "boar": "\U0001f417", "eagle": "\U0001f985",
    "owl": "\U0001f989", "parrot": "\U0001f99c", "fish": "\U0001f41f",
    "butterfly": "\U0001f98b", "worm": "\U0001fab0", "bug": "\U0001f41b",
    "snail": "\U0001f40c", "frog": "\U0001f438", "monkey": "\U0001f435",
    "gorilla": "\U0001f98d", "elephant": "\U0001f418", "rhino": "\U0001f98f",
    "buffalo": "\U0001f403", "cow": "\U0001f42e", "pig": "\U0001f416",
    "chicken": "\U0001f414", "poodle": "\U0001f429", "microbe": "\U0001f9a0",
    "squid": "\U0001f991", "lobster": "\U0001f99e", "unicorn": "\U0001f984",
    "mermaid": "\U0001f9dc", "troll": "\U0001f9cc", "genie": "\U0001f9de",
    "zombie": "\U0001f9df", "alien": "\U0001f47d", "robot": "\U0001f916",
    "ninja": "\U0001f977", "pirate": "\u2620\ufe0f",
    "sumo": "\U0001f94b", "joker": "\U0001f0cf",
    "scarecrow": "\U0001f9d1",
    # Unique floor-boss emojis
    "boss_warlord": "\U0001f482", "boss_king": "\U0001f451",
    "boss_emperor": "\U0001f3db\ufe0f", "boss_elder": "\U0001f432",
    "boss_overlord": "\U0001f525", "boss_titan": "\U0001f4a5",
    "boss_leviathan": "\U0001f40a", "boss_archlich": "\U0001f9ec",
    "boss_dragon_god": "\U0001f532",
    # Items
    "sword": "\U0001f5e1", "shield": "\U0001f6e1", "potion": "\u2764",
    "gold": "\U0001f48e", "scroll": "\U0001f4dc", "wall": "\u2b1b",
    "floor": None, "door": "\U0001f6aa", "stairs": "\U0001fa9c",
    "boss": "\U0001f451", "star": "\u2b50", "lock": "\U0001f512",
    "fire": "\U0001f525", "snow": "\u2744\ufe0f", "zap": "\u26a1",
    "dagger": "\U0001f5e1", "cross": "\u271d\ufe0f", "skull_warn": "\u26a0\ufe0f",
    "pillar": "\u2b1c", "water": "\U0001f4a7", "lava": "\U0001f525",
    "bones": "\u2620\ufe0f", "mushroom": "\U0001f344", "crystal": "\U0001f48e",
    "web": "\U0001f578", "grass": "\U0001f33f", "ice": "\u2744\ufe0f",
    "tree": "\U0001f333", "flower": "\U0001f33b",
}

C_BG = (18, 18, 28)
C_SB = (28, 28, 42)
C_SBB = (60, 60, 90)
C_TXT = (220, 220, 230)
C_DIM = (130, 130, 150)
C_HP = (200, 50, 50)
C_HPB = (60, 20, 20)
C_XP = (50, 150, 200)
C_XPB = (20, 40, 60)
C_MP = (80, 80, 200)
C_MPB = (25, 25, 60)
C_GOLD = (255, 215, 0)
C_MSG = (180, 180, 190)
C_GOOD = (80, 200, 120)
C_BAD = (220, 70, 70)
C_SPEC = (100, 150, 255)
C_FOG = (10, 10, 18)
C_CD = (80, 80, 100)
C_CD_READY = (80, 200, 120)
C_PERK = (255, 200, 80)
C_SEL = (100, 200, 255)

# Biome color palettes for floor/wall variants
BIOMES = {
    "classic":    {"name": "Stone Crypt",     "floor": (30, 30, 45),  "floor2": (38, 38, 55),  "wall": None},
    "cave":       {"name": "Goblin Caves",    "floor": (28, 32, 25),  "floor2": (35, 40, 30),  "wall": None},
    "cellular":   {"name": "Fungal Caverns",  "floor": (25, 35, 20),  "floor2": (32, 42, 28),  "wall": None},
    "bsp":        {"name": "Ancient Catacombs","floor": (32, 28, 28), "floor2": (40, 35, 35),  "wall": None},
    "maze":       {"name": "Labyrinth",       "floor": (28, 28, 38),  "floor2": (36, 36, 48),  "wall": None},
    "drunkard":   {"name": "Mushroom Den",    "floor": (30, 25, 35),  "floor2": (38, 32, 42),  "wall": None},
}

# ── Class Definitions ────────────────────────────────────────────────────────
CLASS_DEFS = {
    "warrior": {
        "emoji": "warrior", "name": "Warrior",
        "desc": "Tanky melee fighter with powerful",
        "desc2": "strikes and defensive abilities.",
        "hp": 45, "atk": 5, "df": 4, "mp": 10,
        "color": (220, 180, 80),
        "skills": {
            1: {"name": "Power Strike", "emoji": "sword", "cd": 4,
                "desc": "Deal 2x ATK damage",
                "type": "melee_boost", "mult": 2.0},
            3: {"name": "Shield Bash", "emoji": "shield", "cd": 6,
                "desc": "Stun enemy 2 turns + 1.5x dmg",
                "type": "stun", "mult": 1.5, "stun_dur": 2},
            5: {"name": "War Cry", "emoji": "star", "cd": 10,
                "desc": "+3 ATK for 5 turns",
                "type": "buff_atk", "duration": 5, "amount": 3},
            8: {"name": "Berserker", "emoji": "fire", "cd": 15,
                "desc": "3x ATK but -5 DEF for 3 turns",
                "type": "berserk", "duration": 3, "mult": 3.0, "def_pen": 5},
        }
    },
    "mage": {
        "emoji": "mage", "name": "Mage",
        "desc": "Glass cannon with devastating",
        "desc2": "spells and area effects.",
        "hp": 25, "atk": 8, "df": 1, "mp": 30,
        "color": (120, 120, 255),
        "skills": {
            1: {"name": "Fireball", "emoji": "fire", "cd": 3,
                "desc": "AoE 8+lvl*2 damage around you",
                "type": "aoe", "base_dmg": 8, "lvl_mult": 2, "radius": 3},
            3: {"name": "Ice Blast", "emoji": "snow", "cd": 5,
                "desc": "Freeze nearest enemy 3 turns",
                "type": "freeze", "duration": 3, "range": 6},
            5: {"name": "Lightning", "emoji": "zap", "cd": 4,
                "desc": "Hit random visible foe for 3x ATK",
                "type": "lightning", "mult": 3.0},
            8: {"name": "Arcane Nova", "emoji": "star", "cd": 12,
                "desc": "Massive AoE: 15+lvl*3 all visible",
                "type": "aoe_visible", "base_dmg": 15, "lvl_mult": 3},
        }
    },
    "rogue": {
        "emoji": "rogue", "name": "Rogue",
        "desc": "Fast assassin with crits and",
        "desc2": "evasion abilities.",
        "hp": 30, "atk": 7, "df": 2, "mp": 15,
        "color": (180, 80, 220),
        "skills": {
            1: {"name": "Backstab", "emoji": "dagger", "cd": 3,
                "desc": "2.5x damage if behind enemy",
                "type": "backstab", "mult": 2.5, "front_mult": 1.5},
            3: {"name": "Shadow Step", "emoji": "skull_warn", "cd": 6,
                "desc": "Teleport behind nearest enemy",
                "type": "shadow_step", "range": 8},
            5: {"name": "Poison Blade", "emoji": "snake", "cd": 8,
                "desc": "Next 3 hits deal +5 poison/turn",
                "type": "poison", "duration": 3, "dot": 5},
            8: {"name": "Smoke Bomb", "emoji": "ghost", "cd": 12,
                "desc": "Invisible 3 turns, enemies lose you",
                "type": "stealth", "duration": 3},
        }
    },
    "cleric": {
        "emoji": "cleric", "name": "Cleric",
        "desc": "Holy warrior with heals, smites",
        "desc2": "and protective blessings.",
        "hp": 35, "atk": 4, "df": 3, "mp": 25,
        "color": (255, 230, 150),
        "skills": {
            1: {"name": "Heal", "emoji": "potion", "cd": 5,
                "desc": "Restore 15+lvl*3 HP",
                "type": "heal", "base": 15, "lvl_mult": 3},
            3: {"name": "Smite", "emoji": "zap", "cd": 4,
                "desc": "Holy damage 2x ATK (extra vs undead)",
                "type": "smite", "mult": 2.0, "undead_mult": 3.0},
            5: {"name": "Holy Shield", "emoji": "shield", "cd": 10,
                "desc": "+5 DEF for 5 turns",
                "type": "buff_def", "duration": 5, "amount": 5},
            8: {"name": "Divine Wrath", "emoji": "cross", "cd": 14,
                "desc": "Damage ALL enemies for 2x ATK",
                "type": "wrath", "mult": 2.0},
        }
    },
}

# ── Enemy Templates ──────────────────────────────────────────────────────────
# (name, emoji_key, hp, atk, def, xp, gold, color, min_floor, behavior)
# behaviors: chase, ranged, teleport, explode, swarm, tank, regen
ENEMIES = [
    # ── Floor 1: Vermin & Pests (10) ────────────────────────────────────
    ("Rat",         "rat",       6,  2, 0,  5,  1, (160,160,170), 1, "swarm"),
    ("Bat",         "bat",       5,  3, 0,  6,  1, (180,160,200), 1, "swarm"),
    ("Spider",      "spider",    8,  3, 1,  8,  2, (120,100,100), 1, "chase"),
    ("Snake",       "snake",     7,  4, 0,  9,  2, (100,180,80),  1, "chase"),
    ("Bee",         "bee",       4,  4, 0,  6,  1, (220,200,50),  1, "swarm"),
    ("Mosquito",    "mosquito",  4,  5, 0,  7,  2, (180,120,160), 1, "swarm"),
    ("Butterfly",   "butterfly", 5,  6, 0, 10,  3, (200,150,220), 1, "teleport"),
    ("Goblin",      "goblin",   10,  3, 1, 10,  3, (100,200,100), 1, "chase"),
    ("Slime",       "slime",    14,  2, 2, 12,  2, (80,220,80),   1, "regen"),
    ("Scorpion",    "scorpion", 12,  5, 1, 12,  3, (200,160,60),  2, "chase"),
    # ── Floor 1-2: Beasts & Critters (10) ──────────────────────────────
    ("Crab",        "crab",     16,  4, 4, 13,  3, (220,100,60),  2, "tank"),
    ("Turtle",      "turtle",   20,  2, 5, 14,  4, (80,160,80),   2, "tank"),
    ("Wolf",        "wolf",     12,  5, 1, 14,  3, (180,180,190), 2, "swarm"),
    ("Boar",        "boar",     18,  5, 2, 15,  4, (160,120,80),  2, "chase"),
    ("Eagle",       "eagle",    10,  7, 1, 16,  4, (180,160,120), 2, "ranged"),
    ("Skeleton",    "skeleton", 16,  5, 2, 20,  5, (200,200,180), 2, "chase"),
    ("Zombie",      "zombie",   22,  4, 2, 18,  5, (120,180,100), 2, "regen"),
    ("Monkey",      "monkey",   13,  6, 1, 16,  5, (180,140,100), 2, "chase"),
    ("Orc",         "orc",      22,  6, 3, 25,  6, (120,180,80),  2, "tank"),
    ("Ghost",       "ghost",     8,  6, 0, 18,  5, (180,180,220), 2, "teleport"),
    # ── Floor 3-4: Undead & Dark Forces (10) ───────────────────────────
    ("Vampire",     "vampire",  20,  7, 2, 30,  8, (200,60,80),   3, "chase"),
    ("Demon",       "demon",    24,  8, 3, 32,  9, (220,80,60),   3, "chase"),
    ("Mimic",       "mimic",    18, 10, 4, 35, 15, (200,170,80),  3, "chase"),
    ("Scarecrow",   "scarecrow",20,  6, 3, 22,  8, (180,160,80),  3, "ranged"),
    ("Troll",       "troll",    30,  7, 4, 28,  10,(100,180,80),   3, "regen"),
    ("Pirate",      "pirate",   22,  8, 3, 30, 12, (160,120,80),  3, "chase"),
    ("Ninja",       "ninja",    16, 10, 2, 32, 12, (80,80,100),   3, "teleport"),
    ("Golem",       "golem",    35,  6, 6, 40, 10, (160,160,150), 3, "tank"),
    ("Bear",        "bear",     32,  9, 4, 35,  10,(160,120,80),  3, "chase"),
    ("Alien",       "alien",    22, 12, 2, 45, 16, (120,220,120), 4, "teleport"),
    # ── Floor 4-5: Heavy Hitters (10) ─────────────────────────────────
    ("Tiger",       "tiger",    28, 10, 3, 38, 12, (220,160,60),  4, "chase"),
    ("Lion",        "lion",     30,  9, 3, 36, 12, (220,180,80),  4, "swarm"),
    ("Crocodile",   "crocodile",34,  8, 5, 38, 12, (100,140,60),  4, "tank"),
    ("Shark",       "shark",    30, 11, 3, 42, 14, (140,160,180), 4, "chase"),
    ("Gorilla",     "gorilla",  38, 10, 5, 45, 15, (120,100,80),  4, "chase"),
    ("Robot",       "robot",    40,  8, 7, 50, 18, (180,180,200), 4, "ranged"),
    ("Wraith",      "wraith",   15,  9, 1, 38, 12, (150,150,200), 4, "teleport"),
    ("Lich",        "lich",     30, 10, 3, 50, 15, (100,200,180), 4, "ranged"),
    ("Elephant",    "elephant", 50, 10, 7, 55, 18, (160,140,120), 5, "tank"),
    ("Rhino",       "rhino",    45, 12, 6, 52, 18, (160,140,120), 5, "chase"),
    # ── Floor 5-6: Elite & Apex (10) ───────────────────────────────────
    ("Whale",       "whale",    55,  8, 8, 55, 20, (100,140,200), 5, "tank"),
    ("Genie",       "genie",    25, 13, 2, 55, 22, (120,180,255), 5, "teleport"),
    ("Unicorn",     "unicorn",  35, 11, 4, 55, 25, (220,200,255), 5, "chase"),
    ("Mermaid",     "mermaid",  28, 10, 3, 48, 20, (120,200,220), 5, "ranged"),
    ("Dragon",      "dragon",   45, 12, 5, 65, 22, (255,150,50),  4, "ranged"),
    ("Kraken",      "kraken",   50, 11, 4, 70, 25, (80,120,200),  5, "ranged"),
    ("Phoenix",     "phoenix",  40, 14, 3, 80, 30, (255,120,40),  5, "explode"),
    ("Octopus",     "octopus",  35, 10, 4, 45, 16, (180,100,140), 4, "ranged"),
    ("Sumo",        "sumo",     55,  8, 9, 58, 20, (220,180,160), 5, "tank"),
    ("Joker",       "joker",    20, 15, 1, 60, 25, (220,50,220),  5, "teleport"),
]

# ── Perk Pool ────────────────────────────────────────────────────────────────
PERK_POOL = [
    ("Tough",        "+8 Max HP",          "max_hp", 8),
    ("Strong",       "+2 ATK",             "atk", 2),
    ("Armored",      "+2 DEF",             "df", 2),
    ("Energized",    "+10 Max MP",         "max_mp", 10),
    ("Quick",        "+1 ATK, +1 DEF",     "both_ad", 1),
    ("Vitality",     "+15 Max HP",         "max_hp", 15),
    ("Mighty",       "+3 ATK",             "atk", 3),
    ("Fortified",    "+3 DEF",             "df", 3),
    ("Resilient",    "+20 Max HP, +1 DEF", "hp_df", 0),
    ("Scholar",      "+15 Max MP",         "max_mp", 15),
    ("Berserker",    "+4 ATK, -1 DEF",     "berserk_perk", 0),
    ("Regeneration", "Heal 2 HP per turn", "regen", 2),
    ("Critical Eye", "+15% crit chance",   "crit", 15),
    ("Thick Skin",   "+5 DEF",             "df", 5),
    ("Mana Well",    "+20 Max MP",         "max_mp", 20),
    ("Warlord",      "+2 ATK, +2 DEF",     "both_ad", 2),
    ("Lifesteal",    "Heal 20% of damage", "lifesteal", 20),
    ("Evasion",      "15% dodge chance",   "dodge", 15),
]

UNDEAD_NAMES = {"Skeleton", "Ghost", "Wraith", "Lich", "Vampire", "Zombie", "Pirate"}


# ── Emoji Renderer ───────────────────────────────────────────────────────────
class EmojiRenderer:
    def __init__(self, size):
        self.size = size
        self.cache = {}
        try:
            self.font = ImageFont.truetype(
                "/usr/share/fonts/truetype/emoji/NotoColorEmoji.ttf", size - 4)
        except Exception:
            self.font = ImageFont.load_default()

    def render(self, ch):
        if ch is None:
            return None
        if ch in self.cache:
            return self.cache[ch]
        sz = self.size
        img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        bb = d.textbbox((0, 0), ch, font=self.font)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        x = (sz - tw) // 2 - bb[0]
        y = (sz - th) // 2 - bb[1]
        d.text((x, y), ch, font=self.font, embedded_color=True)
        s = pygame.image.frombuffer(img.tobytes(), img.size, img.mode).convert_alpha()
        self.cache[ch] = s
        return s


# ── Dungeon Gen ──────────────────────────────────────────────────────────────
class Room:
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.cx, self.cy = x + w // 2, y + h // 2
        self.room_type = "normal"  # normal, large, hall, irregular, cross, lshape, treasure, armory

    def hits(self, o, p=2):
        return not (self.x + self.w + p < o.x or o.x + o.w + p < self.x
                    or self.y + self.h + p < o.y or o.y + o.h + p < self.y)

    def contains(self, x, y):
        return self.x <= x < self.x + self.w and self.y <= y < self.y + self.h

    def floor_tiles(self, d, w, h):
        tiles = []
        for yy in range(self.y, self.y + self.h):
            for xx in range(self.x, self.x + self.w):
                if 0 < xx < w - 1 and 0 < yy < h - 1 and d[yy][xx] == FLOOR:
                    tiles.append((xx, yy))
        return tiles


# ── Helper: pick biome based on floor ──────────────────────────────────────
def _pick_biome(lvl):
    order = ["classic", "cave", "cellular", "bsp", "maze", "drunkard"]
    return order[(lvl - 1) % len(order)]


def _get_biome_key(lvl):
    return _pick_biome(lvl)


# ── Corridor helpers ───────────────────────────────────────────────────────
def _ch(d, x1, x2, y, w, h):
    for x in range(min(x1, x2), max(x1, x2) + 1):
        if 0 < y < h - 1 and 0 < x < w - 1 and d[y][x] == WALL:
            d[y][x] = FLOOR

def _cv(d, y1, y2, x, w, h):
    for y in range(min(y1, y2), max(y1, y2) + 1):
        if 0 < y < h - 1 and 0 < x < w - 1 and d[y][x] == WALL:
            d[y][x] = FLOOR


def _corridor_l(d, x1, y1, x2, y2, w, h):
    if random.random() < 0.5:
        _ch(d, x1, x2, y1, w, h); _cv(d, y1, y2, x2, w, h)
    else:
        _cv(d, y1, y2, x1, w, h); _ch(d, x1, x2, y2, w, h)


def _corridor_zigzag(d, x1, y1, x2, y2, w, h):
    cx, cy = x1, y1
    while abs(cx - x2) + abs(cy - y2) > 1:
        if random.random() < 0.25:
            if abs(x2 - cx) > abs(y2 - cy):
                jog = 1 if random.random() < 0.5 else -1
                ny = cy + jog
                if 0 < ny < h - 1 and 0 < cx < w - 1:
                    d[ny][cx] = FLOOR; cy = ny
            else:
                jog = 1 if random.random() < 0.5 else -1
                nx = cx + jog
                if 0 < nx < w - 1 and 0 < cy < h - 1:
                    d[cy][nx] = FLOOR; cx = nx
        dx = (1 if cx < x2 else -1 if cx > x2 else 0)
        dy = (1 if cy < y2 else -1 if cy > y2 else 0)
        if abs(x2 - cx) >= abs(y2 - cy) and dx != 0:
            nx = cx + dx
            if 0 < nx < w - 1 and 0 < cy < h - 1:
                d[cy][nx] = FLOOR; cx = nx
        elif dy != 0:
            ny = cy + dy
            if 0 < ny < h - 1 and 0 < cx < w - 1:
                d[ny][cx] = FLOOR; cy = ny
        elif dx != 0:
            nx = cx + dx
            if 0 < nx < w - 1 and 0 < cy < h - 1:
                d[cy][nx] = FLOOR; cx = nx


def _corridor_wide(d, x1, y1, x2, y2, w, h, width=2):
    if random.random() < 0.5:
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for dy in range(-width // 2, width // 2 + 1):
                ny = y1 + dy
                if 0 < ny < h - 1 and 0 < x < w - 1 and d[ny][x] == WALL:
                    d[ny][x] = FLOOR
        for y in range(min(y1, y2), max(y1, y2) + 1):
            for dx in range(-width // 2, width // 2 + 1):
                nx = x2 + dx
                if 0 < nx < w - 1 and 0 < y < h - 1 and d[y][nx] == WALL:
                    d[y][nx] = FLOOR
    else:
        for y in range(min(y1, y2), max(y1, y2) + 1):
            for dx in range(-width // 2, width // 2 + 1):
                nx = x1 + dx
                if 0 < nx < w - 1 and 0 < y < h - 1 and d[y][nx] == WALL:
                    d[y][nx] = FLOOR
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for dy in range(-width // 2, width // 2 + 1):
                ny = y2 + dy
                if 0 < ny < h - 1 and 0 < x < w - 1 and d[ny][x] == WALL:
                    d[ny][x] = FLOOR


def _corridor_looped(d, x1, y1, x2, y2, w, h):
    """L-corridor with 40% chance of adding a parallel second path (loop)."""
    _corridor_l(d, x1, y1, x2, y2, w, h)
    if random.random() < 0.40:
        off = random.choice([-2, 2])
        if abs(x1 - x2) > abs(y1 - y2):
            _corridor_l(d, x1, y1 + off, x2, y2 + off, w, h)
        else:
            _corridor_l(d, x1 + off, y1, x2 + off, y2, w, h)


# ── MST connectivity guarantee + loop creation ────────────────────────────
def _ensure_connectivity(d, rooms, w, h, corridor_fn=None):
    if len(rooms) < 2:
        return
    if corridor_fn is None:
        corridor_fn = _corridor_l
    n = len(rooms)
    edges = []
    for i in range(n):
        for j in range(i + 1, n):
            dist = abs(rooms[i].cx - rooms[j].cx) + abs(rooms[i].cy - rooms[j].cy)
            edges.append((dist, i, j))
    edges.sort()
    parent = list(range(n))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parent[a] = b
            return True
        return False
    for dist, i, j in edges:
        if union(i, j):
            corridor_fn(d, rooms[i].cx, rooms[i].cy, rooms[j].cx, rooms[j].cy, w, h)
    # Add extra corridors for loops (~15% of remaining edges)
    extra = 0
    max_extra = max(1, n // 3)
    for dist, i, j in edges:
        if extra >= max_extra:
            break
        if random.random() < 0.15:
            corridor_fn(d, rooms[i].cx, rooms[i].cy, rooms[j].cx, rooms[j].cy, w, h)
            extra += 1


# ── Doors ──────────────────────────────────────────────────────────────────
def _place_doors(d, rooms, w, h):
    for room in rooms:
        door_positions = []
        for y in range(room.y, room.y + room.h):
            for x in range(room.x, room.x + room.w):
                if d[y][x] != FLOOR:
                    continue
                if x == room.x or x == room.x + room.w - 1 or y == room.y or y == room.y + room.h - 1:
                    floor_count = 0
                    for ddx, ddy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nx, ny = x + ddx, y + ddy
                        if 0 <= nx < w and 0 <= ny < h and d[ny][nx] == FLOOR:
                            if not room.contains(nx, ny):
                                floor_count += 1
                    if floor_count >= 1:
                        door_positions.append((x, y))
        if door_positions and random.random() < 0.6:
            num_doors = min(random.randint(1, 3), len(door_positions))
            chosen = random.sample(door_positions, num_doors)
            for dx, dy in chosen:
                d[dy][dx] = DOOR


# ── Room features (blocking: pillars, pools) ────────────────────────────────
def _add_room_features(d, room, w, h, biome):
    if room.w < 5 or room.h < 5:
        return
    feat = random.random()
    if feat < 0.30:
        spacing = 3
        for py in range(room.y + 2, room.y + room.h - 2, spacing):
            for px in range(room.x + 2, room.x + room.w - 2, spacing):
                if d[py][px] == FLOOR:
                    d[py][px] = PILLAR
    elif feat < 0.50:
        pw = min(room.w - 4, 5)
        ph = min(room.h - 4, 4)
        if pw >= 2 and ph >= 2:
            cx, cy = room.cx, room.cy
            sx, sy = cx - pw // 2, cy - ph // 2
            tile = WATER if biome != "maze" and random.random() < 0.7 else LAVA
            for yy in range(sy, sy + ph):
                for xx in range(sx, sx + pw):
                    if 0 < xx < w - 1 and 0 < yy < h - 1:
                        if d[yy][xx] == FLOOR:
                            d[yy][xx] = tile
    elif feat < 0.60:
        for corner_y, corner_x in [(room.y + 1, room.x + 1),
                                     (room.y + 1, room.x + room.w - 2),
                                     (room.y + room.h - 2, room.x + 1),
                                     (room.y + room.h - 2, room.x + room.w - 2)]:
            if 0 < corner_x < w - 1 and 0 < corner_y < h - 1:
                if d[corner_y][corner_x] == FLOOR:
                    d[corner_y][corner_x] = WATER


# ── Varied room shape carvers ──────────────────────────────────────────────
def _carve_cross_room(d, rx, ry, size, w, h):
    arm = size // 2
    for yy in range(ry + arm, ry + arm + size):
        for xx in range(rx, rx + size * 3 - size // 2):
            if 0 < xx < w - 1 and 0 < yy < h - 1:
                d[yy][xx] = FLOOR
    for yy in range(ry, ry + size * 3 - size // 2):
        for xx in range(rx + arm, rx + arm + size):
            if 0 < xx < w - 1 and 0 < yy < h - 1:
                d[yy][xx] = FLOOR
    r = Room(rx, ry, size * 3 - size // 2, size * 3 - size // 2)
    r.room_type = "cross"
    return r

def _carve_lroom(d, rx, ry, w_len, h_len, thick, w, h):
    for yy in range(ry, ry + thick):
        for xx in range(rx, rx + w_len):
            if 0 < xx < w - 1 and 0 < yy < h - 1:
                d[yy][xx] = FLOOR
    for yy in range(ry, ry + h_len):
        for xx in range(rx, rx + thick):
            if 0 < xx < w - 1 and 0 < yy < h - 1:
                d[yy][xx] = FLOOR
    r = Room(rx, ry, w_len, h_len)
    r.room_type = "lshape"
    return r

def _carve_circle_room(d, cx, cy, radius, w, h):
    tiles = []
    for yy in range(cy - radius, cy + radius + 1):
        for xx in range(cx - radius, cx + radius + 1):
            if (xx - cx) ** 2 + (yy - cy) ** 2 <= radius ** 2:
                if 0 < xx < w - 1 and 0 < yy < h - 1:
                    d[yy][xx] = FLOOR
                    tiles.append((xx, yy))
    if not tiles:
        return None
    xs = [p[0] for p in tiles]
    ys = [p[1] for p in tiles]
    r = Room(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
    r.cx, r.cy = cx, cy
    r.room_type = "normal"
    return r

def _carve_troom(d, rx, ry, width, height, stem_h, w, h):
    for yy in range(ry, ry + height):
        for xx in range(rx, rx + width):
            if 0 < xx < w - 1 and 0 < yy < h - 1:
                d[yy][xx] = FLOOR
    stem_x = rx + width // 2 - 1
    for yy in range(ry + height, ry + height + stem_h):
        for xx in range(stem_x, stem_x + 3):
            if 0 < xx < w - 1 and 0 < yy < h - 1:
                d[yy][xx] = FLOOR
    r = Room(rx, ry, width, height + stem_h)
    r.room_type = "normal"
    return r


# ── Biome-specific scattered decorations (walkable, visual only) ───────────
def _scatter_decorations(d, rooms, w, h, biome, lvl):
    deco_map = {
        "classic":  [(DECO_BONES, 0.06), (DECO_CRYSTAL, 0.02)],
        "cave":     [(DECO_WEB, 0.08), (DECO_CRYSTAL, 0.04), (DECO_BONES, 0.03)],
        "cellular": [(DECO_MUSHROOM, 0.10), (DECO_BONES, 0.02)],
        "bsp":      [(DECO_BONES, 0.05), (DECO_CRYSTAL, 0.03)],
        "maze":     [(DECO_FLOWERS, 0.04), (DECO_GRASS, 0.06)],
        "drunkard": [(DECO_MUSHROOM, 0.08), (DECO_CRYSTAL, 0.05)],
    }
    decos = deco_map.get(biome, deco_map["classic"])
    for room in rooms:
        tiles = room.floor_tiles(d, w, h)
        if not tiles:
            continue
        for deco_type, chance in decos:
            actual_chance = min(chance * (1 + lvl * 0.05), 0.20)
            for tx, ty in tiles:
                if d[ty][tx] != FLOOR:
                    continue
                if random.random() < actual_chance:
                    d[ty][tx] = deco_type


# ── Special room types ────────────────────────────────────────────────────
def _make_special_room(d, room, w, h, special_type, biome):
    tiles = room.floor_tiles(d, w, h)
    if len(tiles) < 6:
        return
    if special_type == "treasure":
        room.room_type = "treasure"
        cx, cy = room.cx, room.cy
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                tx, ty = cx + dx, cy + dy
                if 0 < tx < w - 1 and 0 < ty < h - 1 and d[ty][tx] == FLOOR:
                    if dx == 0 and dy == 0:
                        d[ty][tx] = DECO_CRYSTAL
                    elif abs(dx) + abs(dy) <= 1:
                        d[ty][tx] = WATER
        for corner_dy, corner_dx in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            tx, ty = cx + corner_dx * 2, cy + corner_dy * 2
            if 0 < tx < w - 1 and 0 < ty < h - 1 and d[ty][tx] == FLOOR:
                d[ty][tx] = PILLAR
    elif special_type == "armory":
        room.room_type = "armory"
        for py in range(room.y + 2, room.y + room.h - 2, 2):
            for px in range(room.x + 1, room.x + room.w - 1, 3):
                if 0 < px < w - 1 and 0 < py < h - 1 and d[py][px] == FLOOR:
                    d[py][px] = PILLAR
    elif special_type == "library":
        room.room_type = "library"
        spacing = 2
        for py in range(room.y + 1, room.y + room.h - 1, spacing):
            for px in range(room.x + 1, room.x + room.w - 1, spacing):
                if 0 < px < w - 1 and 0 < py < h - 1 and d[py][px] == FLOOR:
                    if random.random() < 0.5:
                        d[py][px] = PILLAR
                    else:
                        d[py][px] = DECO_CRYSTAL
    elif special_type == "shrine":
        room.room_type = "shrine"
        cx, cy = room.cx, room.cy
        if 0 < cx < w - 1 and 0 < cy < h - 1 and d[cy][cx] == FLOOR:
            d[cy][cx] = DECO_CRYSTAL
        for dy, dx in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            tx, ty = cx + dx, cy + dy
            if 0 < tx < w - 1 and 0 < ty < h - 1 and d[ty][tx] == FLOOR:
                d[ty][tx] = PILLAR


def _assign_special_rooms(d, rooms, w, h, biome, lvl):
    if len(rooms) < 4:
        return
    candidates = [r for r in rooms[1:] if r.w >= 6 and r.h >= 5]
    if not candidates:
        return
    specials = ["treasure", "armory", "library", "shrine"]
    num_special = min(random.randint(1, 2), len(candidates))
    chosen = random.sample(candidates, num_special)
    for room, stype in zip(chosen, random.sample(specials, min(num_special, len(specials)))):
        _make_special_room(d, room, w, h, stype, biome)


# ── Stairs placement: farthest room from start ─────────────────────────────
def _place_stairs_farthest(d, rooms, w, h):
    if len(rooms) < 2:
        return
    r0 = rooms[0]
    best_room = rooms[-1]
    best_dist = 0
    for r in rooms[1:]:
        dist = abs(r.cx - r0.cx) + abs(r.cy - r0.cy)
        if dist > best_dist:
            best_dist = dist
            best_room = r
    for dy in range(best_room.h):
        for dx in range(best_room.w):
            tx, ty = best_room.x + dx, best_room.y + dy
            if 0 < tx < w - 1 and 0 < ty < h - 1 and d[ty][tx] == FLOOR:
                d[ty][tx] = STAIRS
                return
    d[best_room.cy][best_room.cx] = STAIRS


# ══════════════════════════════════════════════════════════════════════════
# ALGORITHM 1: Classic Rooms + Varied Shapes + MST + Loops
# ══════════════════════════════════════════════════════════════════════════
def _gen_classic(w, h, lvl):
    d = [[WALL] * w for _ in range(h)]
    rooms = []
    max_rooms = min(12 + lvl * 2, 30)
    for _ in range(500):
        if len(rooms) >= max_rooms:
            break
        shape_roll = random.random()
        if shape_roll < 0.12 and len(rooms) >= 2:
            size = random.randint(3, 5)
            rx = random.randint(3, w - size * 3)
            ry = random.randint(3, h - size * 3)
            nr = _carve_cross_room(d, rx, ry, size, w, h)
        elif shape_roll < 0.22 and len(rooms) >= 2:
            radius = random.randint(3, 5)
            cx = random.randint(radius + 2, w - radius - 3)
            cy = random.randint(radius + 2, h - radius - 3)
            nr = _carve_circle_room(d, cx, cy, radius, w, h)
            if nr is None:
                continue
        elif shape_roll < 0.30 and len(rooms) >= 1:
            w_len = random.randint(8, 14)
            h_len = random.randint(7, 12)
            thick = random.randint(3, 4)
            rx = random.randint(2, w - w_len - 2)
            ry = random.randint(2, h - h_len - 2)
            nr = _carve_lroom(d, rx, ry, w_len, h_len, thick, w, h)
        elif shape_roll < 0.36 and len(rooms) >= 1:
            rw = random.randint(8, 14)
            rh = random.randint(3, 5)
            stem = random.randint(3, 5)
            rx = random.randint(2, w - rw - 2)
            ry = random.randint(2, h - rh - stem - 2)
            nr = _carve_troom(d, rx, ry, rw, rh, stem, w, h)
        else:
            rw = random.randint(5, 12)
            rh = random.randint(4, 9)
            rx = random.randint(1, w - rw - 1)
            ry = random.randint(1, h - rh - 1)
            nr = Room(rx, ry, rw, rh)
            if any(nr.hits(r) for r in rooms):
                continue
            for yy in range(ry, ry + rh):
                for xx in range(rx, rx + rw):
                    d[yy][xx] = FLOOR
        if any(nr.hits(r) for r in rooms):
            continue
        rooms.append(nr)
    _ensure_connectivity(d, rooms, w, h, _corridor_looped)
    _place_doors(d, rooms, w, h)
    for r in rooms[1:]:
        _add_room_features(d, r, w, h, "classic")
    _assign_special_rooms(d, rooms, w, h, "classic", lvl)
    _scatter_decorations(d, rooms, w, h, "classic", lvl)
    return d, rooms


# ══════════════════════════════════════════════════════════════════════════
# ALGORITHM 2: Organic Caves (drunkard's walk)
# ══════════════════════════════════════════════════════════════════════════
def _gen_cave(w, h, lvl):
    d = [[WALL] * w for _ in range(h)]
    rooms = []
    num_seeds = min(4 + lvl // 3, 10)
    for _ in range(num_seeds):
        cx = random.randint(5, w - 6)
        cy = random.randint(5, h - 6)
        steps = random.randint(80, 180)
        x, y = cx, cy
        for _ in range(steps):
            if 1 < x < w - 2 and 1 < y < h - 2:
                d[y][x] = FLOOR
                if random.random() < 0.4:
                    for ddx, ddy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nx, ny = x + ddx, y + ddy
                        if 1 < nx < w - 2 and 1 < ny < h - 2:
                            d[ny][nx] = FLOOR
            ddx, ddy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])
            x = max(2, min(w - 3, x + ddx))
            y = max(2, min(h - 3, y + ddy))
    floor_tiles = [(x, y) for y in range(1, h - 1) for x in range(1, w - 1) if d[y][x] == FLOOR]
    if len(floor_tiles) < 10:
        for y in range(3, h - 3):
            for x in range(3, w - 3):
                d[y][x] = FLOOR
        rooms.append(Room(2, 2, w - 4, h - 4))
        return d, rooms
    visited = set()
    clusters = []
    for fx, fy in floor_tiles:
        if (fx, fy) in visited:
            continue
        cluster = []
        queue = deque([(fx, fy)])
        visited.add((fx, fy))
        while queue:
            tx, ty = queue.popleft()
            cluster.append((tx, ty))
            for ddx, ddy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = tx + ddx, ty + ddy
                if (nx, ny) not in visited and 0 < nx < w - 1 and 0 < ny < h - 1 and d[ny][nx] == FLOOR:
                    visited.add((nx, ny))
                    queue.append((nx, ny))
        if len(cluster) >= 8:
            clusters.append(cluster)
    clusters.sort(key=len, reverse=True)
    for cl in clusters[:max(3, len(clusters) // 2)]:
        xs = [p[0] for p in cl]
        ys = [p[1] for p in cl]
        r = Room(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
        r.cx, r.cy = sum(xs) // len(xs), sum(ys) // len(ys)
        r.room_type = "irregular"
        rooms.append(r)
    _ensure_connectivity(d, rooms, w, h, lambda d, x1, y1, x2, y2, w, h: _corridor_wide(d, x1, y1, x2, y2, w, h, 2))
    _scatter_decorations(d, rooms, w, h, "cave", lvl)
    return d, rooms


# ══════════════════════════════════════════════════════════════════════════
# ALGORITHM 3: Cellular Automata Caves
# ══════════════════════════════════════════════════════════════════════════
def _gen_cellular(w, h, lvl):
    d = [[WALL] * w for _ in range(h)]
    fill = 0.48
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            d[y][x] = FLOOR if random.random() < fill else WALL
    for _ in range(4):
        nd = [row[:] for row in d]
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                walls = sum(1 for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                           if d[y + dy][x + dx] == WALL)
                if d[y][x] == FLOOR:
                    nd[y][x] = FLOOR if walls < 5 else WALL
                else:
                    nd[y][x] = FLOOR if walls < 4 else WALL
        d = nd
    for y in range(h):
        d[y][0] = d[y][w - 1] = WALL
    for x in range(w):
        d[0][x] = d[h - 1][x] = WALL
    floor_tiles = [(x, y) for y in range(1, h - 1) for x in range(1, w - 1) if d[y][x] == FLOOR]
    visited = set()
    rooms = []
    for fx, fy in floor_tiles:
        if (fx, fy) in visited:
            continue
        cluster = []
        queue = deque([(fx, fy)])
        visited.add((fx, fy))
        while queue:
            tx, ty = queue.popleft()
            cluster.append((tx, ty))
            for ddx, ddy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = tx + ddx, ty + ddy
                if (nx, ny) not in visited and 0 < nx < w - 1 and 0 < ny < h - 1 and d[ny][nx] == FLOOR:
                    visited.add((nx, ny))
                    queue.append((nx, ny))
        if len(cluster) >= 10:
            xs = [p[0] for p in cluster]
            ys = [p[1] for p in cluster]
            r = Room(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
            r.cx, r.cy = sum(xs) // len(xs), sum(ys) // len(ys)
            r.room_type = "irregular"
            rooms.append(r)
    _ensure_connectivity(d, rooms, w, h, _corridor_looped)
    for r in rooms:
        if r.w >= 8 and r.h >= 6:
            _add_room_features(d, r, w, h, "cellular")
    _scatter_decorations(d, rooms, w, h, "cellular", lvl)
    return d, rooms


# ══════════════════════════════════════════════════════════════════════════
# ALGORITHM 4: BSP Tree
# ══════════════════════════════════════════════════════════════════════════
class BSPNode:
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.left = self.right = None
        self.room = None
    def split(self, depth, max_depth=4, min_size=8):
        if depth >= max_depth or self.w < min_size * 2 or self.h < min_size * 2:
            return False
        if self.w > self.h and self.w >= min_size * 2:
            split_x = random.randint(self.x + min_size, self.x + self.w - min_size)
            self.left = BSPNode(self.x, self.y, split_x - self.x, self.h)
            self.right = BSPNode(split_x, self.y, self.x + self.w - split_x, self.h)
        elif self.h >= min_size * 2:
            split_y = random.randint(self.y + min_size, self.y + self.h - min_size)
            self.left = BSPNode(self.x, self.y, self.w, split_y - self.y)
            self.right = BSPNode(self.x, split_y, self.w, self.y + self.h - split_y)
        else:
            return False
        self.left.split(depth + 1, max_depth, min_size)
        self.right.split(depth + 1, max_depth, min_size)
        return True
    def create_rooms(self, d, w, h, biome, lvl):
        rooms = []
        if self.left and self.right:
            rooms += self.left.create_rooms(d, w, h, biome, lvl)
            rooms += self.right.create_rooms(d, w, h, biome, lvl)
            lr = self._get_room(self.left)
            rr = self._get_room(self.right)
            if lr and rr:
                _corridor_zigzag(d, lr.cx, lr.cy, rr.cx, rr.cy, w, h)
        else:
            pad = 2
            max_rw = max(3, self.w - pad * 2)
            max_rh = max(3, self.h - pad * 2)
            min_rw = max(3, min(4, max_rw))
            min_rh = max(3, min(3, max_rh))
            if max_rw < 3 or max_rh < 3:
                return rooms
            rw = random.randint(min_rw, max_rw)
            rh = random.randint(min_rh, max_rh)
            rx = self.x + pad + random.randint(0, max(0, self.w - rw - pad * 2))
            ry = self.y + pad + random.randint(0, max(0, self.h - rh - pad * 2))
            rw = min(rw, self.w - pad * 2)
            rh = min(rh, self.h - pad * 2)
            rx = max(self.x + 1, min(rx, self.x + self.w - rw - 1))
            ry = max(self.y + 1, min(ry, self.y + self.h - rh - 1))
            if rw >= 6 and rh >= 5 and random.random() < 0.15:
                cr = _carve_circle_room(d, rx + rw // 2, ry + rh // 2, min(rw, rh) // 2, w, h)
                if cr:
                    r = cr
                else:
                    for yy in range(ry, ry + rh):
                        for xx in range(rx, rx + rw):
                            if 0 < xx < w - 1 and 0 < yy < h - 1:
                                d[yy][xx] = FLOOR
                    r = Room(rx, ry, rw, rh)
            else:
                for yy in range(ry, ry + rh):
                    for xx in range(rx, rx + rw):
                        if 0 < xx < w - 1 and 0 < yy < h - 1:
                            d[yy][xx] = FLOOR
                r = Room(rx, ry, rw, rh)
            r.room_type = random.choice(["normal", "large", "hall"])
            self.room = r
            rooms.append(r)
        return rooms
    def _get_room(self, node):
        if node.room:
            return node.room
        if node.left:
            r = self._get_room(node.left)
            if r: return r
        if node.right:
            r = self._get_room(node.right)
            if r: return r
        return None


def _gen_bsp(w, h, lvl):
    d = [[WALL] * w for _ in range(h)]
    root = BSPNode(1, 1, w - 2, h - 2)
    root.split(0, max_depth=5, min_size=6)
    rooms = root.create_rooms(d, w, h, "bsp", lvl)
    _ensure_connectivity(d, rooms, w, h, _corridor_l)
    _place_doors(d, rooms, w, h)
    for r in rooms[1:]:
        if r.room_type in ("large", "hall"):
            _add_room_features(d, r, w, h, "bsp")
    _assign_special_rooms(d, rooms, w, h, "bsp", lvl)
    _scatter_decorations(d, rooms, w, h, "bsp", lvl)
    return d, rooms


# ══════════════════════════════════════════════════════════════════════════
# ALGORITHM 5: Maze + Rooms (with dead-end removal + loop breaking)
# ══════════════════════════════════════════════════════════════════════════
def _gen_maze(w, h, lvl):
    d = [[WALL] * w for _ in range(h)]
    rooms = []
    num_rooms = min(5 + lvl, 12)
    for _ in range(500):
        if len(rooms) >= num_rooms:
            break
        rw = random.randint(4, 8)
        rh = random.randint(3, 6)
        rx = random.randint(2, w - rw - 2)
        ry = random.randint(2, h - rh - 2)
        nr = Room(rx, ry, rw, rh)
        if any(nr.hits(r, p=3) for r in rooms):
            continue
        for yy in range(ry, ry + rh):
            for xx in range(rx, rx + rw):
                d[yy][xx] = FLOOR
        rooms.append(nr)
    if len(rooms) < 2:
        return _gen_classic(w, h, lvl)
    maze_w = (w - 2) // 2
    maze_h = (h - 2) // 2
    maze_visited = [[False] * maze_w for _ in range(maze_h)]
    stack = []
    sx = max(0, min(maze_w - 1, (rooms[0].cx - 1) // 2))
    sy = max(0, min(maze_h - 1, (rooms[0].cy - 1) // 2))
    maze_visited[sy][sx] = True
    stack.append((sx, sy))
    while stack:
        cx, cy = stack[-1]
        neighbors = []
        for ddx, ddy in [(0, -2), (0, 2), (-2, 0), (2, 0)]:
            nx, ny = cx + ddx // 2, cy + ddy // 2
            mx, my = cx + ddx, cy + ddy
            if 0 <= mx < maze_w and 0 <= my < maze_h and not maze_visited[my][mx]:
                neighbors.append((mx, my, nx, ny))
        if neighbors:
            mx, my, wx, wy = random.choice(neighbors)
            maze_visited[my][mx] = True
            for ty in (cy * 2 + 1, my * 2 + 1):
                for tx in (cx * 2 + 1, mx * 2 + 1):
                    if 0 < tx < w - 1 and 0 < ty < h - 1:
                        d[ty][tx] = FLOOR
            if 0 < wx * 2 + 1 < w - 1 and 0 < wy * 2 + 1 < h - 1:
                d[wy * 2 + 1][wx * 2 + 1] = FLOOR
            stack.append((mx, my))
        else:
            stack.pop()
    for r in rooms:
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                tx, ty = r.cx + dx, r.cy + dy
                if 0 < tx < w - 1 and 0 < ty < h - 1:
                    d[ty][tx] = FLOOR
    # Dead-end removal: remove ~40% of corridor dead-ends
    dead_ends = []
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            if d[y][x] != FLOOR:
                continue
            adj = sum(1 for ddx, ddy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                      if 0 < x + ddx < w - 1 and 0 < y + ddy < h - 1
                      and d[y + ddy][x + ddx] == FLOOR)
            if adj == 1:
                dead_ends.append((x, y))
    random.shuffle(dead_ends)
    for ex, ey in dead_ends[:len(dead_ends) * 2 // 5]:
        d[ey][ex] = WALL
    # Loop breaking: punch through walls between parallel corridors
    for _ in range(w * h // 80):
        rx = random.randint(2, w - 3)
        ry = random.randint(2, h - 3)
        if d[ry][rx] == WALL:
            floor_neighbors = sum(1 for ddx, ddy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                                   if 0 < rx + ddx < w - 1 and 0 < ry + ddy < h - 1
                                   and d[ry + ddy][rx + ddx] == FLOOR)
            if floor_neighbors >= 2 and floor_neighbors <= 3:
                d[ry][rx] = FLOOR
    _ensure_connectivity(d, rooms, w, h, _corridor_l)
    _place_doors(d, rooms, w, h)
    _scatter_decorations(d, rooms, w, h, "maze", lvl)
    return d, rooms


# ══════════════════════════════════════════════════════════════════════════
# ALGORITHM 6: Drunkard's Walk Cave Network
# ══════════════════════════════════════════════════════════════════════════
def _gen_drunkard(w, h, lvl):
    d = [[WALL] * w for _ in range(h)]
    rooms = []
    num_walkers = 3 + min(lvl, 5)
    walkers = []
    for i in range(num_walkers):
        wx = random.randint(5, w - 6)
        wy = random.randint(5, h - 6)
        walkers.append([wx, wy, random.randint(100, 250)])
    for walker in walkers:
        x, y, steps = walker
        for _ in range(steps):
            if 1 < x < w - 2 and 1 < y < h - 2:
                d[y][x] = FLOOR
                if random.random() < 0.35:
                    ddx, ddy = random.choice([(-1, 0), (1, 0), (0, -1), (0, 1)])
                    nx, ny = x + ddx, y + ddy
                    if 1 < nx < w - 2 and 1 < ny < h - 2:
                        d[ny][nx] = FLOOR
            ddx, ddy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])
            x = max(2, min(w - 3, x + ddx))
            y = max(2, min(h - 3, y + ddy))
        walker[0], walker[1] = x, y
    floor_tiles = [(x, y) for y in range(1, h - 1) for x in range(1, w - 1) if d[y][x] == FLOOR]
    visited = set()
    for fx, fy in floor_tiles:
        if (fx, fy) in visited:
            continue
        cluster = []
        queue = deque([(fx, fy)])
        visited.add((fx, fy))
        while queue:
            tx, ty = queue.popleft()
            cluster.append((tx, ty))
            for ddx, ddy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = tx + ddx, ty + ddy
                if (nx, ny) not in visited and 0 < nx < w - 1 and 0 < ny < h - 1 and d[ny][nx] == FLOOR:
                    visited.add((nx, ny))
                    queue.append((nx, ny))
        if len(cluster) >= 12:
            xs = [p[0] for p in cluster]
            ys = [p[1] for p in cluster]
            r = Room(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
            r.cx, r.cy = sum(xs) // len(xs), sum(ys) // len(ys)
            r.room_type = "irregular"
            rooms.append(r)
    _ensure_connectivity(d, rooms, w, h, lambda d, x1, y1, x2, y2, w, h: _corridor_wide(d, x1, y1, x2, y2, w, h, 2))
    _scatter_decorations(d, rooms, w, h, "drunkard", lvl)
    return d, rooms


# ══════════════════════════════════════════════════════════════════════════
# MAIN DISPATCHER
# ══════════════════════════════════════════════════════════════════════════
def gen_dungeon(w, h, lvl=1):
    biome = _pick_biome(lvl)
    generators = {
        "classic":  _gen_classic,
        "cave":     _gen_cave,
        "cellular": _gen_cellular,
        "bsp":      _gen_bsp,
        "maze":     _gen_maze,
        "drunkard": _gen_drunkard,
    }
    d, rooms = generators[biome](w, h, lvl)
    if len(rooms) < 2:
        rx, ry = w - 10, h - 8
        for yy in range(ry, ry + 5):
            for xx in range(rx, rx + 7):
                if 0 < xx < w - 1 and 0 < yy < h - 1:
                    d[yy][xx] = FLOOR
        r = Room(rx, ry, 7, 5)
        rooms.append(r)
        if rooms:
            _corridor_l(d, rooms[0].cx, rooms[0].cy, r.cx, r.cy, w, h)
    _place_stairs_farthest(d, rooms, w, h)
    return d, rooms, biome


def compute_fov(dungeon, px, py, radius=8):
    vis = {(px, py)}
    H, W = len(dungeon), len(dungeon[0])
    for i in range(360):
        a = 2 * math.pi * i / 360
        dx, dy = math.cos(a), math.sin(a)
        x, y = px + 0.5, py + 0.5
        for _ in range(radius):
            x += dx * 0.5; y += dy * 0.5
            ix, iy = int(x), int(y)
            if not (0 <= ix < W and 0 <= iy < H):
                break
            vis.add((ix, iy))
            if dungeon[iy][ix] in (WALL, PILLAR, WATER, LAVA):
                break
    return vis


# ── Entities ─────────────────────────────────────────────────────────────────
class Entity:
    def __init__(self, name, emoji, x, y, hp, atk, df, color=C_TXT):
        self.name, self.emoji = name, emoji
        self.x, self.y = x, y
        self.max_hp, self.hp = hp, hp
        self.atk, self.defense = atk, df
        self.color = color
        self.alive = True
        self.stun = 0
        self.freeze = 0
        self.poison = 0
        self.poison_dmg = 0


class Enemy(Entity):
    def __init__(self, name, emoji, x, y, hp, atk, df,
                 xp_r, gold_r, color, behavior="chase"):
        super().__init__(name, emoji, x, y, hp, atk, df, color)
        self.xp_reward, self.gold_reward = xp_r, gold_r
        self.behavior = behavior
        # AI state
        self.last_seen_x = None
        self.last_seen_y = None
        self.ai_state = "idle"       # idle, hunt, fight, flee, kite, guard
        self.turns_since_seen = 0
        self.flee_turns = 0
        self.charge_timer = 0        # for explode rush
        self.enraged = False
        self.ability_cooldown = 0


class Player(Entity):
    def __init__(self, cls_key, x, y):
        cd = CLASS_DEFS[cls_key]
        super().__init__(cd["name"], EMOJI[cd["emoji"]], x, y,
                         cd["hp"], cd["atk"], cd["df"], cd["color"])
        self.cls_key = cls_key
        self.max_mp = cd["mp"]
        self.mp = cd["mp"]
        self.level = 1
        self.xp = 0
        self.xp_next = 20
        self.gold = 0
        self.weapon_atk = 0
        self.armor_def = 0
        self.potions = 2
        self.kills = 0
        # Skills: {level: {skill_data + "cd_current": 0, "unlocked": True}}
        self.skills = {}
        for lvl, sk in cd["skills"].items():
            s = dict(sk)
            s["cd_current"] = 0
            s["unlocked"] = (lvl <= 1)
            s["unlock_level"] = lvl
            self.skills[lvl] = s
        # Buffs: list of (name, turns_left, stat, amount)
        self.buffs = []
        # Status
        self.stealth = 0
        self.poison_blade = 0
        self.poison_blade_dmg = 0
        # Perks
        self.perks = []
        self.crit_chance = 5
        self.dodge_chance = 0
        self.regen = 0
        self.lifesteal = 0
        # Level-up queue
        self.pending_levelups = 0
        self.levelup_choices = []

    def get_total_atk(self):
        a = self.atk + self.weapon_atk
        for _, _, stat, amt in self.buffs:
            if stat == "atk":
                a += amt
        return a

    def get_total_def(self):
        d = self.defense + self.armor_def
        for _, _, stat, amt in self.buffs:
            if stat == "def":
                d += amt
        return d

    def tick_cooldowns(self):
        for lvl in self.skills:
            sk = self.skills[lvl]
            if sk["cd_current"] > 0:
                sk["cd_current"] -= 1
        # Tick buffs
        new_buffs = []
        for name, turns, stat, amt in self.buffs:
            if turns > 1:
                new_buffs.append((name, turns - 1, stat, amt))
            else:
                self.msg_extra(f"{name} expired.", C_DIM)
        self.buffs = new_buffs
        # Tick status
        if self.stealth > 0:
            self.stealth -= 1
            if self.stealth == 0:
                self.msg_extra("Stealth ended.", C_DIM)
        if self.poison_blade > 0:
            self.poison_blade -= 1
        # Regen
        if self.regen > 0:
            self.hp = min(self.hp + self.regen, self.max_hp)

    def msg_extra(self, text, color):
        pass  # Set by Game

    def unlock_skills(self):
        for lvl, sk in self.skills.items():
            if not sk["unlocked"] and self.level >= sk["unlock_level"]:
                sk["unlocked"] = True


# ── Item ─────────────────────────────────────────────────────────────────────
class Item:
    def __init__(self, name, emoji, x, y, itype, value):
        self.name, self.emoji = name, emoji
        self.x, self.y = x, y
        self.item_type, self.value = itype, value


# ── Floating Text ────────────────────────────────────────────────────────────
class FloatText:
    def __init__(self, x, y, text, color, life=30):
        self.x, self.y = x, y
        self.text, self.color = text, color
        self.life = self.max_life = life


# ── GAME ─────────────────────────────────────────────────────────────────────
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SW, SH))
        pygame.display.set_caption("Emoji Roguelike v3")
        self.clock = pygame.time.Clock()
        self.er = EmojiRenderer(TILE)

        self.fsm = pygame.font.SysFont("DejaVu Sans", 13)
        self.fmd = pygame.font.SysFont("DejaVu Sans", 16)
        self.flg = pygame.font.SysFont("DejaVu Sans", 21, bold=True)
        self.ftl = pygame.font.SysFont("DejaVu Sans", 32, bold=True)
        self.fxl = pygame.font.SysFont("DejaVu Sans", 48, bold=True)

        self.floor_s = self._floor_tile()
        self.wall_s = self.er.render(EMOJI["wall"])
        self.door_s = self.er.render(EMOJI["door"])
        self.stair_s = self.er.render(EMOJI["stairs"])
        self.pillar_s = self.er.render(EMOJI["pillar"])
        self.water_s = self.er.render(EMOJI["water"])
        self.lava_s = self.er.render(EMOJI["lava"])
        self.deco_s = {
            DECO_BONES:   self.er.render(EMOJI["bones"]),
            DECO_WEB:     self.er.render(EMOJI["web"]),
            DECO_CRYSTAL: self.er.render(EMOJI["crystal"]),
            DECO_MUSHROOM: self.er.render(EMOJI["mushroom"]),
            DECO_GRASS:   self.er.render(EMOJI["grass"]),
            DECO_ICE:     self.er.render(EMOJI["ice"]),
            DECO_FLOWERS: self.er.render(EMOJI["flower"]),
        }

        self.messages = deque(maxlen=80)
        self.floats = []
        self.state = "class_select"  # class_select, playing, levelup, game_over
        self.class_sel = 0
        self.class_keys = list(CLASS_DEFS.keys())
        self.player = None
        self.dungeon_level = 1
        self.game_over = False
        self.turn_count = 0
        self.explored = set()
        self.visible = set()
        self.enemies = []
        self.items = []
        self.dungeon = []
        self.rooms = []
        self.biome = "classic"
        self.feature_cache = {}

    def _floor_tile(self, biome="classic"):
        bp = BIOMES.get(biome, BIOMES["classic"])
        c1 = bp["floor"]
        c2 = bp["floor2"]
        s = pygame.Surface((TILE, TILE))
        s.fill(c1)
        pygame.draw.rect(s, c2, (0, 0, TILE, TILE), 1)
        # Add subtle random speckle for texture
        for _ in range(3):
            rx = random.randint(2, TILE - 3)
            ry = random.randint(2, TILE - 3)
            sc = tuple(max(0, min(255, c + random.randint(-8, 8))) for c in c1)
            pygame.draw.rect(s, sc, (rx, ry, 2, 2))
        return s

    def _rebuild_floor_tile(self):
        self.floor_s = self._floor_tile(self.biome)

    def msg(self, t, c=C_MSG):
        self.messages.append((t, c))

    def add_float(self, x, y, text, color):
        self.floats.append(FloatText(x * TILE, y * TILE - 10, text, color))

    # ── Level Gen ────────────────────────────────────────────────────────
    def _new_level(self):
        self.dungeon, self.rooms, self.biome = gen_dungeon(MW, MH, self.dungeon_level)
        self.feature_cache.clear()
        self._rebuild_floor_tile()
        bp = BIOMES.get(self.biome, BIOMES["classic"])
        self.msg(f"Biome: {bp['name']}", C_SPEC)
        self.explored = set()
        s = self.rooms[0]
        if self.player is None:
            return
        # Place player on a FLOOR tile in the first room
        placed = False
        for dy in range(s.h):
            for dx in range(s.w):
                tx, ty = s.x + dx, s.y + dy
                if 0 < tx < MW - 1 and 0 < ty < MH - 1 and self.dungeon[ty][tx] == FLOOR:
                    self.player.x, self.player.y = tx, ty
                    placed = True
                    break
            if placed:
                break
        if not placed:
            self.player.x, self.player.y = s.cx, s.cy
        self.enemies = []
        self._place_enemies()
        self.items = []
        self._place_items()
        self.visible = compute_fov(self.dungeon, self.player.x, self.player.y)
        self.explored.update(self.visible)

    def _place_enemies(self):
        num = 8 + self.dungeon_level * 3
        for _ in range(num):
            if len(self.rooms) < 2:
                break
            room = random.choice(self.rooms[1:])
            if room.w < 3 or room.h < 3:
                continue
            x = random.randint(room.x + 1, max(room.x + 1, room.x + room.w - 2))
            y = random.randint(room.y + 1, max(room.y + 1, room.y + room.h - 2))
            if self.dungeon[y][x] not in WALKABLE:
                continue
            if any(e.x == x and e.y == y for e in self.enemies):
                continue
            avail = [t for t in ENEMIES if t[8] <= self.dungeon_level]
            if not avail:
                avail = ENEMIES[:2]
            w = [1.0 / max(t[8], 0.5) for t in avail]
            tmpl = random.choices(avail, weights=w, k=1)[0]
            sc = 1 + (self.dungeon_level - 1) * 0.15
            name, ek, hp, atk, df, xp, gold, color, _, beh = tmpl
            self.enemies.append(Enemy(
                name, EMOJI[ek], x, y,
                int(hp * sc), int(atk * sc), int(df * sc),
                int(xp * sc), int(gold * sc), color, beh))
        # Boss every 5
        if self.dungeon_level % 5 == 0 and len(self.rooms) >= 2:
            br = self.rooms[-1]
            boss_names = {
                5:  ("Goblin King",    "boss_king"),
                10: ("Orc Warlord",    "boss_warlord"),
                15: ("Demon King",     "boss_king"),
                20: ("Lich Emperor",   "boss_emperor"),
                25: ("Elder Dragon",   "boss_elder"),
                30: ("Fire Overlord",  "boss_overlord"),
                35: ("Stone Titan",    "boss_titan"),
                40: ("Leviathan",      "boss_leviathan"),
                45: ("Arch-Lich",      "boss_archlich"),
                50: ("Dragon God",     "boss_dragon_god"),
            }
            bn, be = boss_names.get(
                ((self.dungeon_level - 1) // 5) * 5 + 5
                if self.dungeon_level <= 50
                else 50,
                (f"Floor {self.dungeon_level} Boss", "boss"))
            # Boss difficulty scales with floor tier
            tier = min((self.dungeon_level - 1) // 5, 10)
            boss_hp  = 70 + self.dungeon_level * 14 + tier * 20
            boss_atk = 14 + self.dungeon_level * 2 + tier * 2
            boss_df  = 6 + self.dungeon_level + tier
            boss_xp  = 120 + self.dungeon_level * 28 + tier * 40
            boss_gold= 60 + self.dungeon_level * 14 + tier * 25
            boss_beh = random.choice(["tank", "ranged", "chase"]) if tier >= 3 else "tank"
            self.enemies.append(Enemy(
                bn, EMOJI[be], br.cx, br.cy,
                boss_hp, boss_atk, boss_df,
                boss_xp, boss_gold, (255, 50, 50), boss_beh))

    def _place_items(self):
        num = 5 + self.dungeon_level * 2
        for _ in range(num):
            if len(self.rooms) < 2:
                break
            room = random.choice(self.rooms[1:])
            if room.w < 3 or room.h < 3:
                continue
            x = random.randint(room.x + 1, max(room.x + 1, room.x + room.w - 2))
            y = random.randint(room.y + 1, max(room.y + 1, room.y + room.h - 2))
            if self.dungeon[y][x] not in WALKABLE:
                continue
            if any(i.x == x and i.y == y for i in self.items):
                continue
            r = random.random()
            dl = self.dungeon_level
            if r < 0.25:
                it = Item("Health Potion", EMOJI["potion"], x, y,
                          "potion", 8 + dl * 2)
            elif r < 0.40:
                v = 1 + dl // 2
                it = Item(f"Sword +{v}", EMOJI["sword"], x, y, "weapon", v)
            elif r < 0.52:
                v = 1 + dl // 3
                it = Item(f"Shield +{v}", EMOJI["shield"], x, y, "armor", v)
            elif r < 0.72:
                v = random.randint(3, 10) * dl
                it = Item(f"Gold ({v})", EMOJI["gold"], x, y, "gold", v)
            elif r < 0.85:
                st = random.choice(["Fireball", "Teleport", "Shield"])
                it = Item(f"Scroll of {st}", EMOJI["scroll"], x, y,
                          "scroll", st)
            else:
                # Mana potion
                it = Item("Mana Crystal", EMOJI["zap"], x, y,
                          "mana", 5 + dl * 2)
            self.items.append(it)

    # ── Player Actions ───────────────────────────────────────────────────
    def move_player(self, dx, dy):
        if self.game_over or self.state != "playing":
            return
        p = self.player
        nx, ny = p.x + dx, p.y + dy
        if not (0 <= nx < MW and 0 <= ny < MH):
            return
        tile = self.dungeon[ny][nx]
        if tile == WALL or tile == PILLAR:
            return

        enemy = None
        for e in self.enemies:
            if e.alive and e.x == nx and e.y == ny:
                enemy = e
                break

        if enemy:
            self._attack(enemy)
        elif tile in (WATER, LAVA):
            # Hazard tiles: can't walk into them
            return
        else:
            old_x, old_y = p.x, p.y
            p.x, p.y = nx, ny
            self._pickup_items()
            # Opportunity attack: adjacent enemies hit you as you flee
            for e in self.enemies:
                if (e.alive and e.stun <= 0 and e.freeze <= 0
                        and abs(e.x - old_x) <= 1 and abs(e.y - old_y) <= 1
                        and abs(e.x - p.x) <= 1 and abs(e.y - p.y) <= 1):
                    oa_dmg = max(1, e.atk // 2 - p.get_total_def() // 2)
                    p.hp -= oa_dmg
                    self.msg(f"{e.name} opportunity attack! -{oa_dmg}", C_BAD)
                    self.add_float(p.x, p.y, f"-{oa_dmg}", C_BAD)
                    if p.hp <= 0:
                        p.hp = 0; self.game_over = True
                        self.state = "game_over"
                        self.msg("Slain while fleeing!", C_BAD)
                        return
            if self.dungeon[ny][nx] == STAIRS:
                self.dungeon_level += 1
                self.msg(f"Descend to floor {self.dungeon_level}!", C_SPEC)
                self._new_level()
                p.unlock_skills()
                return

        self._end_turn()

    def _attack(self, enemy, mult=1.0, is_skill=False):
        p = self.player
        total = p.get_total_atk()
        # Crit
        crit = random.randint(1, 100) <= p.crit_chance
        dmg_mult = mult * (2.0 if crit else 1.0)
        dmg = max(1, int(total * dmg_mult - enemy.defense + random.randint(-1, 2)))
        enemy.hp -= dmg
        crit_txt = " CRIT!" if crit else ""
        self.msg(f"Hit {enemy.name} for {dmg}!{crit_txt}", C_GOOD)
        self.add_float(enemy.x, enemy.y, f"-{dmg}", C_GOOD if not crit else C_GOLD)
        # Lifesteal
        if p.lifesteal > 0:
            heal = max(1, dmg * p.lifesteal // 100)
            p.hp = min(p.hp + heal, p.max_hp)
        # Poison blade
        if p.poison_blade > 0:
            enemy.poison = max(enemy.poison, p.poison_blade)
            enemy.poison_dmg = max(enemy.poison_dmg, p.poison_blade_dmg)
        if enemy.hp <= 0:
            self._kill_enemy(enemy)
        elif enemy.stun <= 0 and enemy.freeze <= 0:
            # Counter-attack (unless stunned/frozen)
            self._enemy_attack_player(enemy)

    def _kill_enemy(self, e):
        p = self.player
        e.alive = False
        p.xp += e.xp_reward
        p.gold += e.gold_reward
        p.kills += 1
        self.msg(f"{e.name} slain! +{e.xp_reward}XP +{e.gold_reward}G", C_SPEC)
        self.add_float(e.x, e.y, f"+{e.xp_reward}XP", C_SPEC)
        # Check level up
        self._check_level_up()

    def _enemy_attack_player(self, e):
        p = self.player
        # Dodge
        if random.randint(1, 100) <= p.dodge_chance:
            self.msg(f"Dodged {e.name}!", C_SPEC)
            return
        ed = max(1, e.atk - p.get_total_def() + random.randint(-1, 1))
        # Stealth reduces damage
        if p.stealth > 0:
            ed = max(1, ed // 2)
        p.hp -= ed
        self.msg(f"{e.name} hits you for {ed}!", C_BAD)
        self.add_float(p.x, p.y, f"-{ed}", C_BAD)
        # Vampire lifesteal
        if e.name == "Vampire":
            heal = ed // 2
            e.hp = min(e.hp + heal, e.max_hp)
        if p.hp <= 0:
            p.hp = 0
            self.game_over = True
            self.state = "game_over"
            self.msg("You have been slain!", C_BAD)

    def _check_level_up(self):
        p = self.player
        while p.xp >= p.xp_next:
            p.xp -= p.xp_next
            p.level += 1
            p.max_hp += 5
            p.hp = min(p.hp + 10, p.max_hp)
            p.max_mp += 3
            p.mp = min(p.mp + 5, p.max_mp)
            p.atk += 1
            p.defense += 1
            p.xp_next = int(p.xp_next * 1.4)
            p.pending_levelups += 1
            self.msg(f"LEVEL UP! Now level {p.level}!", C_PERK)
            p.unlock_skills()
        if p.pending_levelups > 0 and self.state == "playing":
            self._generate_levelup_choices()

    def _generate_levelup_choices(self):
        p = self.player
        choices = random.sample(PERK_POOL, min(3, len(PERK_POOL)))
        p.levelup_choices = list(choices)
        self.state = "levelup"

    def _apply_perk(self, perk):
        p = self.player
        name, desc, ptype, val = perk
        p.perks.append(name)
        if ptype == "max_hp":
            p.max_hp += val; p.hp = min(p.hp + val, p.max_hp)
        elif ptype == "atk":
            p.atk += val
        elif ptype == "df":
            p.defense += val
        elif ptype == "max_mp":
            p.max_mp += val; p.mp = min(p.mp + val, p.max_mp)
        elif ptype == "both_ad":
            p.atk += val; p.defense += val
        elif ptype == "hp_df":
            p.max_hp += 15; p.hp = min(p.hp + 15, p.max_hp); p.defense += 1
        elif ptype == "berserk_perk":
            p.atk += 4; p.defense = max(0, p.defense - 1)
        elif ptype == "regen":
            p.regen += val
        elif ptype == "crit":
            p.crit_chance += val
        elif ptype == "lifesteal":
            p.lifesteal += val
        elif ptype == "dodge":
            p.dodge_chance += val
        self.msg(f"Perk: {name} - {desc}", C_PERK)

    # ── Skills ───────────────────────────────────────────────────────────
    def use_skill(self, skill_idx):
        if self.game_over or self.state != "playing":
            return
        p = self.player
        skill_levels = sorted(p.skills.keys())
        if skill_idx >= len(skill_levels):
            return
        lvl = skill_levels[skill_idx]
        sk = p.skills[lvl]
        if not sk["unlocked"]:
            self.msg(f"Skill locked until level {sk['unlock_level']}.", C_DIM)
            return
        if sk["cd_current"] > 0:
            self.msg(f"{sk['name']} on cooldown ({sk['cd_current']} turns).", C_DIM)
            return

        stype = sk["type"]
        used = False

        if stype == "melee_boost":
            # Hit adjacent enemy with multiplier
            target = self._find_adjacent_enemy()
            if target:
                sk["cd_current"] = sk["cd"]
                self._attack(target, mult=sk["mult"], is_skill=True)
                used = True
            else:
                self.msg("No enemy adjacent!", C_BAD)

        elif stype == "stun":
            target = self._find_adjacent_enemy()
            if target:
                sk["cd_current"] = sk["cd"]
                self._attack(target, mult=sk["mult"], is_skill=True)
                if target.alive:
                    target.stun = sk["stun_dur"]
                    self.msg(f"{target.name} stunned for {sk['stun_dur']} turns!", C_SPEC)
                used = True
            else:
                self.msg("No enemy adjacent!", C_BAD)

        elif stype == "buff_atk":
            sk["cd_current"] = sk["cd"]
            p.buffs.append((sk["name"], sk["duration"], "atk", sk["amount"]))
            self.msg(f"{sk['name']}: +{sk['amount']} ATK for {sk['duration']} turns!", C_SPEC)
            used = True

        elif stype == "berserk":
            sk["cd_current"] = sk["cd"]
            p.buffs.append((sk["name"], sk["duration"], "atk",
                            int(p.get_total_atk() * (sk["mult"] - 1))))
            p.buffs.append(("Berserk Def", sk["duration"], "def", -sk["def_pen"]))
            self.msg(f"BERSERK! 3x ATK -{sk['def_pen']} DEF for {sk['duration']}t!", C_BAD)
            used = True

        elif stype == "aoe":
            sk["cd_current"] = sk["cd"]
            dmg = sk["base_dmg"] + p.level * sk["lvl_mult"]
            rad = sk["radius"]
            hit = 0
            for e in self.enemies:
                if e.alive and abs(e.x - p.x) <= rad and abs(e.y - p.y) <= rad:
                    e.hp -= dmg
                    self.add_float(e.x, e.y, f"-{dmg}", (255, 150, 50))
                    hit += 1
                    if e.hp <= 0:
                        self._kill_enemy(e)
            self.msg(f"Fireball! Hit {hit} enemies for {dmg}!", (255, 150, 50))
            used = True

        elif stype == "freeze":
            sk["cd_current"] = sk["cd"]
            target = self._nearest_visible_enemy(sk["range"])
            if target:
                target.freeze = sk["duration"]
                self.msg(f"{target.name} frozen for {sk['duration']} turns!", C_SPEC)
                self.add_float(target.x, target.y, "FROZEN!", (150, 200, 255))
                used = True
            else:
                self.msg("No enemy in range!", C_BAD)

        elif stype == "lightning":
            sk["cd_current"] = sk["cd"]
            vis_enemies = [e for e in self.enemies if e.alive and (e.x, e.y) in self.visible]
            if vis_enemies:
                target = random.choice(vis_enemies)
                dmg = max(1, int(p.get_total_atk() * sk["mult"] - target.defense))
                target.hp -= dmg
                self.add_float(target.x, target.y, f"-{dmg}", (255, 255, 100))
                self.msg(f"Lightning hits {target.name} for {dmg}!", (255, 255, 100))
                if target.hp <= 0:
                    self._kill_enemy(target)
                used = True
            else:
                self.msg("No visible target!", C_BAD)

        elif stype == "aoe_visible":
            sk["cd_current"] = sk["cd"]
            dmg = sk["base_dmg"] + p.level * sk["lvl_mult"]
            hit = 0
            for e in self.enemies:
                if e.alive and (e.x, e.y) in self.visible:
                    e.hp -= dmg
                    self.add_float(e.x, e.y, f"-{dmg}", (180, 100, 255))
                    hit += 1
                    if e.hp <= 0:
                        self._kill_enemy(e)
            self.msg(f"Arcane Nova! Hit {hit} for {dmg}!", (180, 100, 255))
            used = True

        elif stype == "backstab":
            sk["cd_current"] = sk["cd"]
            target = self._find_adjacent_enemy()
            if target:
                # Check if "behind" (simplified: always backstab in this context)
                self._attack(target, mult=sk["mult"], is_skill=True)
                used = True
            else:
                self.msg("No enemy adjacent!", C_BAD)

        elif stype == "shadow_step":
            sk["cd_current"] = sk["cd"]
            target = self._nearest_visible_enemy(sk["range"])
            if target:
                # Teleport behind enemy (opposite side from current position)
                dx = 1 if p.x <= target.x else -1
                dy = 1 if p.y <= target.y else -1
                nx, ny = target.x + dx, target.y + dy
                if (0 <= nx < MW and 0 <= ny < MH
                        and self.dungeon[ny][nx] in (FLOOR, STAIRS)):
                    p.x, p.y = nx, ny
                    self.msg(f"Shadow Step behind {target.name}!", C_SPEC)
                else:
                    # Fallback: teleport to any adjacent tile
                    for ddx, ddy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                        ax, ay = target.x + ddx, target.y + ddy
                        if (0 <= ax < MW and 0 <= ay < MH
                                and self.dungeon[ay][ax] in (FLOOR, STAIRS)
                                and not (ax == target.x and ay == target.y)):
                            p.x, p.y = ax, ay
                            break
                used = True
            else:
                self.msg("No target in range!", C_BAD)

        elif stype == "poison":
            sk["cd_current"] = sk["cd"]
            p.poison_blade = sk["duration"]
            p.poison_blade_dmg = sk["dot"]
            self.msg(f"Poison Blade! Next {sk['duration']} hits +{sk['dot']} poison/turn!", (100, 220, 80))
            used = True

        elif stype == "stealth":
            sk["cd_current"] = sk["cd"]
            p.stealth = sk["duration"]
            self.msg(f"Smoke Bomb! Invisible for {sk['duration']} turns!", C_SPEC)
            used = True

        elif stype == "heal":
            sk["cd_current"] = sk["cd"]
            heal = sk["base"] + p.level * sk["lvl_mult"]
            p.hp = min(p.hp + heal, p.max_hp)
            self.msg(f"Healed for {heal} HP!", C_GOOD)
            self.add_float(p.x, p.y, f"+{heal}", C_GOOD)
            used = True

        elif stype == "smite":
            sk["cd_current"] = sk["cd"]
            target = self._nearest_visible_enemy(8)
            if target:
                m = sk["undead_mult"] if target.name in UNDEAD_NAMES else sk["mult"]
                dmg = max(1, int(p.get_total_atk() * m - target.defense))
                target.hp -= dmg
                self.add_float(target.x, target.y, f"-{dmg}", (255, 255, 200))
                extra = " (holy!)" if target.name in UNDEAD_NAMES else ""
                self.msg(f"Smite {target.name} for {dmg}!{extra}", C_SPEC)
                if target.hp <= 0:
                    self._kill_enemy(target)
                used = True
            else:
                self.msg("No target in range!", C_BAD)

        elif stype == "buff_def":
            sk["cd_current"] = sk["cd"]
            p.buffs.append((sk["name"], sk["duration"], "def", sk["amount"]))
            self.msg(f"{sk['name']}: +{sk['amount']} DEF for {sk['duration']} turns!", C_SPEC)
            used = True

        elif stype == "wrath":
            sk["cd_current"] = sk["cd"]
            dmg_base = max(1, int(p.get_total_atk() * sk["mult"]))
            hit = 0
            for e in self.enemies:
                if e.alive:
                    d = max(1, dmg_base - e.defense)
                    e.hp -= d
                    self.add_float(e.x, e.y, f"-{d}", (255, 230, 150))
                    hit += 1
                    if e.hp <= 0:
                        self._kill_enemy(e)
            self.msg(f"Divine Wrath! Hit {hit} enemies!", (255, 230, 150))
            used = True

        if used:
            self._end_turn()

    def _find_adjacent_enemy(self):
        p = self.player
        for e in self.enemies:
            if e.alive and abs(e.x - p.x) <= 1 and abs(e.y - p.y) <= 1:
                return e
        return None

    def _nearest_visible_enemy(self, max_dist=8):
        p = self.player
        best, best_d = None, 999
        for e in self.enemies:
            if e.alive and (e.x, e.y) in self.visible:
                d = abs(e.x - p.x) + abs(e.y - p.y)
                if d <= max_dist and d < best_d:
                    best, best_d = e, d
        return best

    # ── Items ────────────────────────────────────────────────────────────
    def _pickup_items(self):
        p = self.player
        px, py = p.x, p.y
        grabbed = [i for i in self.items if i.x == px and i.y == py]
        for it in grabbed:
            self.items.remove(it)
            if it.item_type == "potion":
                p.potions += 1
                self.msg(f"Picked up {it.name}!", C_GOOD)
            elif it.item_type == "mana":
                p.mp = min(p.mp + it.value, p.max_mp)
                self.msg(f"Mana Crystal! +{it.value} MP!", (100, 150, 255))
            elif it.item_type == "weapon":
                if it.value > p.weapon_atk:
                    p.weapon_atk = it.value
                    self.msg(f"Equipped {it.name}! ATK+{it.value}", C_GOOD)
                else:
                    self.msg(f"Found {it.name}, keeping yours.", C_MSG)
            elif it.item_type == "armor":
                if it.value > p.armor_def:
                    p.armor_def = it.value
                    self.msg(f"Equipped {it.name}! DEF+{it.value}", C_GOOD)
                else:
                    self.msg(f"Found {it.name}, keeping yours.", C_MSG)
            elif it.item_type == "gold":
                p.gold += it.value
                self.msg(f"Found {it.value} gold!", C_GOLD)
            elif it.item_type == "scroll":
                self._use_scroll(it.value)

    def _use_scroll(self, st):
        if st == "Fireball":
            fd = 8 + self.player.level * 2
            hit = 0
            for e in self.enemies:
                if e.alive and (e.x, e.y) in self.visible:
                    e.hp -= fd; hit += 1
                    if e.hp <= 0:
                        self._kill_enemy(e)
            self.msg(f"Fireball! {hit} hit for {fd}!", (255, 150, 50))
        elif st == "Teleport":
            floors = [(x, y) for y in range(MH) for x in range(MW)
                      if self.dungeon[y][x] in (FLOOR, STAIRS)
                      and not any(e.alive and e.x == x and e.y == y
                                  for e in self.enemies)]
            if floors:
                self.player.x, self.player.y = random.choice(floors)
            self.msg("Teleported!", C_SPEC)
        elif st == "Shield":
            self.player.armor_def += 2
            self.msg("Shield spell! DEF+2", C_SPEC)

    def use_potion(self):
        if self.game_over or self.state != "playing":
            return
        p = self.player
        if p.potions > 0:
            heal = 10 + p.level * 3
            p.hp = min(p.hp + heal, p.max_hp)
            p.potions -= 1
            self.msg(f"Healed {heal} HP! ({p.potions} left)", C_GOOD)
            self.add_float(p.x, p.y, f"+{heal}", C_GOOD)
            self._end_turn()
        else:
            self.msg("No potions!", C_BAD)

    def wait_turn(self):
        if self.game_over or self.state != "playing":
            return
        self.msg("You wait...", C_DIM)
        self._end_turn()

    def _end_turn(self):
        p = self.player
        self.turn_count += 1
        p.tick_cooldowns()
        # Set the msg callback
        p.msg_extra = lambda t, c: self.msg(t, c)
        self._enemy_turn()
        self._tick_enemy_status()
        self.visible = compute_fov(self.dungeon, p.x, p.y)
        self.explored.update(self.visible)
        # Update floats
        self.floats = [f for f in self.floats if f.life > 0]
        for f in self.floats:
            f.life -= 1
            f.y -= 0.8

    # ── Enemy AI ─────────────────────────────────────────────────────────
    # ── Pathfinding ───────────────────────────────────────────────────
    def _bfs_path(self, sx, sy, tx, ty, max_dist=20):
        if sx == tx and sy == ty:
            return []
        visited = {(sx, sy)}
        queue = deque()
        queue.append((sx, sy, []))
        steps = 0
        while queue and steps < 500:
            steps += 1
            cx, cy, path = queue.popleft()
            if len(path) > max_dist:
                continue
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                if (nx, ny) in visited:
                    continue
                if not (0 <= nx < MW and 0 <= ny < MH):
                    continue
                if self.dungeon[ny][nx] not in WALKABLE:
                    continue
                if nx == tx and ny == ty:
                    return path + [(nx, ny)]
                blocked = any(o.alive and o.x == nx and o.y == ny
                              for o in self.enemies)
                if blocked:
                    continue
                visited.add((nx, ny))
                queue.append((nx, ny, path + [(nx, ny)]))
        return []

    def _bfs_next_step(self, sx, sy, tx, ty, max_dist=20):
        path = self._bfs_path(sx, sy, tx, ty, max_dist)
        return path[0] if path else None

    def _can_see_player(self, e, radius=10):
        dx = self.player.x - e.x
        dy = self.player.y - e.y
        dist = max(abs(dx), abs(dy))
        if dist > radius or dist == 0:
            return dist == 0
        sx_step = dx / dist
        sy_step = dy / dist
        cx, cy = e.x + 0.5, e.y + 0.5
        for _ in range(int(dist)):
            cx += sx_step
            cy += sy_step
            ix, iy = int(cx), int(cy)
            if ix == self.player.x and iy == self.player.y:
                return True
            if 0 <= ix < MW and 0 <= iy < MH:
                if self.dungeon[iy][ix] == WALL:
                    return False
        return True

    def _ally_count_adj(self, e, radius=2):
        return sum(1 for o in self.enemies
                   if o.alive and o is not e
                   and abs(o.x - e.x) <= radius and abs(o.y - e.y) <= radius)

    def _safe_tile(self, x, y, exclude=None):
        if not (0 <= x < MW and 0 <= y < MH):
            return False
        if self.dungeon[y][x] not in WALKABLE:
            return False
        if x == self.player.x and y == self.player.y:
            return False
        for o in self.enemies:
            if o.alive and o is not exclude and o.x == x and o.y == y:
                return False
        return True

    def _hp_pct(self, e):
        return e.hp / e.max_hp if e.max_hp > 0 else 0

    # ── Enemy AI Turn ────────────────────────────────────────────────────
    def _enemy_turn(self):
        p = self.player
        for e in self.enemies:
            if not e.alive:
                continue
            if e.ability_cooldown > 0:
                e.ability_cooldown -= 1
            if e.stun > 0:
                e.stun -= 1
                continue
            if e.freeze > 0:
                e.freeze -= 1
                continue
            if e.poison > 0:
                e.hp -= e.poison_dmg
                e.poison -= 1
                if e.hp <= 0:
                    self._kill_enemy(e)
                    continue

            can_see = self._can_see_player(e, 10)
            if can_see:
                e.last_seen_x, e.last_seen_y = p.x, p.y
                e.turns_since_seen = 0
            else:
                e.turns_since_seen += 1

            # Enrage at low HP
            if not e.enraged and self._hp_pct(e) < 0.3 and e.behavior != "explode":
                e.enraged = True
                e.atk += 2
                e.defense = max(0, e.defense - 1)

            dist = abs(e.x - p.x) + abs(e.y - p.y)

            # Stealth: mostly unaware
            if p.stealth > 0:
                if random.random() < 0.15 and can_see:
                    self._exec_ai(e, dist, can_see)
                elif random.random() < 0.3:
                    self._random_move(e)
                continue

            # Regen: heal while out of combat
            if e.behavior == "regen" and self._hp_pct(e) < 0.8 and dist > 5:
                heal = 3 + self.dungeon_level
                e.hp = min(e.hp + heal, e.max_hp)
                if random.random() < 0.3:
                    self._move_away(e)
                continue

            self._exec_ai(e, dist, can_see)

    def _exec_ai(self, e, dist, can_see):
        bh = e.behavior
        # Off-screen: move toward last known position
        if not can_see:
            if e.last_seen_x is not None and e.turns_since_seen <= 8:
                nxt = self._bfs_next_step(e.x, e.y, e.last_seen_x, e.last_seen_y, 12)
                if nxt and self._safe_tile(nxt[0], nxt[1], e):
                    e.x, e.y = nxt
            elif random.random() < 0.25:
                self._random_move(e)
            return
        # Dispatch
        if bh == "chase":
            self._ai_chase(e, dist)
        elif bh == "swarm":
            self._ai_swarm(e, dist)
        elif bh == "tank":
            self._ai_tank(e, dist)
        elif bh == "ranged":
            self._ai_ranged(e, dist)
        elif bh == "teleport":
            self._ai_teleport(e, dist)
        elif bh == "explode":
            self._ai_explode(e, dist)
        elif bh == "regen":
            self._ai_regen(e, dist)

    # ── CHASE: Smart pursuit with pathfinding ───────────────────────────
    def _ai_chase(self, e, dist):
        p = self.player
        if self._hp_pct(e) < 0.2 and random.random() < 0.6:
            self._smart_flee(e)
            return
        if dist <= 1:
            self._enemy_attack_player(e)
        else:
            nxt = self._bfs_next_step(e.x, e.y, p.x, p.y, 15)
            if nxt and self._safe_tile(nxt[0], nxt[1], e):
                e.x, e.y = nxt
                # Enraged: double-step 30% of time
                if e.enraged and random.random() < 0.3:
                    nxt2 = self._bfs_next_step(e.x, e.y, p.x, p.y, 14)
                    if nxt2 and self._safe_tile(nxt2[0], nxt2[1], e):
                        e.x, e.y = nxt2
            else:
                self._move_toward(e)

    # ── SWARM: Pack tactics with flanking ────────────────────────────────
    def _ai_swarm(self, e, dist):
        p = self.player
        allies_near = self._ally_count_adj(e, 3)
        pack_bonus = min(allies_near, 3)
        if self._hp_pct(e) < 0.15 and allies_near == 0:
            self._smart_flee(e)
            return
        if dist <= 1:
            old_atk = e.atk
            e.atk += pack_bonus
            self._enemy_attack_player(e)
            e.atk = old_atk
            if pack_bonus >= 2:
                self.msg(f"{e.name} pack attacks! (+{pack_bonus})", C_BAD)
        elif dist <= 10:
            if allies_near >= 2:
                self._flank_move(e)
            else:
                nxt = self._bfs_next_step(e.x, e.y, p.x, p.y, 15)
                if nxt and self._safe_tile(nxt[0], nxt[1], e):
                    e.x, e.y = nxt
                else:
                    self._move_toward(e)

    def _flank_move(self, e):
        p = self.player
        adj = [(p.x+dx, p.y+dy) for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]]
        open_sides = []
        for ax, ay in adj:
            if not self._safe_tile(ax, ay, e):
                continue
            if not any(o.alive and o is not e and o.x == ax and o.y == ay
                       for o in self.enemies):
                open_sides.append((ax, ay))
        if open_sides:
            target = random.choice(open_sides)
            nxt = self._bfs_next_step(e.x, e.y, target[0], target[1], 8)
            if nxt and self._safe_tile(nxt[0], nxt[1], e):
                e.x, e.y = nxt
                return
        nxt = self._bfs_next_step(e.x, e.y, p.x, p.y, 15)
        if nxt and self._safe_tile(nxt[0], nxt[1], e):
            e.x, e.y = nxt

    # ── TANK: Bodyblock, shove, protect allies ──────────────────────────
    def _ai_tank(self, e, dist):
        p = self.player
        hp_pct = self._hp_pct(e)
        # Brace at low HP
        if hp_pct < 0.5 and not hasattr(e, '_tank_braced'):
            e._tank_braced = True
            e.defense += 3
            self.msg(f"{e.name} braces! +3 DEF", C_BAD)
        if dist <= 1:
            self._enemy_attack_player(e)
            # Shove player back
            if random.random() < 0.25 and e.ability_cooldown == 0:
                self._tank_shove(e)
        elif dist <= 6:
            nxt = self._bfs_next_step(e.x, e.y, p.x, p.y, 15)
            if nxt and self._safe_tile(nxt[0], nxt[1], e):
                e.x, e.y = nxt
            else:
                self._move_toward(e)
        elif dist <= 10:
            if random.random() < 0.5:
                nxt = self._bfs_next_step(e.x, e.y, p.x, p.y, 15)
                if nxt and self._safe_tile(nxt[0], nxt[1], e):
                    e.x, e.y = nxt
        else:
            # Protect nearby low-HP allies
            for ally in self.enemies:
                if (ally.alive and ally is not e
                        and abs(ally.x - p.x) <= 2 and abs(ally.y - p.y) <= 2
                        and self._hp_pct(ally) < 0.4):
                    mx = (ally.x + p.x) // 2
                    my = (ally.y + p.y) // 2
                    nxt = self._bfs_next_step(e.x, e.y, mx, my, 8)
                    if nxt and self._safe_tile(nxt[0], nxt[1], e):
                        e.x, e.y = nxt
                        break

    def _tank_shove(self, e):
        p = self.player
        dx = 1 if p.x > e.x else -1 if p.x < e.x else 0
        dy = 1 if p.y > e.y else -1 if p.y < e.y else 0
        nx, ny = p.x + dx, p.y + dy
        if self._safe_tile_for_player(nx, ny):
            p.x, p.y = nx, ny
            self.msg(f"{e.name} shoves you back!", C_BAD)
            e.ability_cooldown = 4
            self.visible = compute_fov(self.dungeon, p.x, p.y)
            self.explored.update(self.visible)

    def _safe_tile_for_player(self, x, y):
        if not (0 <= x < MW and 0 <= y < MH):
            return False
        if self.dungeon[y][x] not in WALKABLE:
            return False
        if any(o.alive and o.x == x and o.y == y for o in self.enemies):
            return False
        return True

    # ── RANGED: Kiting with optimal range ────────────────────────────────
    def _ai_ranged(self, e, dist):
        p = self.player
        opt_min, opt_max = 3, 5
        if dist <= 1:
            self._enemy_attack_player(e)
            if random.random() < 0.5:
                self._smart_flee(e)
            return
        if opt_min <= dist <= opt_max:
            self._ranged_shot(e)
            if random.random() < 0.2:
                self._kite_reposition(e)
        elif dist < opt_min:
            self._smart_flee(e)
            if random.random() < 0.5:
                self._ranged_shot(e)
        elif dist <= 8:
            self._ranged_approach(e, dist)
        elif dist <= 12:
            if random.random() < 0.4:
                self._ranged_shot(e)
            elif random.random() < 0.5:
                nxt = self._bfs_next_step(e.x, e.y, p.x, p.y, 12)
                if nxt and self._safe_tile(nxt[0], nxt[1], e):
                    e.x, e.y = nxt

    def _ranged_shot(self, e):
        p = self.player
        if not self._can_see_player(e, 8):
            return
        dmg = max(1, e.atk - p.get_total_def() // 2 + random.randint(-1, 1))
        if random.randint(1, 100) <= 10:
            dmg = int(dmg * 1.5)
            self.msg(f"{e.name} crit shot! {dmg}!", (255, 200, 100))
        else:
            self.msg(f"{e.name} shoots for {dmg}!", C_BAD)
        p.hp -= dmg
        self.add_float(p.x, p.y, f"-{dmg}", C_BAD)
        if p.hp <= 0:
            p.hp = 0; self.game_over = True
            self.state = "game_over"
            self.msg("You have been slain!", C_BAD)

    def _kite_reposition(self, e):
        p = self.player
        dx = 1 if p.x >= e.x else -1
        dy = 1 if p.y >= e.y else -1
        laterals = [(dx, -dy), (-dx, dy)]
        random.shuffle(laterals)
        for lx, ly in laterals:
            if lx == 0 and ly == 0:
                continue
            nx, ny = e.x + lx, e.y + ly
            new_dist = abs(nx - p.x) + abs(ny - p.y)
            if self._safe_tile(nx, ny, e) and 2 <= new_dist <= 6:
                e.x, e.y = nx, ny
                return
        self._move_away(e)

    def _ranged_approach(self, e, dist):
        p = self.player
        nxt = self._bfs_next_step(e.x, e.y, p.x, p.y, 8)
        if nxt:
            new_dist = abs(nxt[0] - p.x) + abs(nxt[1] - p.y)
            if new_dist >= 2 and self._safe_tile(nxt[0], nxt[1], e):
                e.x, e.y = nxt
                return
        self._move_toward(e)

    # ── TELEPORT: Tactical blink ─────────────────────────────────────────
    def _ai_teleport(self, e, dist):
        # Low HP: blink away
        if self._hp_pct(e) < 0.25 and random.random() < 0.4 and e.ability_cooldown == 0:
            self._blink_away(e)
            e.ability_cooldown = 3
            return
        if dist <= 1:
            self._enemy_attack_player(e)
            if random.random() < 0.3 and e.ability_cooldown == 0:
                self._blink_away(e)
                e.ability_cooldown = 2
        elif dist <= 3:
            if e.ability_cooldown == 0 and random.random() < 0.5:
                self._blink_close(e)
                e.ability_cooldown = 3
            else:
                nxt = self._bfs_next_step(e.x, e.y, self.player.x, self.player.y, 8)
                if nxt and self._safe_tile(nxt[0], nxt[1], e):
                    e.x, e.y = nxt
        elif dist <= 8:
            if random.random() < 0.35 and e.ability_cooldown == 0:
                self._blink_close(e)
                e.ability_cooldown = 3
            else:
                nxt = self._bfs_next_step(e.x, e.y, self.player.x, self.player.y, 10)
                if nxt and self._safe_tile(nxt[0], nxt[1], e):
                    e.x, e.y = nxt
        elif dist <= 12 and e.ability_cooldown == 0 and random.random() < 0.2:
            self._blink_close(e)
            e.ability_cooldown = 3

    def _blink_close(self, e):
        p = self.player
        candidates = []
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                nx, ny = p.x + dx, p.y + dy
                d = abs(nx - p.x) + abs(ny - p.y)
                if 1 <= d <= 2 and self._safe_tile(nx, ny, e):
                    candidates.append((nx, ny))
        if candidates:
            best = [c for c in candidates
                    if not any(o.alive and o is not e
                               and abs(o.x - c[0]) <= 1 and abs(o.y - c[1]) <= 1
                               for o in self.enemies)]
            target = random.choice(best if best else candidates)
            e.x, e.y = target
            self.msg(f"{e.name} blinks near you!", C_BAD)

    def _blink_away(self, e):
        p = self.player
        candidates = []
        for y in range(max(0, e.y - 6), min(MH, e.y + 7)):
            for x in range(max(0, e.x - 6), min(MW, e.x + 7)):
                d = abs(x - p.x) + abs(y - p.y)
                if 5 <= d <= 8 and self._safe_tile(x, y, e):
                    candidates.append((x, y))
        if candidates:
            e.x, e.y = random.choice(candidates)
            self.msg(f"{e.name} blinks away!", C_SPEC)
        else:
            self._smart_flee(e)

    # ── EXPLODE: Charge + chain reactions ────────────────────────────────
    def _ai_explode(self, e, dist):
        p = self.player
        if dist <= 1:
            expl_dmg = e.atk * 2
            p.hp -= expl_dmg
            self.msg(f"{e.name} EXPLODES for {expl_dmg}!", (255, 100, 0))
            self.add_float(p.x, p.y, f"-{expl_dmg}", (255, 100, 0))
            e.alive = False
            # Chain reaction
            for o in self.enemies:
                if (o.alive and o is not e and o.behavior == "explode"
                        and abs(o.x - e.x) <= 2 and abs(o.y - e.y) <= 2):
                    o.atk += 2
                    o.charge_timer = 99
                    self.msg(f"{o.name} ignited by blast!", C_BAD)
            if p.hp <= 0:
                p.hp = 0; self.game_over = True
                self.state = "game_over"
                self.msg("You have been slain!", C_BAD)
        elif dist <= 3:
            e.charge_timer += 1
            nxt = self._bfs_next_step(e.x, e.y, p.x, p.y, 10)
            if nxt and self._safe_tile(nxt[0], nxt[1], e):
                e.x, e.y = nxt
            if e.charge_timer >= 2:
                nxt2 = self._bfs_next_step(e.x, e.y, p.x, p.y, 9)
                if nxt2 and self._safe_tile(nxt2[0], nxt2[1], e):
                    e.x, e.y = nxt2
        else:
            nxt = self._bfs_next_step(e.x, e.y, p.x, p.y, 15)
            if nxt and self._safe_tile(nxt[0], nxt[1], e):
                e.x, e.y = nxt
            else:
                self._move_toward(e)

    # ── REGEN: Adaptive aggression ───────────────────────────────────────
    def _ai_regen(self, e, dist):
        p = self.player
        hp_pct = self._hp_pct(e)
        if hp_pct < 0.3:
            self._smart_flee(e)
            e.hp = min(e.hp + 4 + self.dungeon_level, e.max_hp)
            return
        if hp_pct < 0.6:
            if dist <= 1:
                self._enemy_attack_player(e)
            elif dist <= 4:
                e.hp = min(e.hp + 2, e.max_hp)
                if random.random() < 0.4:
                    self._move_away(e)
                else:
                    nxt = self._bfs_next_step(e.x, e.y, p.x, p.y, 10)
                    if nxt and self._safe_tile(nxt[0], nxt[1], e):
                        e.x, e.y = nxt
            return
        if dist <= 1:
            self._enemy_attack_player(e)
        elif dist <= 10:
            nxt = self._bfs_next_step(e.x, e.y, p.x, p.y, 15)
            if nxt and self._safe_tile(nxt[0], nxt[1], e):
                e.x, e.y = nxt
            else:
                self._move_toward(e)

    # ── Smart Flee: prefers cover ────────────────────────────────────────
    def _smart_flee(self, e):
        p = self.player
        best = None
        best_score = -1
        for dx, dy in [(0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]:
            nx, ny = e.x + dx, e.y + dy
            if self._safe_tile(nx, ny, e):
                d = abs(nx - p.x) + abs(ny - p.y)
                walls = sum(1 for wx, wy in [(nx+1,ny),(nx-1,ny),(nx,ny+1),(nx,ny-1)]
                             if 0 <= wx < MW and 0 <= wy < MH and self.dungeon[wy][wx] == WALL)
                score = d + walls * 0.5
                if score > best_score:
                    best_score = score
                    best = (nx, ny)
        if best:
            e.x, e.y = best
        else:
            self._move_away(e)

    # ── Movement Helpers ────────────────────────────────────────────────
    def _move_toward(self, e):
        p = self.player
        dx = (1 if e.x < p.x else -1 if e.x > p.x else 0)
        dy = (1 if e.y < p.y else -1 if e.y > p.y else 0)
        for mx, my in [(dx, 0), (0, dy), (dx, dy), (dy, dx)]:
            if mx == 0 and my == 0:
                continue
            if self._safe_tile(e.x + mx, e.y + my, e):
                e.x, e.y = e.x + mx, e.y + my
                break

    def _move_away(self, e):
        p = self.player
        dx = (-1 if e.x < p.x else 1 if e.x > p.x else 0)
        dy = (-1 if e.y < p.y else 1 if e.y > p.y else 0)
        for mx, my in [(dx, 0), (0, dy), (dx, dy)]:
            if mx == 0 and my == 0:
                continue
            if self._safe_tile(e.x + mx, e.y + my, e):
                e.x, e.y = e.x + mx, e.y + my
                break

    def _random_move(self, e):
        dirs = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        random.shuffle(dirs)
        for dx, dy in dirs:
            if self._safe_tile(e.x + dx, e.y + dy, e):
                e.x, e.y = e.x + dx, e.y + dy
                break

    def _tick_enemy_status(self):
        for e in self.enemies:
            if not e.alive:
                continue
            if e.stun > 0:
                pass  # handled in _enemy_turn
            if e.poison > 0:
                e.hp -= e.poison_dmg
                e.poison -= 1
                self.add_float(e.x, e.y, f"-{e.poison_dmg}", (100, 220, 80))
                if e.hp <= 0:
                    self._kill_enemy(e)

    # ── Drawing ──────────────────────────────────────────────────────────
    def draw(self):
        self.screen.fill(C_BG)
        if self.state == "class_select":
            self._draw_class_select()
        elif self.state in ("playing", "levelup"):
            self._draw_map()
            self._draw_floats()
            self._draw_sidebar()
            if self.state == "levelup":
                self._draw_levelup()
        elif self.state == "game_over":
            self._draw_map()
            self._draw_sidebar()
            self._draw_game_over()

    def _draw_class_select(self):
        cx, cy = SW // 2, SH // 2
        # Title
        t = self.fxl.render("EMOJI ROGUELIKE", True, C_TXT)
        self.screen.blit(t, (cx - t.get_width() // 2, 40))
        t2 = self.flg.render("Choose Your Class", True, C_SPEC)
        self.screen.blit(t2, (cx - t2.get_width() // 2, 100))

        keys = self.class_keys
        card_w, card_h = 220, 320
        gap = 30
        total_w = len(keys) * card_w + (len(keys) - 1) * gap
        start_x = cx - total_w // 2
        start_y = 160

        for i, ck in enumerate(keys):
            cd = CLASS_DEFS[ck]
            x = start_x + i * (card_w + gap)
            y = start_y
            selected = (i == self.class_sel)

            # Card background
            bg_col = (40, 40, 65) if not selected else (50, 50, 80)
            pygame.draw.rect(self.screen, bg_col, (x, y, card_w, card_h),
                             border_radius=12)
            border_col = cd["color"] if selected else C_SBB
            pygame.draw.rect(self.screen, border_col, (x, y, card_w, card_h),
                             width=3 if selected else 1, border_radius=12)

            # Class emoji
            es = self.er.render(EMOJI[cd["emoji"]])
            if es:
                self.screen.blit(es, (x + card_w // 2 - es.get_width() // 2, y + 15))

            # Class name
            ns = self.flg.render(cd["name"], True, cd["color"])
            self.screen.blit(ns, (x + card_w // 2 - ns.get_width() // 2, y + 65))

            # Description
            ds1 = self.fsm.render(cd["desc"], True, C_TXT)
            ds2 = self.fsm.render(cd["desc2"], True, C_TXT)
            self.screen.blit(ds1, (x + card_w // 2 - ds1.get_width() // 2, y + 95))
            self.screen.blit(ds2, (x + card_w // 2 - ds2.get_width() // 2, y + 112))

            # Stats
            sy = y + 140
            for label, val in [("HP", cd["hp"]), ("ATK", cd["atk"]),
                                ("DEF", cd["df"]), ("MP", cd["mp"])]:
                col = C_HP if label == "HP" else C_SPEC if label == "ATK" else \
                      C_XP if label == "DEF" else C_MP
                self.screen.blit(self.fmd.render(f"{label}: {val}", True, col),
                                 (x + 20, sy))
                sy += 22

            # Skills preview
            sy += 10
            self.screen.blit(self.fmd.render("Skills:", True, C_GOLD), (x + 20, sy))
            sy += 22
            for lvl in sorted(cd["skills"].keys()):
                sk = cd["skills"][lvl]
                semoji = self.er.render(EMOJI.get(sk["emoji"], ""))
                txt = f"L{lvl}: {sk['name']}"
                self.screen.blit(self.fsm.render(txt, True, C_DIM), (x + 25, sy))
                if semoji:
                    self.screen.blit(semoji, (x + card_w - 45, sy - 2))
                sy += 18

        # Controls hint
        hint = self.fmd.render("Arrow Keys: Select   ENTER: Start", True, C_DIM)
        self.screen.blit(hint, (cx - hint.get_width() // 2, SH - 50))

    def _draw_map(self):
        p = self.player
        for y in range(MH):
            for x in range(MW):
                sx, sy = x * TILE, y * TILE
                if (x, y) in self.visible:
                    tile = self.dungeon[y][x]
                    if tile == WALL:
                        self.screen.blit(self.wall_s, (sx, sy))
                    elif tile == FLOOR:
                        self.screen.blit(self.floor_s, (sx, sy))
                    elif tile == DOOR:
                        self.screen.blit(self.floor_s, (sx, sy))
                        self.screen.blit(self.door_s, (sx, sy))
                    elif tile == STAIRS:
                        self.screen.blit(self.floor_s, (sx, sy))
                        self.screen.blit(self.stair_s, (sx, sy))
                    elif tile == PILLAR:
                        self.screen.blit(self.floor_s, (sx, sy))
                        self.screen.blit(self.pillar_s, (sx, sy))
                    elif tile == WATER:
                        # Animated-ish water tile
                        key = ("water", x, y)
                        if key not in self.feature_cache:
                            ws = pygame.Surface((TILE, TILE))
                            ws.fill((20, 50, 90))
                            pygame.draw.rect(ws, (30, 70, 120), (0, 0, TILE, TILE), 1)
                            # Water ripples
                            for wy in range(5, TILE - 5, 8):
                                wave_x = 3 + (wy * 7 + x * 3) % (TILE - 8)
                                pygame.draw.arc(ws, (60, 120, 180),
                                              (wave_x, wy, 10, 4), 0, 3.14, 1)
                            wsurf = self.er.render(EMOJI["water"])
                            if wsurf:
                                ws.blit(wsurf, (TILE // 2 - wsurf.get_width() // 2,
                                               TILE // 2 - wsurf.get_height() // 2))
                            self.feature_cache[key] = ws
                        self.screen.blit(self.feature_cache[key], (sx, sy))
                    elif tile == LAVA:
                        key = ("lava", x, y)
                        if key not in self.feature_cache:
                            ls = pygame.Surface((TILE, TILE))
                            ls.fill((80, 20, 10))
                            pygame.draw.rect(ls, (120, 40, 15), (0, 0, TILE, TILE), 1)
                            lsurf = self.er.render(EMOJI["lava"])
                            if lsurf:
                                ls.blit(lsurf, (TILE // 2 - lsurf.get_width() // 2,
                                               TILE // 2 - lsurf.get_height() // 2))
                            self.feature_cache[key] = ls
                        self.screen.blit(self.feature_cache[key], (sx, sy))
                    elif tile in self.deco_s:
                        # Walkable decorative tile
                        self.screen.blit(self.floor_s, (sx, sy))
                        ds = self.deco_s.get(tile)
                        if ds:
                            self.screen.blit(ds, (sx, sy))
                    for it in self.items:
                        if it.x == x and it.y == y:
                            s = self.er.render(it.emoji)
                            if s:
                                self.screen.blit(s, (sx, sy))
                    # Enemies
                    for e in self.enemies:
                        if e.alive and e.x == x and e.y == y:
                            s = self.er.render(e.emoji)
                            if s:
                                self.screen.blit(s, (sx, sy))
                            # Status indicators
                            if e.stun > 0:
                                pygame.draw.rect(self.screen, (255, 255, 0),
                                                 (sx, sy, TILE, TILE), 2)
                            elif e.freeze > 0:
                                pygame.draw.rect(self.screen, (100, 180, 255),
                                                 (sx, sy, TILE, TILE), 2)
                            elif e.poison > 0:
                                pygame.draw.rect(self.screen, (100, 220, 80),
                                                 (sx, sy, TILE, TILE), 2)
                            elif e.enraged:
                                pygame.draw.rect(self.screen, (255, 80, 80),
                                                 (sx, sy, TILE, TILE), 2)
                            # HP bar
                            if e.hp < e.max_hp:
                                bw = TILE - 4
                                pygame.draw.rect(self.screen, C_HPB,
                                                 (sx + 2, sy - 2, bw, 4))
                                fw = int(bw * e.hp / e.max_hp)
                                pygame.draw.rect(self.screen, C_HP,
                                                 (sx + 2, sy - 2, fw, 4))
                    # Player
                    if p.x == x and p.y == y:
                        s = self.er.render(p.emoji)
                        if s:
                            if p.stealth > 0:
                                s = s.copy()
                                s.set_alpha(128)
                            self.screen.blit(s, (sx, sy))
                        pygame.draw.rect(self.screen, C_SEL,
                                         (sx, sy, TILE, TILE), 2, border_radius=4)
                elif (x, y) in self.explored:
                    tile = self.dungeon[y][x]
                    if tile == WALL:
                        self.screen.blit(self.wall_s, (sx, sy))
                    elif tile in WALKABLE or tile in (PILLAR, WATER, LAVA):
                        self.screen.blit(self.floor_s, (sx, sy))
                        if tile == PILLAR:
                            self.screen.blit(self.pillar_s, (sx, sy))
                    dim = pygame.Surface((TILE, TILE))
                    dim.fill(C_FOG); dim.set_alpha(180)
                    self.screen.blit(dim, (sx, sy))
                else:
                    pygame.draw.rect(self.screen, C_FOG, (sx, sy, TILE, TILE))

    def _draw_floats(self):
        for f in self.floats:
            alpha = int(255 * f.life / f.max_life)
            s = self.fmd.render(f.text, True, f.color)
            s.set_alpha(alpha)
            self.screen.blit(s, (int(f.x), int(f.y)))

    def _draw_sidebar(self):
        p = self.player
        sbx = MW * TILE
        pygame.draw.rect(self.screen, C_SB, (sbx, 0, SBW, SH))
        pygame.draw.line(self.screen, C_SBB, (sbx, 0), (sbx, SH), 2)
        x, y = sbx + 12, 10

        # Class icon + name
        cls = CLASS_DEFS[p.cls_key]
        es = self.er.render(EMOJI[cls["emoji"]])
        if es:
            self.screen.blit(es, (x, y))
        self._lbl(x + TILE, y + 5, f'{cls["name"]} Lv.{p.level}', cls["color"], self.flg)
        y += 42
        pygame.draw.line(self.screen, C_SBB, (x, y), (sbx + SBW - 12, y))
        y += 8

        self._lbl(x, y, f"Floor: {self.dungeon_level}  Turns: {self.turn_count}",
                  C_DIM, self.fsm); y += 16
        bp = BIOMES.get(self.biome, BIOMES["classic"])
        self._lbl(x, y, f"Biome: {bp['name']}",
                  C_SPEC, self.fsm); y += 16
        self._lbl(x, y, f"Kills: {p.kills}  Perks: {len(p.perks)}",
                  C_DIM, self.fsm); y += 20

        # HP bar
        self._bar(x, y, "HP", p.hp, p.max_hp, C_HP, C_HPB); y += 24
        # MP bar
        self._bar(x, y, "MP", p.mp, p.max_mp, C_MP, C_MPB); y += 24
        # XP bar
        self._bar(x, y, "XP", p.xp, p.xp_next, C_XP, C_XPB); y += 24

        # Stats
        ta = p.get_total_atk()
        td = p.get_total_def()
        self._lbl(x, y, f"ATK:{p.atk}(+{p.weapon_atk})={ta}  DEF:{p.defense}(+{p.armor_def})={td}",
                  C_TXT, self.fsm); y += 16
        # Passive stats
        passives = []
        if p.crit_chance > 5:
            passives.append(f"Crit:{p.crit_chance}%")
        if p.dodge_chance > 0:
            passives.append(f"Dodge:{p.dodge_chance}%")
        if p.regen > 0:
            passives.append(f"Regen:{p.regen}")
        if p.lifesteal > 0:
            passives.append(f"LS:{p.lifesteal}%")
        if passives:
            self._lbl(x, y, "  ".join(passives), C_PERK, self.fsm)
        y += 20

        # Buffs
        if p.buffs:
            buff_txt = "  ".join(f"{n}({t})" for n, t, _, _ in p.buffs)
            self._lbl(x, y, buff_txt[:38], (200, 200, 100), self.fsm)
            y += 16
        if p.stealth > 0:
            self._lbl(x, y, f"Stealth: {p.stealth}t", C_SPEC, self.fsm)
            y += 16
        if p.poison_blade > 0:
            self._lbl(x, y, f"Poison Blade: {p.poison_blade} hits", (100, 220, 80), self.fsm)
            y += 16

        # Gold & Potions
        gs = self.er.render(EMOJI["gold"])
        if gs:
            self.screen.blit(gs, (x, y))
        self._lbl(x + TILE - 2, y + 2, f"  {p.gold}", C_GOLD, self.fmd)
        ps = self.er.render(EMOJI["potion"])
        if ps:
            self.screen.blit(ps, (x + 110, y))
        self._lbl(x + 110 + TILE - 2, y + 2, f"  {p.potions} [P]", C_GOOD, self.fsm)
        y += TILE + 6

        # Skills
        pygame.draw.line(self.screen, C_SBB, (x, y), (sbx + SBW - 12, y))
        y += 6
        self._lbl(x, y, "SKILLS", C_TXT, self.fmd); y += 20
        skill_levels = sorted(p.skills.keys())
        for si, lvl in enumerate(skill_levels):
            sk = p.skills[lvl]
            key_str = f"[{si + 1}]"
            if sk["unlocked"]:
                semoji = self.er.render(EMOJI.get(sk["emoji"], ""))
                if sk["cd_current"] > 0:
                    col = C_CD
                    status = f"CD:{sk['cd_current']}"
                else:
                    col = C_CD_READY
                    status = "Ready"
                self._lbl(x, y, f"{key_str} {sk['name']} {status}", col, self.fsm)
                if semoji:
                    self.screen.blit(semoji, (sbx + SBW - 48, y - 2))
            else:
                self._lbl(x, y, f"{key_str} ??? (Lv.{sk['unlock_level']})", C_DIM, self.fsm)
                ls = self.er.render(EMOJI["lock"])
                if ls:
                    self.screen.blit(ls, (sbx + SBW - 48, y - 2))
            y += 17

        y += 6
        pygame.draw.line(self.screen, C_SBB, (x, y), (sbx + SBW - 12, y))
        y += 6

        # Messages log
        self._lbl(x, y, "LOG", C_TXT, self.fmd); y += 18
        max_msgs = max(1, (SH - y - 80) // 14)
        for text, color in list(self.messages)[-max_msgs:]:
            dt = text[:40] + ".." if len(text) > 42 else text
            self._lbl(x, y, dt, color, self.fsm)
            y += 14
            if y > SH - 75:
                break

        # Controls
        y = SH - 65
        pygame.draw.line(self.screen, C_SBB, (x, y), (sbx + SBW - 12, y))
        y += 8
        for line in ["WASD/Arrows: Move  1-4: Skills",
                     "P: Potion  SPACE: Wait  R: Restart",
                     "Q/E/Z/C: Diagonal  ESC: Quit"]:
            self._lbl(x, y, line, C_DIM, self.fsm)
            y += 14

    def _draw_levelup(self):
        # Overlay
        ov = pygame.Surface((SW, SH)); ov.fill((0, 0, 0)); ov.set_alpha(160)
        self.screen.blit(ov, (0, 0))
        cx = MW * TILE // 2
        cy = SH // 2

        p = self.player
        bw, bh = 500, 250
        bx, by = cx - bw // 2, cy - bh // 2
        pygame.draw.rect(self.screen, (30, 30, 50), (bx, by, bw, bh), border_radius=12)
        pygame.draw.rect(self.screen, C_PERK, (bx, by, bw, bh), width=3, border_radius=12)

        t = self.flg.render(f"Level Up! Choose a Perk (Lv.{p.level})", True, C_PERK)
        self.screen.blit(t, (cx - t.get_width() // 2, by + 15))

        choices = p.levelup_choices
        for i, (name, desc, _, _) in enumerate(choices):
            ix = bx + 30
            iy = by + 65 + i * 55
            # Card
            sel_col = (50, 50, 75)
            pygame.draw.rect(self.screen, sel_col,
                             (ix, iy, bw - 60, 45), border_radius=8)
            pygame.draw.rect(self.screen, C_SEL,
                             (ix, iy, bw - 60, 45), width=2, border_radius=8)
            self._lbl(ix + 15, iy + 5, f"[{i + 1}] {name}", C_PERK, self.fmd)
            self._lbl(ix + 15, iy + 24, desc, C_TXT, self.fsm)

        hint = self.fsm.render(f"Press 1-{len(choices)} to choose", True, C_DIM)
        self.screen.blit(hint, (cx - hint.get_width() // 2, by + bh - 30))

    def _draw_game_over(self):
        ov = pygame.Surface((SW, SH)); ov.fill((0, 0, 0)); ov.set_alpha(150)
        self.screen.blit(ov, (0, 0))
        cx = MW * TILE // 2; cy = SH // 2
        bw, bh = 420, 280
        bx, by = cx - bw // 2, cy - bh // 2
        pygame.draw.rect(self.screen, (30, 15, 15), (bx, by, bw, bh), border_radius=12)
        pygame.draw.rect(self.screen, (180, 50, 50), (bx, by, bw, bh), width=3, border_radius=12)

        t = self.ftl.render("GAME OVER", True, (255, 80, 80))
        self.screen.blit(t, (cx - t.get_width() // 2, by + 15))
        sk = self.er.render(EMOJI["skeleton"])
        if sk:
            self.screen.blit(sk, (cx - sk.get_width() // 2, by + 60))

        p = self.player
        cls = CLASS_DEFS[p.cls_key]
        lines = [
            f"{cls['name']} Level {p.level}  Floor {self.dungeon_level}",
            f"Kills: {p.kills}  Gold: {p.gold}  Perks: {len(p.perks)}",
            f"Turns survived: {self.turn_count}",
            f"Perks: {', '.join(p.perks) if p.perks else 'None'}",
        ]
        for i, line in enumerate(lines):
            s = self.fmd.render(line, True, C_TXT)
            self.screen.blit(s, (cx - s.get_width() // 2, by + 110 + i * 25))
        r = self.fsm.render("[R] Class Select  [ESC] Quit", True, C_DIM)
        self.screen.blit(r, (cx - r.get_width() // 2, by + bh - 30))

    def _lbl(self, x, y, text, color, font):
        self.screen.blit(font.render(str(text), True, color), (x, y))

    def _bar(self, x, y, label, cur, mx, fill, bg):
        bw = SBW - 35
        self._lbl(x, y, label, C_TXT, self.fsm)
        pygame.draw.rect(self.screen, bg, (x + 25, y + 1, bw - 25, 14), border_radius=3)
        if mx > 0:
            fw = int((bw - 25) * min(cur, mx) / mx)
            if fw > 0:
                pygame.draw.rect(self.screen, fill, (x + 25, y + 1, fw, 14), border_radius=3)
        self._lbl(x + 27, y, f"{cur}/{mx}", C_TXT, self.fsm)

    # ── Restart ──────────────────────────────────────────────────────────
    def restart(self):
        self.state = "class_select"
        self.class_sel = 0
        self.player = None
        self.dungeon_level = 1
        self.messages.clear()
        self.floats.clear()
        self.game_over = False
        self.turn_count = 0
        self.explored = set()
        self.enemies = []
        self.items = []

    def start_game(self, cls_key):
        cd = CLASS_DEFS[cls_key]
        self.state = "playing"
        self.dungeon_level = 1
        self.messages.clear()
        self.floats.clear()
        self.game_over = False
        self.turn_count = 0
        self.explored = set()
        self.enemies = []
        self.items = []

        # Generate first level
        self.dungeon, self.rooms, self.biome = gen_dungeon(MW, MH, 1)
        self.feature_cache.clear()
        self._rebuild_floor_tile()
        bp = BIOMES.get(self.biome, BIOMES["classic"])
        s = self.rooms[0]
        # Place player on a FLOOR tile in first room
        px, py = s.cx, s.cy
        for dy in range(s.h):
            for dx in range(s.w):
                tx, ty = s.x + dx, s.y + dy
                if 0 < tx < MW - 1 and 0 < ty < MH - 1 and self.dungeon[ty][tx] == FLOOR:
                    px, py = tx, ty
                    break
            else:
                continue
            break
        self.player = Player(cls_key, px, py)
        self.msg(f"Biome: {bp['name']}", C_SPEC)
        self._place_enemies()
        self._place_items()
        self.visible = compute_fov(self.dungeon, self.player.x, self.player.y)
        self.explored.update(self.visible)

        self.msg(f"You enter the dungeon as a {cd['name']}!", C_SPEC)
        self.msg("WASD/Arrows move. 1-4 skills. Bump to attack.", C_MSG)
        self.msg("[P] Potion  [SPACE] Wait  [R] Restart", C_MSG)

    # ── Main Loop ────────────────────────────────────────────────────────
    def run(self):
        running = True
        while running:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False
                elif ev.type == pygame.KEYDOWN:
                    k = ev.key
                    if self.state == "class_select":
                        if k in (pygame.K_LEFT, pygame.K_a):
                            self.class_sel = (self.class_sel - 1) % len(self.class_keys)
                        elif k in (pygame.K_RIGHT, pygame.K_d):
                            self.class_sel = (self.class_sel + 1) % len(self.class_keys)
                        elif k == pygame.K_RETURN or k == pygame.K_KP_ENTER:
                            self.start_game(self.class_keys[self.class_sel])
                        elif k == pygame.K_1:
                            self.start_game(self.class_keys[0])
                        elif k == pygame.K_2:
                            self.start_game(self.class_keys[1])
                        elif k == pygame.K_3:
                            self.start_game(self.class_keys[2])
                        elif k == pygame.K_4:
                            self.start_game(self.class_keys[3])
                        elif k == pygame.K_ESCAPE:
                            running = False

                    elif self.state == "levelup":
                        p = self.player
                        choices = p.levelup_choices
                        if k == pygame.K_1 and len(choices) >= 1:
                            self._apply_perk(choices[0])
                            p.pending_levelups -= 1
                            if p.pending_levelups > 0:
                                self._generate_levelup_choices()
                            else:
                                self.state = "playing"
                                p.levelup_choices = []
                        elif k == pygame.K_2 and len(choices) >= 2:
                            self._apply_perk(choices[1])
                            p.pending_levelups -= 1
                            if p.pending_levelups > 0:
                                self._generate_levelup_choices()
                            else:
                                self.state = "playing"
                                p.levelup_choices = []
                        elif k == pygame.K_3 and len(choices) >= 3:
                            self._apply_perk(choices[2])
                            p.pending_levelups -= 1
                            if p.pending_levelups > 0:
                                self._generate_levelup_choices()
                            else:
                                self.state = "playing"
                                p.levelup_choices = []

                    elif self.state == "playing":
                        if k == pygame.K_ESCAPE:
                            running = False
                        elif k == pygame.K_r:
                            self.restart()
                        elif k == pygame.K_p:
                            self.use_potion()
                        elif k == pygame.K_SPACE:
                            self.wait_turn()
                        elif k in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                            self.use_skill(k - pygame.K_1)
                        elif not self.game_over:
                            moves = {
                                pygame.K_UP: (0, -1), pygame.K_w: (0, -1), pygame.K_KP8: (0, -1),
                                pygame.K_DOWN: (0, 1), pygame.K_s: (0, 1), pygame.K_KP2: (0, 1),
                                pygame.K_LEFT: (-1, 0), pygame.K_a: (-1, 0), pygame.K_KP4: (-1, 0),
                                pygame.K_RIGHT: (1, 0), pygame.K_d: (1, 0), pygame.K_KP6: (1, 0),
                                pygame.K_q: (-1, -1), pygame.K_e: (1, -1),
                                pygame.K_z: (-1, 1), pygame.K_c: (1, 1),
                            }
                            if k in moves:
                                self.move_player(*moves[k])

                    elif self.state == "game_over":
                        if k == pygame.K_r:
                            self.restart()
                        elif k == pygame.K_ESCAPE:
                            running = False

            self.draw()
            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()