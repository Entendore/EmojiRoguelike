use rand::Rng;
use std::collections::HashSet;

pub const MAP_WIDTH: usize = 50;
pub const MAP_HEIGHT: usize = 25;
pub const MAX_FLOOR: usize = 15;

// ─── Biome System ────────────────────────────────────────────────────

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Biome {
    StoneDungeon,
    CrystalCavern,
    EnchantedForest,
    FrozenDepths,
    VolcanicCore,
    PoisonSwamp,
    HauntedGraveyard,
}

impl Biome {
    pub fn from_floor(floor: usize) -> Self {
        match floor {
            1..=2 => Biome::StoneDungeon,
            3..=4 => Biome::CrystalCavern,
            5..=6 => Biome::EnchantedForest,
            7..=8 => Biome::FrozenDepths,
            9..=10 => Biome::VolcanicCore,
            11..=12 => Biome::PoisonSwamp,
            13..=15 => Biome::HauntedGraveyard,
            _ => Biome::StoneDungeon,
        }
    }

    pub fn name(&self) -> &'static str {
        match self {
            Biome::StoneDungeon => "Stone Dungeon",
            Biome::CrystalCavern => "Crystal Cavern",
            Biome::EnchantedForest => "Enchanted Forest",
            Biome::FrozenDepths => "Frozen Depths",
            Biome::VolcanicCore => "Volcanic Core",
            Biome::PoisonSwamp => "Poison Swamp",
            Biome::HauntedGraveyard => "Haunted Graveyard",
        }
    }

    pub fn emoji(&self) -> &'static str {
        match self {
            Biome::StoneDungeon => "🏰",
            Biome::CrystalCavern => "💎",
            Biome::EnchantedForest => "🌲",
            Biome::FrozenDepths => "❄️",
            Biome::VolcanicCore => "🌋",
            Biome::PoisonSwamp => "🌿",
            Biome::HauntedGraveyard => "🪦",
        }
    }

    pub fn wall_emoji(&self) -> &'static str {
        match self {
            Biome::StoneDungeon => "🧱",
            Biome::CrystalCavern => "💠",
            Biome::EnchantedForest => "🌲",
            Biome::FrozenDepths => "🧊",
            Biome::VolcanicCore => "🪨",
            Biome::PoisonSwamp => "🍄",
            Biome::HauntedGraveyard => "🪦",
        }
    }

    pub fn floor_char(&self) -> &'static str {
        match self {
            Biome::StoneDungeon => " ·",
            Biome::CrystalCavern => " ◇",
            Biome::EnchantedForest => " ⌇",
            Biome::FrozenDepths => " ❅",
            Biome::VolcanicCore => " ·",
            Biome::PoisonSwamp => " ≈",
            Biome::HauntedGraveyard => " ·",
        }
    }

    pub fn wall_color(&self) -> (u8, u8, u8) {
        match self {
            Biome::StoneDungeon => (100, 100, 100),
            Biome::CrystalCavern => (140, 100, 200),
            Biome::EnchantedForest => (60, 120, 50),
            Biome::FrozenDepths => (130, 180, 220),
            Biome::VolcanicCore => (160, 60, 30),
            Biome::PoisonSwamp => (80, 110, 50),
            Biome::HauntedGraveyard => (80, 70, 90),
        }
    }

    pub fn floor_color(&self) -> (u8, u8, u8) {
        match self {
            Biome::StoneDungeon => (60, 60, 60),
            Biome::CrystalCavern => (80, 60, 100),
            Biome::EnchantedForest => (40, 80, 30),
            Biome::FrozenDepths => (100, 140, 180),
            Biome::VolcanicCore => (100, 40, 20),
            Biome::PoisonSwamp => (50, 80, 40),
            Biome::HauntedGraveyard => (50, 45, 55),
        }
    }

    pub fn bg_color(&self) -> (u8, u8, u8) {
        match self {
            Biome::StoneDungeon => (18, 18, 24),
            Biome::CrystalCavern => (20, 14, 30),
            Biome::EnchantedForest => (12, 22, 10),
            Biome::FrozenDepths => (14, 20, 28),
            Biome::VolcanicCore => (28, 12, 8),
            Biome::PoisonSwamp => (14, 22, 12),
            Biome::HauntedGraveyard => (18, 16, 22),
        }
    }
}

// ─── Tile Types ──────────────────────────────────────────────────────

#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub enum Tile {
    // Basic
    Wall,
    Floor,
    StairsDown,
    #[allow(dead_code)]
    Door,
    // Hazard / terrain
    Water,         // 💧 impassable deep water
    ShallowWater,  // 🌊 walkable, slows (cosmetic for now)
    Lava,          // 🌋 walkable, deals 5-8 damage per step
    Trap,          // 🔸 walkable, hidden spike trap (one-time damage)
    // Decorative walkable floors
    Ice,           // ❄️ frozen floor
    Grass,         // 🌿 grassy floor
    Mud,           // muddy floor
    Moss,          // mossy floor
    Crystal,       // 💎 crystal floor
    Rubble,        // rubble floor
    Blood,         // 🩸 bloodstain
    Bones,         // 🦴 bone pile
    Web,           // 🕸️ spider web
}

impl Tile {
    pub fn is_walkable(&self) -> bool {
        matches!(
            self,
            Tile::Floor
                | Tile::StairsDown
                | Tile::Door
                | Tile::ShallowWater
                | Tile::Lava
                | Tile::Trap
                | Tile::Ice
                | Tile::Grass
                | Tile::Mud
                | Tile::Moss
                | Tile::Crystal
                | Tile::Rubble
                | Tile::Blood
                | Tile::Bones
                | Tile::Web
        )
    }

    pub fn is_opaque(&self) -> bool {
        matches!(self, Tile::Wall | Tile::Water)
    }

    /// True if this tile deals damage when walked on
    pub fn is_damaging(&self) -> bool {
        matches!(self, Tile::Lava | Tile::Trap)
    }

    /// True if this tile is a "floor variant" (walkable, transparent, decorative)
    pub fn is_floor_variant(&self) -> bool {
        matches!(
            self,
            Tile::Floor
                | Tile::Ice
                | Tile::Grass
                | Tile::Mud
                | Tile::Moss
                | Tile::Crystal
                | Tile::Rubble
                | Tile::Blood
                | Tile::Bones
                | Tile::Web
                | Tile::ShallowWater
        )
    }
}

// ─── Rect ────────────────────────────────────────────────────────────

#[derive(Clone, Debug)]
pub struct Rect {
    pub x: usize,
    pub y: usize,
    pub w: usize,
    pub h: usize,
}

impl Rect {
    pub fn new(x: usize, y: usize, w: usize, h: usize) -> Self {
        Self { x, y, w, h }
    }

    pub fn center(&self) -> (usize, usize) {
        (self.x + self.w / 2, self.y + self.h / 2)
    }

    pub fn intersects(&self, other: &Rect) -> bool {
        self.x < other.x + other.w
            && self.x + self.w > other.x
            && self.y < other.y + other.h
            && self.y + self.h > other.y
    }

    pub fn random_inner<R: Rng>(&self, rng: &mut R) -> (usize, usize) {
        let x = rng.gen_range(self.x + 1..self.x + self.w - 1).max(self.x + 1);
        let y = rng.gen_range(self.y + 1..self.y + self.h - 1).max(self.y + 1);
        (x, y)
    }
}

// ─── Game Map ────────────────────────────────────────────────────────

pub struct GameMap {
    pub tiles: Vec<Vec<Tile>>,
    pub rooms: Vec<Rect>,
    pub revealed: Vec<Vec<bool>>,
    pub visible: Vec<Vec<bool>>,
    pub biome: Biome,
}

impl GameMap {
    pub fn new() -> Self {
        let tiles = vec![vec![Tile::Wall; MAP_HEIGHT]; MAP_WIDTH];
        let revealed = vec![vec![false; MAP_HEIGHT]; MAP_WIDTH];
        let visible = vec![vec![false; MAP_HEIGHT]; MAP_WIDTH];
        Self {
            tiles,
            rooms: Vec::new(),
            revealed,
            visible,
            biome: Biome::StoneDungeon,
        }
    }

    pub fn generate(&mut self, floor: usize) {
        self.biome = Biome::from_floor(floor);
        self.tiles = vec![vec![Tile::Wall; MAP_HEIGHT]; MAP_WIDTH];
        self.rooms.clear();
        self.revealed = vec![vec![false; MAP_HEIGHT]; MAP_WIDTH];
        self.visible = vec![vec![false; MAP_HEIGHT]; MAP_WIDTH];

        let mut rng = rand::thread_rng();
        let max_rooms = 12 + floor.min(5);
        let min_size = 5;
        let max_size = 10;

        for _ in 0..max_rooms {
            let w = rng.gen_range(min_size..=max_size);
            let h = rng.gen_range(min_size..=max_size);
            let x = rng.gen_range(1..MAP_WIDTH.saturating_sub(w + 1));
            let y = rng.gen_range(1..MAP_HEIGHT.saturating_sub(h + 1));

            let new_room = Rect::new(x, y, w, h);

            let overlaps = self.rooms.iter().any(|r| new_room.intersects(r));

            if !overlaps {
                self.carve_room(&new_room);
                if let Some(prev) = self.rooms.last() {
                    self.carve_corridor(prev.center(), new_room.center());
                }
                self.rooms.push(new_room);
            }
        }

        // Place stairs down in the last room
        if self.rooms.len() > 1 {
            let last_room = self.rooms.last().unwrap();
            let (sx, sy) = last_room.center();
            self.tiles[sx][sy] = Tile::StairsDown;
        }

        // Add biome-specific decorations
        self.add_biome_decorations(floor);
    }

    fn carve_room(&mut self, room: &Rect) {
        for x in room.x..room.x + room.w {
            for y in room.y..room.y + room.h {
                if x > 0 && x < MAP_WIDTH - 1 && y > 0 && y < MAP_HEIGHT - 1 {
                    self.tiles[x][y] = Tile::Floor;
                }
            }
        }
    }

    fn carve_corridor(&mut self, from: (usize, usize), to: (usize, usize)) {
        let mut x = from.0;
        let mut y = from.1;

        if rand::thread_rng().gen_bool(0.5) {
            while x != to.0 {
                if x > 0 && x < MAP_WIDTH - 1 && y > 0 && y < MAP_HEIGHT - 1 {
                    self.tiles[x][y] = Tile::Floor;
                }
                if x < to.0 { x += 1; } else { x -= 1; }
            }
            while y != to.1 {
                if x > 0 && x < MAP_WIDTH - 1 && y > 0 && y < MAP_HEIGHT - 1 {
                    self.tiles[x][y] = Tile::Floor;
                }
                if y < to.1 { y += 1; } else { y -= 1; }
            }
        } else {
            while y != to.1 {
                if x > 0 && x < MAP_WIDTH - 1 && y > 0 && y < MAP_HEIGHT - 1 {
                    self.tiles[x][y] = Tile::Floor;
                }
                if y < to.1 { y += 1; } else { y -= 1; }
            }
            while x != to.0 {
                if x > 0 && x < MAP_WIDTH - 1 && y > 0 && y < MAP_HEIGHT - 1 {
                    self.tiles[x][y] = Tile::Floor;
                }
                if x < to.0 { x += 1; } else { x -= 1; }
            }
        }

        if to.0 > 0 && to.0 < MAP_WIDTH - 1 && to.1 > 0 && to.1 < MAP_HEIGHT - 1 {
            self.tiles[to.0][to.1] = Tile::Floor;
        }
    }

    fn add_biome_decorations(&mut self, floor: usize) {
        let mut rng = rand::thread_rng();

        // Collect all floor tiles
        let floor_tiles: Vec<(usize, usize)> = (0..MAP_WIDTH)
            .flat_map(|x| (0..MAP_HEIGHT).map(move |y| (x, y)))
            .filter(|&(x, y)| self.tiles[x][y] == Tile::Floor)
            .collect();

        match self.biome {
            Biome::StoneDungeon => {
                // Scatter rubble and bones
                self.scatter_tiles(&floor_tiles, Tile::Rubble, 0.05, &mut rng);
                self.scatter_tiles(&floor_tiles, Tile::Bones, 0.03, &mut rng);
                // Some traps
                self.scatter_tiles(&floor_tiles, Tile::Trap, 0.02 + floor as f64 * 0.003, &mut rng);
            }
            Biome::CrystalCavern => {
                // Crystal formations and shallow water pools
                self.scatter_tiles(&floor_tiles, Tile::Crystal, 0.10, &mut rng);
                self.scatter_tiles(&floor_tiles, Tile::ShallowWater, 0.04, &mut rng);
            }
            Biome::EnchantedForest => {
                // Grass, mud, spider webs
                self.scatter_tiles(&floor_tiles, Tile::Grass, 0.25, &mut rng);
                self.scatter_tiles(&floor_tiles, Tile::Mud, 0.08, &mut rng);
                self.scatter_tiles(&floor_tiles, Tile::Web, 0.04, &mut rng);
                self.scatter_tiles(&floor_tiles, Tile::Trap, 0.02, &mut rng);
            }
            Biome::FrozenDepths => {
                // Ice, shallow water (frozen pools), traps
                self.scatter_tiles(&floor_tiles, Tile::Ice, 0.30, &mut rng);
                self.scatter_tiles(&floor_tiles, Tile::ShallowWater, 0.05, &mut rng);
                self.scatter_tiles(&floor_tiles, Tile::Crystal, 0.04, &mut rng);
            }
            Biome::VolcanicCore => {
                // Lava pools! Very dangerous
                self.scatter_tiles(&floor_tiles, Tile::Lava, 0.06 + floor as f64 * 0.005, &mut rng);
                self.scatter_tiles(&floor_tiles, Tile::Rubble, 0.10, &mut rng);
                self.scatter_tiles(&floor_tiles, Tile::Blood, 0.05, &mut rng);
            }
            Biome::PoisonSwamp => {
                // Water, mud, moss everywhere
                self.scatter_tiles(&floor_tiles, Tile::Water, 0.06, &mut rng);
                self.scatter_tiles(&floor_tiles, Tile::ShallowWater, 0.10, &mut rng);
                self.scatter_tiles(&floor_tiles, Tile::Mud, 0.20, &mut rng);
                self.scatter_tiles(&floor_tiles, Tile::Moss, 0.15, &mut rng);
                self.scatter_tiles(&floor_tiles, Tile::Trap, 0.03, &mut rng);
            }
            Biome::HauntedGraveyard => {
                // Bones, blood, moss, webs
                self.scatter_tiles(&floor_tiles, Tile::Bones, 0.12, &mut rng);
                self.scatter_tiles(&floor_tiles, Tile::Blood, 0.06, &mut rng);
                self.scatter_tiles(&floor_tiles, Tile::Moss, 0.10, &mut rng);
                self.scatter_tiles(&floor_tiles, Tile::Web, 0.05, &mut rng);
                self.scatter_tiles(&floor_tiles, Tile::Trap, 0.03, &mut rng);
            }
        }
    }

    fn scatter_tiles<R: Rng>(
        &mut self,
        floor_tiles: &[(usize, usize)],
        tile: Tile,
        probability: f64,
        rng: &mut R,
    ) {
        for &(x, y) in floor_tiles {
            if rng.gen_bool(probability) {
                self.tiles[x][y] = tile;
            }
        }
    }

    pub fn is_walkable(&self, x: usize, y: usize) -> bool {
        x < MAP_WIDTH && y < MAP_HEIGHT && self.tiles[x][y].is_walkable()
    }

    pub fn get_random_walkable<R: Rng>(&self, rng: &mut R, room_idx: usize) -> Option<(usize, usize)> {
        let room = self.rooms.get(room_idx)?;
        for _ in 0..100 {
            let (x, y) = room.random_inner(rng);
            if self.tiles[x][y].is_walkable() && !self.tiles[x][y].is_damaging() {
                return Some((x, y));
            }
        }
        let (cx, cy) = room.center();
        if self.tiles[cx][cy].is_walkable() {
            return Some((cx, cy));
        }
        None
    }

    /// Trigger a trap at position, converting it to rubble. Returns true if a trap was triggered.
    pub fn trigger_trap(&mut self, x: usize, y: usize) -> bool {
        if x < MAP_WIDTH && y < MAP_HEIGHT && self.tiles[x][y] == Tile::Trap {
            self.tiles[x][y] = Tile::Rubble;
            true
        } else {
            false
        }
    }

    pub fn compute_fov(&mut self, px: usize, py: usize, radius: usize) {
        for row in &mut self.visible {
            row.iter_mut().for_each(|v| *v = false);
        }

        let px_i = px as i32;
        let py_i = py as i32;
        let radius_i = radius as i32;

        for angle_deg in 0..360 {
            let angle_rad = (angle_deg as f64) * std::f64::consts::PI / 180.0;
            let dx = angle_rad.cos();
            let dy = angle_rad.sin();

            let mut fx = px_i as f64 + 0.5;
            let mut fy = py_i as f64 + 0.5;

            for _ in 0..radius_i {
                fx += dx * 0.5;
                fy += dy * 0.5;

                let ix = fx as i32;
                let iy = fy as i32;

                if ix < 0 || iy < 0 || ix >= MAP_WIDTH as i32 || iy >= MAP_HEIGHT as i32 {
                    break;
                }

                let ux = ix as usize;
                let uy = iy as usize;

                self.visible[ux][uy] = true;
                self.revealed[ux][uy] = true;

                if self.tiles[ux][uy].is_opaque() {
                    break;
                }
            }
        }

        self.visible[px][py] = true;
        self.revealed[px][py] = true;
    }

    #[allow(dead_code)]
    pub fn get_empty_floor_tiles(&self, occupied: &HashSet<(usize, usize)>) -> Vec<(usize, usize)> {
        let mut tiles = Vec::new();
        for x in 0..MAP_WIDTH {
            for y in 0..MAP_HEIGHT {
                if self.tiles[x][y].is_floor_variant() && !occupied.contains(&(x, y)) {
                    tiles.push((x, y));
                }
            }
        }
        tiles
    }
}