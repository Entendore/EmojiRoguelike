//! Emoji Roguelike – with expanded biomes, new interactive tiles, shops, water/lava, secret doors, confusion, cloaks, custom input, main menu, and settings menu.
//! Idiomatic Rust with modules, builder pattern, and error handling.

use anyhow::{anyhow, Context, Result};
use crossterm::{
    cursor, event, execute, style, terminal, QueueableCommand,
};
use rand::Rng;
use serde::{Deserialize, Serialize};
use std::collections::VecDeque;
use std::fs;
use std::io::{stdout, Write};
use std::time::{Duration, Instant};

// =============================================================================
// Constants
// =============================================================================
const PLAYER_MOVE_INTERVAL: Duration = Duration::from_millis(150);
const MONSTER_MOVE_INTERVAL: Duration = Duration::from_millis(500);
const STATUS_TICK_INTERVAL: Duration = Duration::from_secs(2);
const HUNGER_TICK_INTERVAL: Duration = Duration::from_secs(5);
const SAVE_FILE: &str = "save.json";
const WIN_LEVEL: usize = 5;
const MAX_HUNGER: i32 = 100;
const HUNGER_DAMAGE: i32 = 1;

// =============================================================================
// Module: biome (EXPANDED with 4 new biomes)
// =============================================================================
mod biome {
    use super::*;

    #[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
    pub enum Biome {
        Dungeon,
        Cave,
        Forest,
        Crypt,
        Volcano,
        Swamp,   // NEW: toxic, muddy
        Ice,     // NEW: slippery, frosty
        Desert,  // NEW: dry, sandy
        Abyss,   // NEW: dark, corrupted
    }

    impl Biome {
        pub fn random() -> Self {
            match rand::thread_rng().gen_range(0..9) {
                0 => Self::Dungeon,
                1 => Self::Cave,
                2 => Self::Forest,
                3 => Self::Crypt,
                4 => Self::Volcano,
                5 => Self::Swamp,
                6 => Self::Ice,
                7 => Self::Desert,
                _ => Self::Abyss,
            }
        }

        pub const fn wall_tile(self) -> char {
            match self {
                Self::Dungeon => '🧱',
                Self::Cave => '🪨',
                Self::Forest => '🌲',
                Self::Crypt => '🪦',
                Self::Volcano => '🌋',
                Self::Swamp => '🌳',
                Self::Ice => '🧊',
                Self::Desert => '🏜️',
                Self::Abyss => '🌑',
            }
        }

        pub const fn floor_tile(self) -> char {
            match self {
                Self::Dungeon => '·',
                Self::Cave => '⬛',
                Self::Forest => '🌿',
                Self::Crypt => '🕯️',
                Self::Volcano => '🪨',
                Self::Swamp => '🍄',
                Self::Ice => '❄️',
                Self::Desert => '🟨',
                Self::Abyss => '🟪',
            }
        }

        pub fn wall_color(self) -> style::Color {
            match self {
                Self::Dungeon => style::Color::DarkGrey,
                Self::Cave => style::Color::Grey,
                Self::Forest => style::Color::DarkGreen,
                Self::Crypt => style::Color::Magenta,
                Self::Volcano => style::Color::Red,
                Self::Swamp => style::Color::Green,
                Self::Ice => style::Color::Cyan,
                Self::Desert => style::Color::Yellow,
                Self::Abyss => style::Color::DarkMagenta,
            }
        }

        pub fn floor_color(self) -> style::Color {
            match self {
                Self::Dungeon => style::Color::White,
                Self::Cave => style::Color::DarkGrey,
                Self::Forest => style::Color::Green,
                Self::Crypt => style::Color::DarkMagenta,
                Self::Volcano => style::Color::DarkRed,
                Self::Swamp => style::Color::DarkGreen,
                Self::Ice => style::Color::White,
                Self::Desert => style::Color::DarkYellow,
                Self::Abyss => style::Color::Magenta,
            }
        }
    }
}

// =============================================================================
// Module: map_gen (EXPANDED with new interactive tiles)
// =============================================================================
mod map_gen {
    use super::*;

    pub const MAP_WIDTH: usize = 50;
    pub const MAP_HEIGHT: usize = 25;
    const ROOM_MIN_SIZE: usize = 4;
    const ROOM_MAX_SIZE: usize = 8;
    const MAX_ROOMS: usize = 20;
    pub const MAX_MONSTERS: usize = 8;
    pub const MAX_TREASURES: usize = 5;
    pub const MAX_POTIONS: usize = 5;

    #[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
    pub enum Tile {
        Wall,
        Floor,
        Door,
        LockedDoor,
        Water,
        Lava,
        SecretDoor,
        // NEW TILES
        Ice,      // slippery
        Mud,      // slows/flavor
        Web,      // traps/flavor
        Sand,     // flavor
        Bridge,   // crosses hazards
        Altar,    // heals player
        Chest,    // gives gold
    }

    #[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
    pub struct Position {
        pub x: usize,
        pub y: usize,
    }

    impl Position {
        pub fn distance(self, other: Self) -> f64 {
            let dx = self.x as f64 - other.x as f64;
            let dy = self.y as f64 - other.y as f64;
            (dx * dx + dy * dy).sqrt()
        }
    }

    #[derive(Serialize, Deserialize)]
    struct Room {
        x1: usize,
        y1: usize,
        x2: usize,
        y2: usize,
    }

    impl Room {
        fn center(&self) -> Position {
            Position {
                x: (self.x1 + self.x2) / 2,
                y: (self.y1 + self.y2) / 2,
            }
        }
        fn intersects(&self, other: &Self) -> bool {
            self.x1 <= other.x2 && self.x2 >= other.x1 && self.y1 <= other.y2 && self.y2 >= other.y1
        }

        fn random_pos(&self) -> Position {
            let mut rng = rand::thread_rng();
            let x = rng.gen_range(self.x1 + 1..=self.x2 - 1);
            let y = rng.gen_range(self.y1 + 1..=self.y2 - 1);
            Position { x, y }
        }
    }

    fn create_room(map: &mut [Vec<Tile>], room: &Room) {
        for y in room.y1..=room.y2 {
            for x in room.x1..=room.x2 {
                map[y][x] = Tile::Floor;
            }
        }
    }

    fn create_h_corridor(map: &mut [Vec<Tile>], x1: usize, x2: usize, y: usize) {
        let (min_x, max_x) = (x1.min(x2), x1.max(x2));
        for x in min_x..=max_x {
            if y < MAP_HEIGHT && x < MAP_WIDTH {
                map[y][x] = Tile::Floor;
            }
        }
    }

    fn create_v_corridor(map: &mut [Vec<Tile>], y1: usize, y2: usize, x: usize) {
        let (min_y, max_y) = (y1.min(y2), y1.max(y2));
        for y in min_y..=max_y {
            if y < MAP_HEIGHT && x < MAP_WIDTH {
                map[y][x] = Tile::Floor;
            }
        }
    }

    pub fn generate(level: usize, biome: biome::Biome) -> (Vec<Vec<Tile>>, Vec<Room>) {
        let mut map = vec![vec![Tile::Wall; MAP_WIDTH]; MAP_HEIGHT];
        let mut rooms = Vec::new();
        let mut rng = rand::thread_rng();

        let max_rooms = (MAX_ROOMS).min(10 + level * 2);

        for _ in 0..max_rooms {
            let w = rng.gen_range(ROOM_MIN_SIZE..=ROOM_MAX_SIZE);
            let h = rng.gen_range(ROOM_MIN_SIZE..=ROOM_MAX_SIZE);
            let x = rng.gen_range(1..(MAP_WIDTH - w - 1));
            let y = rng.gen_range(1..(MAP_HEIGHT - h - 1));
            let new_room = Room {
                x1: x,
                y1: y,
                x2: x + w - 1,
                y2: y + h - 1,
            };

            if rooms.iter().any(|room| new_room.intersects(room)) {
                continue;
            }

            create_room(&mut map, &new_room);

            if let Some(prev) = rooms.last() {
                let prev_center = prev.center();
                let new_center = new_room.center();
                if rng.gen_bool(0.5) {
                    create_h_corridor(&mut map, prev_center.x, new_center.x, prev_center.y);
                    create_v_corridor(&mut map, prev_center.y, new_center.y, new_center.x);
                } else {
                    create_v_corridor(&mut map, prev_center.y, new_center.y, prev_center.x);
                    create_h_corridor(&mut map, prev_center.x, new_center.x, new_center.y);
                }
            }

            rooms.push(new_room);
        }

        // Place biome-specific and special tiles
        for room in rooms.iter().skip(1) {
            if rng.gen_bool(0.25) {
                let pos = room.random_pos();
                let tile = match biome {
                    biome::Biome::Swamp => Tile::Mud,
                    biome::Biome::Ice => Tile::Ice,
                    biome::Biome::Desert => Tile::Sand,
                    biome::Biome::Abyss => Tile::Web,
                    biome::Biome::Forest => if rng.gen_bool(0.5) { Tile::Web } else { Tile::Floor },
                    _ => {
                        let specials = [Tile::Water, Tile::Lava, Tile::Altar, Tile::Chest, Tile::Bridge];
                        specials[rng.gen_range(0..specials.len())]
                    }
                };
                map[pos.y][pos.x] = tile;
            }
        }

        (map, rooms)
    }
}

// =============================================================================
// Module: items (extended)
// =============================================================================
mod items {
    use super::*;

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub enum ItemKind {
        Weapon { attack_bonus: i32 },
        Shield { defense_bonus: i32 },
        Helmet { defense_bonus: i32 },
        Ring { attack_bonus: i32, defense_bonus: i32 },
        Boots { defense_bonus: i32, speed_bonus: f32 },
        Amulet { health_regen: i32 },
        Cloak { defense_bonus: i32 },

        ScrollTeleport,
        ScrollIdentify,
        ScrollEnchantWeapon { bonus: i32 },
        ScrollEnchantArmor { bonus: i32 },
        WandMagicMissile { charges: i32, damage: i32 },
        Food { hunger_restore: i32 },
        Key,
        PotionHeal { amount: i32 },
        PotionStrength { bonus: i32 },
        AmuletOfYendor,
    }

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct Item {
        pub name: String,
        pub symbol: char,
        pub kind: ItemKind,
    }

    #[derive(Default)]
    pub struct ItemBuilder {
        name: Option<String>,
        symbol: Option<char>,
        kind: Option<ItemKind>,
    }

    impl ItemBuilder {
        pub fn new() -> Self { Self::default() }
        pub fn name(mut self, name: impl Into<String>) -> Self {
            self.name = Some(name.into()); self
        }
        pub fn symbol(mut self, symbol: char) -> Self {
            self.symbol = Some(symbol); self
        }
        pub fn kind(mut self, kind: ItemKind) -> Self {
            self.kind = Some(kind); self
        }
        pub fn build(self) -> Result<Item> {
            Ok(Item {
                name: self.name.ok_or_else(|| anyhow!("Name required"))?,
                symbol: self.symbol.ok_or_else(|| anyhow!("Symbol required"))?,
                kind: self.kind.ok_or_else(|| anyhow!("Kind required"))?,
            })
        }
    }

    pub fn new_sword() -> Item { ItemBuilder::new().name("Sword").symbol('🗡️').kind(ItemKind::Weapon { attack_bonus: 3 }).build().unwrap() }
    pub fn new_shield() -> Item { ItemBuilder::new().name("Shield").symbol('🛡️').kind(ItemKind::Shield { defense_bonus: 2 }).build().unwrap() }
    pub fn new_helmet() -> Item { ItemBuilder::new().name("Helmet").symbol('⛑️').kind(ItemKind::Helmet { defense_bonus: 1 }).build().unwrap() }
    pub fn new_ring() -> Item { ItemBuilder::new().name("Ring").symbol('💍').kind(ItemKind::Ring { attack_bonus: 1, defense_bonus: 1 }).build().unwrap() }
    pub fn new_boots() -> Item { ItemBuilder::new().name("Boots").symbol('👢').kind(ItemKind::Boots { defense_bonus: 1, speed_bonus: 0.8 }).build().unwrap() }
    pub fn new_amulet() -> Item { ItemBuilder::new().name("Amulet").symbol('📿').kind(ItemKind::Amulet { health_regen: 2 }).build().unwrap() }
    pub fn new_cloak() -> Item { ItemBuilder::new().name("Cloak").symbol('🧥').kind(ItemKind::Cloak { defense_bonus: 1 }).build().unwrap() }
    pub fn new_scroll_teleport() -> Item { ItemBuilder::new().name("Scroll of Teleport").symbol('📜').kind(ItemKind::ScrollTeleport).build().unwrap() }
    pub fn new_scroll_identify() -> Item { ItemBuilder::new().name("Scroll of Identify").symbol('📖').kind(ItemKind::ScrollIdentify).build().unwrap() }
    pub fn new_scroll_enchant_weapon(bonus: i32) -> Item { ItemBuilder::new().name("Scroll of Enchant Weapon").symbol('⚡').kind(ItemKind::ScrollEnchantWeapon { bonus }).build().unwrap() }
    pub fn new_scroll_enchant_armor(bonus: i32) -> Item { ItemBuilder::new().name("Scroll of Enchant Armor").symbol('🛡️').kind(ItemKind::ScrollEnchantArmor { bonus }).build().unwrap() }
    pub fn new_wand_magic_missile(charges: i32, damage: i32) -> Item { ItemBuilder::new().name("Wand of Magic Missile").symbol('🪄').kind(ItemKind::WandMagicMissile { charges, damage }).build().unwrap() }
    pub fn new_food(hunger_restore: i32) -> Item { ItemBuilder::new().name("Food").symbol('🍖').kind(ItemKind::Food { hunger_restore }).build().unwrap() }
    pub fn new_key() -> Item { ItemBuilder::new().name("Key").symbol('🔑').kind(ItemKind::Key).build().unwrap() }
    pub fn new_potion_heal(amount: i32) -> Item { ItemBuilder::new().name("Potion of Healing").symbol('❤️').kind(ItemKind::PotionHeal { amount }).build().unwrap() }
    pub fn new_potion_strength(bonus: i32) -> Item { ItemBuilder::new().name("Potion of Strength").symbol('💪').kind(ItemKind::PotionStrength { bonus }).build().unwrap() }
    pub fn new_amulet_of_yendor() -> Item { ItemBuilder::new().name("Amulet of Yendor").symbol('🏆').kind(ItemKind::AmuletOfYendor).build().unwrap() }
}

// =============================================================================
// Module: entities (extended)
// =============================================================================
mod entities {
    use super::*;
    use map_gen::Position;

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub enum MonsterAbility {
        None,
        Poison { damage: i32, duration: i32 },
        Ranged { damage: i32, range: i32 },
        Teleport { range: i32 },
        Summon { count: i32 },
        Heal { amount: i32 },
        Confuse { duration: i32 },
        Boss,
    }

    #[derive(Debug, Serialize, Deserialize)]
    pub struct Monster {
        pub pos: Position,
        pub hp: i32,
        pub max_hp: i32,
        pub attack: i32,
        pub symbol: char,
        pub view_range: i32,
        pub ability: MonsterAbility,
        pub alive: bool,
        pub is_boss: bool,
    }

    impl Monster {
        pub fn new(pos: Position, level: usize, is_boss: bool) -> Self {
            let mut rng = rand::thread_rng();
            let base_hp = if is_boss { 30 + level as i32 * 5 } else { 5 + level as i32 * 2 };
            let hp = rng.gen_range(base_hp..base_hp + if is_boss { 10 } else { 5 });
            let attack = if is_boss { 5 + level as i32 + rng.gen_range(0..5) } else { 2 + level as i32 + rng.gen_range(0..3) };
            let symbol = if is_boss { '🐲' } else {
                let symbols = ['👹', '🐉', '👾', '🧟', '🦇', '🧌', '👻', '🐙', '🧛', '🕷️', '🦂'];
                symbols[rng.gen_range(0..symbols.len())]
            };
            let view_range = if level > 2 { 6 } else { 4 };
            let ability = if is_boss {
                MonsterAbility::Boss
            } else if rng.gen_bool(0.2) {
                MonsterAbility::Poison { damage: 2 + level as i32, duration: 3 }
            } else if rng.gen_bool(0.15) {
                MonsterAbility::Ranged { damage: 3 + level as i32, range: 5 }
            } else if rng.gen_bool(0.15) {
                MonsterAbility::Teleport { range: 6 }
            } else if rng.gen_bool(0.1) {
                MonsterAbility::Summon { count: 1 }
            } else if rng.gen_bool(0.1) {
                MonsterAbility::Heal { amount: 5 + level as i32 }
            } else if rng.gen_bool(0.1) {
                MonsterAbility::Confuse { duration: 3 }
            } else {
                MonsterAbility::None
            };
            Self { pos, hp, max_hp: hp, attack, symbol, view_range, ability, alive: true, is_boss }
        }
        pub fn is_alive(&self) -> bool { self.alive && self.hp > 0 }
    }

    #[derive(Debug, Serialize, Deserialize)]
    pub struct Treasure { pub pos: Position, pub symbol: char }
    impl Treasure { pub fn new(pos: Position) -> Self { Self { pos, symbol: '💰' } } }

    #[derive(Debug, Serialize, Deserialize)]
    pub struct Potion { pub pos: Position, pub heal_amount: i32, pub symbol: char }
    impl Potion {
        pub fn new(pos: Position) -> Self {
            Self { pos, heal_amount: rand::thread_rng().gen_range(4..10), symbol: '🧪' }
        }
    }

    #[derive(Debug, Serialize, Deserialize)]
    pub struct Stairs { pub pos: Position, pub symbol: char }
    impl Stairs { pub fn new(pos: Position) -> Self { Self { pos, symbol: '🪜' } } }

    #[derive(Debug, Serialize, Deserialize)]
    pub struct GroundItem { pub pos: Position, pub item: items::Item }

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub enum StatusKind { Poison, Starving, Confused }

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct StatusEffect { pub kind: StatusKind, pub damage: i32, pub duration: i32 }
    impl StatusEffect {
        pub fn new_poison(damage: i32, duration: i32) -> Self { Self { kind: StatusKind::Poison, damage, duration } }
        pub fn new_starving(damage: i32) -> Self { Self { kind: StatusKind::Starving, damage, duration: 999 } }
        pub fn new_confused(duration: i32) -> Self { Self { kind: StatusKind::Confused, damage: 0, duration } }
    }

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub enum TrapKind { Damage { damage: i32 }, Poison { damage: i32, duration: i32 }, Pit { damage: i32 } }

    #[derive(Debug, Serialize, Deserialize)]
    pub struct Trap { pub pos: Position, pub kind: TrapKind, pub symbol: char, pub triggered: bool }
    impl Trap {
        pub fn new(pos: Position, level: usize) -> Self {
            let mut rng = rand::thread_rng();
            let kind = if rng.gen_bool(0.5) {
                TrapKind::Damage { damage: 2 + level as i32 }
            } else if rng.gen_bool(0.5) {
                TrapKind::Poison { damage: 1 + level as i32, duration: 3 }
            } else {
                TrapKind::Pit { damage: 5 + level as i32 }
            };
            Self { pos, kind, symbol: '⚠', triggered: false }
        }
        pub fn is_active(&self) -> bool { !self.triggered }
    }

    #[derive(Debug, Serialize, Deserialize)]
    pub struct Shop { pub pos: Position, pub items: Vec<items::Item>, pub prices: Vec<i32>, pub symbol: char }
    impl Shop {
        pub fn new(pos: Position, level: usize) -> Self {
            let mut rng = rand::thread_rng();
            let mut items = Vec::new();
            let mut prices = Vec::new();
            let num_items = rng.gen_range(3..=5);
            for _ in 0..num_items {
                let item = match rng.gen_range(0..8) {
                    0 => items::new_sword(), 1 => items::new_shield(), 2 => items::new_helmet(),
                    3 => items::new_ring(), 4 => items::new_boots(), 5 => items::new_amulet(),
                    6 => items::new_cloak(), _ => items::new_potion_heal(rng.gen_range(6..12)),
                };
                items.push(item);
                prices.push(rng.gen_range(10..=30) + level as i32 * 2);
            }
            Self { pos, items, prices, symbol: '🧝' }
        }
    }
}

// =============================================================================
// Module: equipment (extended)
// =============================================================================
mod equipment {
    use super::*;
    use items::{Item, ItemKind};

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct Equipment {
        pub weapon: Option<Item>, pub shield: Option<Item>, pub helmet: Option<Item>,
        pub ring1: Option<Item>, pub ring2: Option<Item>, pub boots: Option<Item>,
        pub amulet: Option<Item>, pub cloak: Option<Item>,
    }
    impl Default for Equipment { fn default() -> Self { Self::new() } }
    impl Equipment {
        pub fn new() -> Self {
            Self { weapon: None, shield: None, helmet: None, ring1: None, ring2: None, boots: None, amulet: None, cloak: None }
        }
        pub fn total_attack(&self) -> i32 {
            let mut bonus = 0;
            if let Some(Item { kind: ItemKind::Weapon { attack_bonus }, .. }) = &self.weapon { bonus += attack_bonus; }
            for ring in [&self.ring1, &self.ring2] {
                if let Some(Item { kind: ItemKind::Ring { attack_bonus, .. }, .. }) = ring { bonus += attack_bonus; }
            }
            bonus
        }
        pub fn total_defense(&self) -> i32 {
            let mut bonus = 0;
            for item in [&self.shield, &self.helmet, &self.boots, &self.cloak] {
                if let Some(item) = item {
                    match &item.kind {
                        ItemKind::Shield { defense_bonus } | ItemKind::Helmet { defense_bonus } |
                        ItemKind::Boots { defense_bonus, .. } | ItemKind::Cloak { defense_bonus } => bonus += defense_bonus,
                        _ => {}
                    }
                }
            }
            for ring in [&self.ring1, &self.ring2] {
                if let Some(Item { kind: ItemKind::Ring { defense_bonus, .. }, .. }) = ring { bonus += defense_bonus; }
            }
            bonus
        }
        pub fn total_speed_bonus(&self) -> f32 {
            self.boots.as_ref().and_then(|b| match &b.kind { ItemKind::Boots { speed_bonus, .. } => Some(*speed_bonus), _ => None }).unwrap_or(1.0)
        }
        pub fn total_regen(&self) -> i32 {
            self.amulet.as_ref().and_then(|a| match &a.kind { ItemKind::Amulet { health_regen } => Some(*health_regen), _ => None }).unwrap_or(0)
        }
    }
}

// =============================================================================
// Module: settings (Custom Input & Settings)
// =============================================================================
mod settings {
    use super::*;
    use input::get_input_blocking;
    use std::io::stdout;

    const SETTINGS_FILE: &str = "settings.json";

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct Settings {
        pub key_up: String,
        pub key_down: String,
        pub key_left: String,
        pub key_right: String,
        pub key_fireball: String,
        pub key_heal: String,
        pub key_wand: String,
        pub key_inventory: String,
        pub key_save: String,
        pub key_pause: String,
        pub key_quit: String,
    }

    impl Default for Settings {
        fn default() -> Self {
            Self {
                key_up: "w".to_string(), key_down: "s".to_string(), key_left: "a".to_string(), key_right: "d".to_string(),
                key_fireball: "1".to_string(), key_heal: "2".to_string(), key_wand: "3".to_string(),
                key_inventory: "i".to_string(), key_save: "S".to_string(), key_pause: "p".to_string(), key_quit: "q".to_string(),
            }
        }
    }

    pub fn save_settings(settings: &Settings) -> Result<()> {
        let serialized = serde_json::to_string_pretty(settings)?;
        fs::write(SETTINGS_FILE, serialized)?;
        Ok(())
    }

    pub fn load_settings() -> Result<Settings> {
        let data = fs::read_to_string(SETTINGS_FILE)?;
        let settings: Settings = serde_json::from_str(&data)?;
        Ok(settings)
    }

    pub fn matches_key(code: &event::KeyCode, setting: &str) -> bool {
        let setting_lower = setting.to_lowercase();
        match code {
            event::KeyCode::Up => setting_lower == "up",
            event::KeyCode::Down => setting_lower == "down",
            event::KeyCode::Left => setting_lower == "left",
            event::KeyCode::Right => setting_lower == "right",
            event::KeyCode::Enter => setting_lower == "enter",
            event::KeyCode::Esc => setting_lower == "esc",
            event::KeyCode::Backspace => setting_lower == "backspace",
            event::KeyCode::Char(c) => setting_lower == c.to_lowercase().to_string(),
            _ => false,
        }
    }

    pub fn show_settings_menu(settings: &mut Settings) {
        loop {
            let mut stdout = stdout();
            execute!(stdout, cursor::MoveTo(0, 0), terminal::Clear(terminal::ClearType::All), style::SetForegroundColor(style::Color::White)).unwrap();

            stdout.queue(cursor::MoveTo(10, 3)).unwrap().queue(style::Print("⚙️  Settings  ⚙️")).unwrap();
            stdout.queue(cursor::MoveTo(10, 5)).unwrap().queue(style::Print(format!("1) Move Up:    [{}]", settings.key_up))).unwrap();
            stdout.queue(cursor::MoveTo(10, 6)).unwrap().queue(style::Print(format!("2) Move Down:  [{}]", settings.key_down))).unwrap();
            stdout.queue(cursor::MoveTo(10, 7)).unwrap().queue(style::Print(format!("3) Move Left:  [{}]", settings.key_left))).unwrap();
            stdout.queue(cursor::MoveTo(10, 8)).unwrap().queue(style::Print(format!("4) Move Right: [{}]", settings.key_right))).unwrap();
            stdout.queue(cursor::MoveTo(10, 9)).unwrap().queue(style::Print(format!("5) Fireball:   [{}]", settings.key_fireball))).unwrap();
            stdout.queue(cursor::MoveTo(10, 10)).unwrap().queue(style::Print(format!("6) Heal:       [{}]", settings.key_heal))).unwrap();
            stdout.queue(cursor::MoveTo(10, 11)).unwrap().queue(style::Print(format!("7) Use Wand:   [{}]", settings.key_wand))).unwrap();
            stdout.queue(cursor::MoveTo(10, 12)).unwrap().queue(style::Print(format!("8) Inventory:  [{}]", settings.key_inventory))).unwrap();
            stdout.queue(cursor::MoveTo(10, 13)).unwrap().queue(style::Print(format!("9) Save Game:  [{}]", settings.key_save))).unwrap();
            stdout.queue(cursor::MoveTo(10, 14)).unwrap().queue(style::Print(format!("0) Pause:      [{}]", settings.key_pause))).unwrap();
            stdout.queue(cursor::MoveTo(10, 15)).unwrap().queue(style::Print(format!("Q) Quit Game:  [{}]", settings.key_quit))).unwrap();
            
            stdout.queue(cursor::MoveTo(10, 17)).unwrap().queue(style::Print("Press number to rebind, Esc to go back")).unwrap();
            stdout.flush().unwrap();

            let key = get_input_blocking();
            match key {
                event::KeyCode::Esc => return,
                event::KeyCode::Char(c) => {
                    let setting_to_change = match c {
                        '1' => Some(&mut settings.key_up), '2' => Some(&mut settings.key_down),
                        '3' => Some(&mut settings.key_left), '4' => Some(&mut settings.key_right),
                        '5' => Some(&mut settings.key_fireball), '6' => Some(&mut settings.key_heal),
                        '7' => Some(&mut settings.key_wand), '8' => Some(&mut settings.key_inventory),
                        '9' => Some(&mut settings.key_save), '0' => Some(&mut settings.key_pause),
                        'q' | 'Q' => Some(&mut settings.key_quit), _ => None,
                    };

                    if let Some(setting) = setting_to_change {
                        stdout.queue(cursor::MoveTo(10, 19)).unwrap().queue(style::Print("Press new key (or Esc to cancel): ")).unwrap();
                        stdout.flush().unwrap();
                        
                        let new_key = get_input_blocking();
                        if new_key == event::KeyCode::Esc { continue; }
                        
                        let key_str = match new_key {
                            event::KeyCode::Up => "Up".to_string(), event::KeyCode::Down => "Down".to_string(),
                            event::KeyCode::Left => "Left".to_string(), event::KeyCode::Right => "Right".to_string(),
                            event::KeyCode::Enter => "Enter".to_string(), event::KeyCode::Esc => "Esc".to_string(),
                            event::KeyCode::Backspace => "Backspace".to_string(), event::KeyCode::Char(c) => c.to_string(),
                            _ => "Unknown".to_string(),
                        };
                        *setting = key_str;
                        let _ = save_settings(settings);
                    }
                }
                _ => {}
            }
        }
    }
}

// =============================================================================
// Module: game (extended with new tile interactions)
// =============================================================================
mod game {
    use super::*;
    use map_gen::{Position, Tile, MAP_WIDTH, MAP_HEIGHT};
    use entities::*;
    use items::*;
    use equipment::Equipment;
    use std::collections::VecDeque;

    pub const VIEW_RADIUS: i32 = 8;
    pub const INVENTORY_SIZE: usize = 10;
    pub const MAX_MESSAGES: usize = 6;

    pub trait Action { fn execute(&mut self, game: &mut Game); }
    pub struct MoveAction { pub dx: i32, pub dy: i32 }
    impl Action for MoveAction { fn execute(&mut self, game: &mut Game) { game.move_player(self.dx, self.dy); } }
    pub struct FireArrowAction; impl Action for FireArrowAction { fn execute(&mut self, game: &mut Game) { game.fire_arrow(); } }
    pub struct FireballAction; impl Action for FireballAction { fn execute(&mut self, game: &mut Game) { game.fireball(); } }
    pub struct HealAction; impl Action for HealAction { fn execute(&mut self, game: &mut Game) { game.heal(); } }
    pub struct UseWandAction; impl Action for UseWandAction { fn execute(&mut self, game: &mut Game) { game.use_wand(); } }

    #[derive(Serialize, Deserialize)]
    pub struct Game {
        pub map: Vec<Vec<Tile>>, pub explored: Vec<Vec<bool>>, pub biome: biome::Biome,
        pub player_pos: Position, pub player_hp: i32, pub player_max_hp: i32,
        pub player_base_attack: i32, pub player_xp: i32, pub player_next_level_xp: i32,
        pub player_level: i32, pub player_hunger: i32, pub equipment: Equipment,
        pub inventory: Vec<Item>, pub facing: (i32, i32), pub monsters: Vec<Monster>,
        pub treasures: Vec<Treasure>, pub potions: Vec<Potion>, pub ground_items: Vec<GroundItem>,
        pub stairs: Option<Stairs>, pub status_effects: Vec<StatusEffect>, pub traps: Vec<Trap>,
        pub shops: Vec<Shop>, pub score: i32, pub level: usize, pub has_amulet: bool, pub won: bool,

        #[serde(skip)] pub messages: VecDeque<(String, style::Color)>,
        #[serde(skip)] pub game_over: bool, #[serde(skip)] pub paused: bool,
        #[serde(skip)] pub last_arrow_time: Option<Instant>, #[serde(skip)] pub last_fireball_time: Option<Instant>,
        #[serde(skip)] pub last_heal_time: Option<Instant>, #[serde(skip)] pub last_wand_time: Option<Instant>,
        #[serde(skip)] pub hunger_timer: Instant, #[serde(skip)] pub confusion_direction_timer: Option<Instant>,
    }

    impl Game {
        pub fn new(map: Vec<Vec<Tile>>, explored: Vec<Vec<bool>>, biome: biome::Biome, player_pos: Position,
            player_hp: i32, player_max_hp: i32, player_base_attack: i32, player_xp: i32, player_level: i32,
            player_hunger: i32, equipment: Equipment, inventory: Vec<Item>, facing: (i32, i32),
            monsters: Vec<Monster>, treasures: Vec<Treasure>, potions: Vec<Potion>, ground_items: Vec<GroundItem>,
            stairs: Option<Stairs>, status_effects: Vec<StatusEffect>, traps: Vec<Trap>, shops: Vec<Shop>,
            score: i32, level: usize, has_amulet: bool, won: bool) -> Self 
        {
            let mut messages = VecDeque::new();
            messages.push_back(("Welcome to the dungeon!".to_string(), style::Color::White));
            Self {
                map, explored, biome, player_pos, player_hp, player_max_hp, player_base_attack,
                player_xp, player_next_level_xp: player_level * 10, player_level, player_hunger,
                equipment, inventory, facing, monsters, treasures, potions, ground_items, stairs,
                status_effects, traps, shops, score, level, has_amulet, won, messages,
                game_over: false, paused: false, last_arrow_time: None, last_fireball_time: None,
                last_heal_time: None, last_wand_time: None, hunger_timer: Instant::now(), confusion_direction_timer: None,
            }
        }

        pub fn add_message(&mut self, msg: impl Into<String>, color: style::Color) {
            let msg = msg.into();
            self.messages.push_back((msg, color));
            if self.messages.len() > MAX_MESSAGES { self.messages.pop_front(); }
        }

        pub fn gain_xp(&mut self, amount: i32) {
            self.player_xp += amount;
            self.add_message(format!("✨ +{} XP", amount), style::Color::Yellow);
            while self.player_xp >= self.player_next_level_xp {
                self.player_xp -= self.player_next_level_xp;
                self.player_level += 1;
                self.player_next_level_xp = self.player_level * 10;
                self.player_max_hp += 2;
                self.player_hp = self.player_max_hp;
                self.player_base_attack += 1;
                self.add_message(format!("🎉 Level up! You are now level {}", self.player_level), style::Color::Green);
                self.add_message("❤️ Max HP +2, Attack +1, fully healed!", style::Color::Green);
            }
        }

        pub fn tick_hunger(&mut self) {
            if self.game_over || self.paused { return; }
            self.player_hunger -= 1;
            if self.player_hunger <= 0 {
                self.player_hp -= HUNGER_DAMAGE;
                self.add_message("🍽️ You are starving! Take 1 damage.", style::Color::Red);
                if !self.status_effects.iter().any(|e| matches!(e.kind, StatusKind::Starving)) {
                    self.status_effects.push(StatusEffect::new_starving(HUNGER_DAMAGE));
                }
                if self.player_hp <= 0 {
                    self.player_hp = 0; self.game_over = true;
                    self.add_message("💀 You starved to death!", style::Color::Red);
                }
            } else {
                if let Some(idx) = self.status_effects.iter().position(|e| matches!(e.kind, StatusKind::Starving)) {
                    self.status_effects.remove(idx);
                }
            }
        }

        pub fn eat_food(&mut self, hunger_restore: i32) {
            self.player_hunger = (self.player_hunger + hunger_restore).min(MAX_HUNGER);
            self.add_message(format!("🍖 You eat food. Hunger +{}", hunger_restore), style::Color::Cyan);
            if let Some(idx) = self.status_effects.iter().position(|e| matches!(e.kind, StatusKind::Starving)) {
                self.status_effects.remove(idx);
            }
        }

        fn has_line_of_sight(&self, from: Position, to: Position) -> bool {
            let mut x0 = from.x as i32; let mut y0 = from.y as i32;
            let x1 = to.x as i32; let y1 = to.y as i32;
            let dx = (x1 - x0).abs(); let dy = (y1 - y0).abs();
            let sx = if x0 < x1 { 1 } else { -1 }; let sy = if y0 < y1 { 1 } else { -1 };
            let mut err = dx - dy;
            loop {
                if x0 == x1 && y0 == y1 { return true; }
                if !(x0 == from.x as i32 && y0 == from.y as i32) {
                    let tile = self.map[y0 as usize][x0 as usize];
                    if tile == Tile::Wall || tile == Tile::LockedDoor { return false; }
                }
                let e2 = 2 * err;
                if e2 > -dy { err -= dy; x0 += sx; }
                if e2 < dx { err += dx; y0 += sy; }
            }
        }

        pub fn reveal_around_player(&mut self) {
            let px = self.player_pos.x as i32; let py = self.player_pos.y as i32;
            for dy in -VIEW_RADIUS..=VIEW_RADIUS {
                for dx in -VIEW_RADIUS..=VIEW_RADIUS {
                    if dx * dx + dy * dy > VIEW_RADIUS * VIEW_RADIUS { continue; }
                    let x = px + dx; let y = py + dy;
                    if x >= 0 && x < MAP_WIDTH as i32 && y >= 0 && y < MAP_HEIGHT as i32 {
                        let pos = Position { x: x as usize, y: y as usize };
                        if self.has_line_of_sight(self.player_pos, pos) {
                            self.explored[y as usize][x as usize] = true;
                        }
                    }
                }
            }
            for dy in -1..=1 {
                for dx in -1..=1 {
                    let x = self.player_pos.x as i32 + dx; let y = self.player_pos.y as i32 + dy;
                    if x >= 0 && x < MAP_WIDTH as i32 && y >= 0 && y < MAP_HEIGHT as i32 {
                        if self.map[y as usize][x as usize] == Tile::SecretDoor {
                            self.map[y as usize][x as usize] = Tile::Floor;
                            self.add_message("🔓 You discovered a secret door!", style::Color::Cyan);
                        }
                    }
                }
            }
        }

        pub fn move_player(&mut self, dx: i32, dy: i32) {
            if self.game_over || self.paused || (dx == 0 && dy == 0) { return; }
            let (final_dx, final_dy) = if self.is_confused() {
                let mut rng = rand::thread_rng();
                let dirs = [(0, -1), (0, 1), (-1, 0), (1, 0)];
                let (rdx, rdy) = dirs[rng.gen_range(0..dirs.len())];
                self.add_message("🌀 You are confused! Move randomly.", style::Color::Yellow);
                (rdx, rdy)
            } else { (dx, dy) };

            if final_dx != 0 || final_dy != 0 { self.facing = (final_dx, final_dy); }
            let new_x = self.player_pos.x as i32 + final_dx;
            let new_y = self.player_pos.y as i32 + final_dy;
            if new_x < 0 || new_x >= MAP_WIDTH as i32 || new_y < 0 || new_y >= MAP_HEIGHT as i32 { return; }
            let new_pos = Position { x: new_x as usize, y: new_y as usize };

            match self.map[new_pos.y][new_pos.x] {
                Tile::Wall => return,
                Tile::LockedDoor => {
                    if let Some(idx) = self.inventory.iter().position(|item| matches!(item.kind, ItemKind::Key)) {
                        self.inventory.remove(idx);
                        self.map[new_pos.y][new_pos.x] = Tile::Door;
                        self.add_message("🔑 You unlock the door!", style::Color::Cyan);
                    } else {
                        self.add_message("🚪 The door is locked. You need a key.", style::Color::Yellow);
                        return;
                    }
                }
                Tile::Water => { self.add_message("💧 You splash through water.", style::Color::Cyan); }
                Tile::Lava => {
                    self.player_hp -= 3;
                    self.add_message("🌋 Lava burns you for 3 damage!", style::Color::Red);
                    if self.player_hp <= 0 { self.player_hp = 0; self.game_over = true; self.add_message("💀 You died in lava!", style::Color::Red); return; }
                }
                // NEW TILE INTERACTIONS
                Tile::Ice => {
                    self.add_message("❄️ You slide on the ice!", style::Color::Cyan);
                    // Simple slide mechanic: attempt one more step in facing direction
                    let slide_x = new_pos.x as i32 + self.facing.0;
                    let slide_y = new_pos.y as i32 + self.facing.1;
                    if slide_x >= 0 && slide_x < MAP_WIDTH as i32 && slide_y >= 0 && slide_y < MAP_HEIGHT as i32 {
                        let slide_pos = Position { x: slide_x as usize, y: slide_y as usize };
                        if self.map[slide_pos.y][slide_pos.x] != Tile::Wall && self.map[slide_pos.y][slide_pos.x] != Tile::LockedDoor {
                            if !self.monsters.iter().any(|m| m.is_alive() && m.pos == slide_pos) {
                                // Successfully slid
                                return self.finalize_move(slide_pos);
                            }
                        }
                    }
                }
                Tile::Mud => { self.add_message("🟤 You trudge through the thick mud.", style::Color::DarkGrey); }
                Tile::Web => { self.add_message("🕸️ You break through a sticky spider web!", style::Color::White); }
                Tile::Sand => { self.add_message("🏜️ You walk across the shifting sand.", style::Color::Yellow); }
                Tile::Bridge => { self.add_message("🌉 You safely cross the bridge.", style::Color::Yellow); }
                Tile::Altar => {
                    let heal = 10.min(self.player_max_hp - self.player_hp);
                    self.player_hp += heal;
                    self.add_message(format!("🛐 You pray at the altar. +{} HP!", heal), style::Color::Magenta);
                    self.map[new_pos.y][new_pos.x] = Tile::Floor; // Altar is consumed
                }
                Tile::Chest => {
                    self.score += 15;
                    self.add_message("📦 You open a chest and find treasure! +15 gold", style::Color::Yellow);
                    self.map[new_pos.y][new_pos.x] = Tile::Floor; // Chest is opened
                }
                Tile::SecretDoor => {
                    self.map[new_pos.y][new_pos.x] = Tile::Floor;
                    self.add_message("🔓 You discovered a secret door!", style::Color::Cyan);
                }
                _ => {}
            }

            self.finalize_move(new_pos);
        }

        fn finalize_move(&mut self, pos: Position) {
            if let Some(idx) = self.monsters.iter().position(|m| m.is_alive() && m.pos == pos) {
                self.melee_attack(idx); return;
            }
            if let Some(idx) = self.traps.iter().position(|t| t.is_active() && t.pos == pos) {
                self.trigger_trap(idx);
                if let TrapKind::Pit { .. } = self.traps[idx].kind { self.descend_level(); return; }
            }
            if let Some(shop) = self.shops.iter().find(|s| s.pos == pos) { self.open_shop(shop); return; }

            self.pickup_items(pos);
            if let Some(stairs) = &self.stairs {
                if stairs.pos == pos { self.descend_level(); return; }
            }
            self.player_pos = pos;
            self.reveal_around_player();
        }

        fn is_confused(&self) -> bool { self.status_effects.iter().any(|e| matches!(e.kind, StatusKind::Confused)) }

        fn melee_attack(&mut self, monster_idx: usize) {
            let monster = &mut self.monsters[monster_idx];
            let total_attack = self.player_base_attack + self.equipment.total_attack();
            monster.hp -= total_attack;
            if monster.hp <= 0 {
                monster.alive = false;
                let msg = format!("💥 You killed the {}!", monster.symbol);
                let color = if monster.is_boss { style::Color::Red } else { style::Color::Yellow };
                self.add_message(msg, color);
                self.score += if monster.is_boss { 50 } else { 10 };
                self.gain_xp(if monster.is_boss { 20 } else { 5 + self.level as i32 });
                self.drop_items_from_monster(monster);
                self.player_pos = monster.pos;
                if monster.is_boss { self.add_message("👑 You defeated a boss!", style::Color::Magenta); }
            } else {
                self.add_message(format!("⚔️ You hit {} for {} damage!", monster.symbol, total_attack), style::Color::White);
                let damage = (monster.attack - self.equipment.total_defense()).max(1);
                self.player_hp -= damage;
                self.add_message(format!("💢 {} hits you for {} damage!", monster.symbol, damage), style::Color::Red);
                self.apply_monster_ability(monster);
                if self.player_hp <= 0 { self.player_hp = 0; self.game_over = true; self.add_message("💀 You have been slain!", style::Color::Red); }
            }
        }

        fn pickup_items(&mut self, pos: Position) {
            let mut to_remove = Vec::new();
            for (i, ground) in self.ground_items.iter().enumerate() {
                if ground.pos == pos {
                    if let ItemKind::AmuletOfYendor = ground.item.kind {
                        self.has_amulet = true;
                        self.add_message("🏆 You found the Amulet of Yendor!", style::Color::Magenta);
                        if self.level >= WIN_LEVEL { self.won = true; self.game_over = true; self.add_message("🎉 You win!", style::Color::Green); }
                        to_remove.push(i); continue;
                    }
                    if self.inventory.len() < INVENTORY_SIZE {
                        self.inventory.push(ground.item.clone());
                        self.add_message(format!("Picked up {}.", ground.item.name), style::Color::Cyan);
                        to_remove.push(i);
                    } else { self.add_message("Inventory full!", style::Color::Yellow); }
                }
            }
            for i in to_remove.into_iter().rev() { self.ground_items.remove(i); }

            if let Some(idx) = self.potions.iter().position(|p| p.pos == pos) {
                let potion = self.potions.remove(idx);
                let healed = potion.heal_amount.min(self.player_max_hp - self.player_hp);
                self.player_hp += healed;
                self.add_message(format!("🧪 Drank a potion! +{} HP", healed), style::Color::Green);
                self.score += 2;
            }
            if let Some(idx) = self.treasures.iter().position(|t| t.pos == pos) {
                self.treasures.remove(idx); self.score += 5;
                self.add_message("💰 Collected treasure!", style::Color::Yellow);
            }
        }

        fn drop_items_from_monster(&mut self, monster: &Monster) {
            let mut rng = rand::thread_rng();
            if monster.is_boss {
                let items = vec![new_amulet(), new_wand_magic_missile(5, 12), new_scroll_identify(), new_potion_strength(1)];
                self.ground_items.push(GroundItem { pos: monster.pos, item: items[rng.gen_range(0..items.len())].clone() });
                self.add_message("🎁 Boss dropped a powerful item!", style::Color::Cyan); return;
            }
            if rng.gen_bool(0.4) {
                let items = vec![new_sword(), new_shield(), new_helmet(), new_ring(), new_boots(), new_amulet(), new_cloak(), new_scroll_teleport(), new_scroll_identify(), new_scroll_enchant_weapon(1), new_scroll_enchant_armor(1), new_wand_magic_missile(3, 8), new_food(20), new_key(), new_potion_heal(8)];
                self.ground_items.push(GroundItem { pos: monster.pos, item: items[rng.gen_range(0..items.len())].clone() });
                self.add_message(format!("📦 {} dropped an item!", monster.symbol), style::Color::Cyan);
            }
        }

        fn trigger_trap(&mut self, idx: usize) {
            let trap = &mut self.traps[idx];
            if !trap.is_active() { return; }
            trap.triggered = true;
            self.add_message("💥 You triggered a trap!", style::Color::Red);
            match &trap.kind {
                TrapKind::Damage { damage } => { self.player_hp -= damage; self.add_message(format!("⚡ Trap deals {} damage!", damage), style::Color::Red); }
                TrapKind::Poison { damage, duration } => { self.status_effects.push(StatusEffect::new_poison(*damage, *duration)); self.add_message("☠️ You are poisoned by the trap!", style::Color::Red); }
                TrapKind::Pit { damage } => { self.player_hp -= damage; self.add_message(format!("🕳️ You fall into a pit! {} damage!", damage), style::Color::Red); }
            }
            if self.player_hp <= 0 { self.player_hp = 0; self.game_over = true; self.add_message("💀 You died from a trap!", style::Color::Red); }
        }

        fn apply_monster_ability(&mut self, monster: &Monster) {
            match &monster.ability {
                MonsterAbility::Poison { damage, duration } => { self.status_effects.push(StatusEffect::new_poison(*damage, *duration)); self.add_message(format!("☠️ {} poisons you!", monster.symbol), style::Color::Red); }
                MonsterAbility::Confuse { duration } => { self.status_effects.push(StatusEffect::new_confused(*duration)); self.add_message(format!("🌀 {} confuses you!", monster.symbol), style::Color::Magenta); }
                _ => {}
            }
        }

        pub fn fire_arrow(&mut self) {
            if self.game_over || self.paused { return; }
            if let Some(last) = self.last_arrow_time { if last.elapsed() < Duration::from_secs(1) { self.add_message("🏹 Arrow on cooldown.", style::Color::Yellow); return; } }
            self.last_arrow_time = Some(Instant::now());
            self.ranged_attack(5 + self.player_base_attack + self.equipment.total_attack(), '🏹');
        }
        pub fn fireball(&mut self) {
            if self.game_over || self.paused { return; }
            if let Some(last) = self.last_fireball_time { if last.elapsed() < Duration::from_secs(2) { self.add_message("🔥 Fireball on cooldown.", style::Color::Yellow); return; } }
            self.last_fireball_time = Some(Instant::now());
            self.ranged_attack(10 + self.level as i32 + self.equipment.total_attack(), '🔥');
        }
        pub fn use_wand(&mut self) {
            if self.game_over || self.paused { return; }
            let wand_idx = self.inventory.iter().position(|item| matches!(item.kind, ItemKind::WandMagicMissile { .. }));
            if let Some(idx) = wand_idx {
                let item = &mut self.inventory[idx];
                if let ItemKind::WandMagicMissile { charges, damage } = &mut item.kind {
                    if *charges <= 0 { self.add_message("🪄 Wand has no charges left!", style::Color::Yellow); return; }
                    *charges -= 1; self.ranged_attack(*damage, '🪄');
                    if *charges == 0 { self.inventory.remove(idx); self.add_message("🪄 Wand is spent and crumbles.", style::Color::Yellow); }
                }
            } else { self.add_message("No wand in inventory.", style::Color::Yellow); }
        }

        fn ranged_attack(&mut self, damage: i32, symbol: char) {
            let (dx, dy) = self.facing;
            let mut x = self.player_pos.x as i32 + dx; let mut y = self.player_pos.y as i32 + dy;
            while x >= 0 && x < MAP_WIDTH as i32 && y >= 0 && y < MAP_HEIGHT as i32 {
                let pos = Position { x: x as usize, y: y as usize };
                let tile = self.map[pos.y][pos.x];
                if tile == Tile::Wall || tile == Tile::LockedDoor { self.add_message(format!("{} hits a wall.", symbol), style::Color::White); break; }
                if let Some(idx) = self.monsters.iter().position(|m| m.is_alive() && m.pos == pos) {
                    let monster = &mut self.monsters[idx];
                    monster.hp -= damage;
                    self.add_message(format!("{} hits {} for {} damage!", symbol, monster.symbol, damage), style::Color::White);
                    if monster.hp <= 0 {
                        monster.alive = false;
                        self.add_message(format!("💥 {} killed!", monster.symbol), style::Color::Yellow);
                        self.score += 10; self.gain_xp(5 + self.level as i32); self.drop_items_from_monster(monster);
                    }
                    break;
                }
                x += dx; y += dy;
            }
        }

        pub fn heal(&mut self) {
            if self.game_over || self.paused { return; }
            if let Some(last) = self.last_heal_time { if last.elapsed() < Duration::from_secs(3) { self.add_message("💚 Heal on cooldown.", style::Color::Yellow); return; } }
            self.last_heal_time = Some(Instant::now());
            let healed = (15 + self.level as i32).min(self.player_max_hp - self.player_hp);
            self.player_hp += healed;
            self.add_message(format!("💚 You heal for {} HP!", healed), style::Color::Green);
        }

        pub fn enchant_weapon(&mut self, bonus: i32) {
            if let Some(weapon) = &mut self.equipment.weapon {
                if let ItemKind::Weapon { attack_bonus } = &mut weapon.kind {
                    *attack_bonus += bonus;
                    self.add_message(format!("⚡ Your weapon is enchanted! +{} attack", bonus), style::Color::Cyan);
                }
            } else { self.add_message("You have no weapon equipped.", style::Color::Yellow); }
        }
        pub fn enchant_armor(&mut self, bonus: i32) {
            let slots = [&mut self.equipment.shield, &mut self.equipment.helmet, &mut self.equipment.boots, &mut self.equipment.cloak];
            for slot in slots {
                if let Some(item) = slot {
                    match &mut item.kind {
                        ItemKind::Shield { defense_bonus } => { *defense_bonus += bonus; self.add_message(format!("🛡️ Your shield is enchanted! +{} defense", bonus), style::Color::Cyan); return; }
                        ItemKind::Helmet { defense_bonus } => { *defense_bonus += bonus; self.add_message(format!("⛑️ Your helmet is enchanted! +{} defense", bonus), style::Color::Cyan); return; }
                        ItemKind::Boots { defense_bonus, .. } => { *defense_bonus += bonus; self.add_message(format!("👢 Your boots are enchanted! +{} defense", bonus), style::Color::Cyan); return; }
                        ItemKind::Cloak { defense_bonus } => { *defense_bonus += bonus; self.add_message(format!("🧥 Your cloak is enchanted! +{} defense", bonus), style::Color::Cyan); return; }
                        _ => {}
                    }
                }
            }
            self.add_message("You have no armor equipped to enchant.", style::Color::Yellow);
        }

        pub fn open_shop(&mut self, shop: &Shop) {
            if self.paused || self.game_over { return; }
            self.add_message("🧝 Welcome to the shop!", style::Color::White);
            self.shop_ui(shop);
        }

        fn shop_ui(&mut self, shop: &Shop) {
            use input::get_input_blocking;
            let mut stdout = stdout();
            loop {
                let start_x = 2; let start_y = 5; let width = 40; let height = shop.items.len() as u16 + 4;
                for y in 0..height { for x in 0..width { stdout.queue(cursor::MoveTo(start_x + x, start_y + y)).unwrap().queue(style::Print(' ')).unwrap(); } }
                for x in 0..width {
                    stdout.queue(cursor::MoveTo(start_x + x, start_y)).unwrap().queue(style::Print('▔')).unwrap();
                    stdout.queue(cursor::MoveTo(start_x + x, start_y + height - 1)).unwrap().queue(style::Print('▁')).unwrap();
                }
                for y in 0..height {
                    stdout.queue(cursor::MoveTo(start_x, start_y + y)).unwrap().queue(style::Print('▕')).unwrap();
                    stdout.queue(cursor::MoveTo(start_x + width - 1, start_y + y)).unwrap().queue(style::Print('▏')).unwrap();
                }
                stdout.queue(cursor::MoveTo(start_x + 2, start_y + 1)).unwrap().queue(style::Print("--- Shop ---")).unwrap();
                for (i, (item, price)) in shop.items.iter().zip(shop.prices.iter()).enumerate() {
                    let line = format!(" {}) {} {}  [{} gold]", i + 1, item.symbol, item.name, price);
                    stdout.queue(cursor::MoveTo(start_x + 2, start_y + 2 + i as u16)).unwrap().queue(style::Print(format!("{:<36}", line))).unwrap();
                }
                stdout.queue(cursor::MoveTo(start_x + 2, start_y + height - 2)).unwrap().queue(style::Print("Select number to buy, Esc to leave")).unwrap();
                stdout.flush().unwrap();

                let key = get_input_blocking();
                match key {
                    event::KeyCode::Esc => return,
                    event::KeyCode::Char(c) if c.is_ascii_digit() && c != '0' => {
                        let idx = (c as u8 - '1' as u8) as usize;
                        if idx < shop.items.len() {
                            let price = shop.prices[idx];
                            if self.score >= price {
                                self.score -= price;
                                if self.inventory.len() < INVENTORY_SIZE {
                                    self.inventory.push(shop.items[idx].clone());
                                    self.add_message(format!("Bought {}.", shop.items[idx].name), style::Color::Green);
                                } else { self.add_message("Inventory full!", style::Color::Yellow); }
                            } else { self.add_message("Not enough gold!", style::Color::Red); }
                        }
                    }
                    _ => {}
                }
            }
        }

        fn descend_level(&mut self) {
            if self.level >= WIN_LEVEL && self.has_amulet { self.won = true; self.game_over = true; self.add_message("🎉 You have won the game!", style::Color::Green); return; }
            self.add_message(format!("🪜 Descending to level {}...", self.level + 1), style::Color::White);
            let new_level = self.level + 1;
            let new_biome = biome::Biome::random();
            let (map, rooms) = map_gen::generate(new_level, new_biome);
            let player_pos = rooms[0].center();
            let mut rng = rand::thread_rng();
            let mut positions = rooms[1..].iter().map(|room| room.random_pos()).collect::<Vec<_>>();
            rng.shuffle(&mut positions);
            let mut idx = 0; let mut monsters = Vec::new();

            if let Some(boss_pos) = positions.get(idx) { monsters.push(Monster::new(*boss_pos, new_level, true)); idx += 1; }
            for _ in 0..map_gen::MAX_MONSTERS.min(positions.len() - idx) {
                if idx >= positions.len() { break; }
                let pos = positions[idx]; idx += 1;
                if pos != player_pos { monsters.push(Monster::new(pos, new_level, false)); }
            }
            let mut treasures = Vec::new();
            for _ in 0..map_gen::MAX_TREASURES.min(positions.len() - idx) {
                if idx >= positions.len() { break; }
                let pos = positions[idx]; idx += 1;
                if pos != player_pos { treasures.push(Treasure::new(pos)); }
            }
            let mut potions = Vec::new();
            for _ in 0..map_gen::MAX_POTIONS.min(positions.len() - idx) {
                if idx >= positions.len() { break; }
                let pos = positions[idx]; idx += 1;
                if pos != player_pos { potions.push(Potion::new(pos)); }
            }
            let item_templates = vec![new_sword(), new_shield(), new_helmet(), new_ring(), new_boots(), new_amulet(), new_cloak(), new_scroll_teleport(), new_scroll_identify(), new_scroll_enchant_weapon(1), new_scroll_enchant_armor(1), new_wand_magic_missile(3, 8), new_food(20), new_key(), new_potion_heal(8), new_potion_strength(1)];
            let mut ground_items = Vec::new();
            for template in item_templates {
                if idx < positions.len() {
                    let pos = positions[idx]; idx += 1;
                    if pos != player_pos { ground_items.push(GroundItem { pos, item: template.clone() }); }
                }
            }
            if new_level == WIN_LEVEL {
                if idx < positions.len() { let pos = positions[idx]; idx += 1; ground_items.push(GroundItem { pos, item: new_amulet_of_yendor() }); }
                else if let Some(boss) = monsters.iter().find(|m| m.is_boss) { ground_items.push(GroundItem { pos: boss.pos, item: new_amulet_of_yendor() }); }
            }
            let mut traps = Vec::new();
            for _ in 0..rng.gen_range(2..=4) {
                if idx < positions.len() { let pos = positions[idx]; idx += 1; if pos != player_pos { traps.push(Trap::new(pos, new_level)); } }
            }
            let mut shops = Vec::new();
            if rng.gen_bool(0.3) {
                if idx < positions.len() { let pos = positions[idx]; idx += 1; if pos != player_pos { shops.push(Shop::new(pos, new_level)); } }
            }
            let stairs_pos = if idx < positions.len() { Some(positions[idx]) } else { Some(rooms[rooms.len() - 1].center()) };
            
            self.map = map; self.explored = vec![vec![false; MAP_WIDTH]; MAP_HEIGHT]; self.biome = new_biome;
            self.player_pos = player_pos; self.monsters = monsters; self.treasures = treasures; self.potions = potions;
            self.ground_items = ground_items; self.traps = traps; self.shops = shops; self.stairs = stairs_pos.map(Stairs::new);
            self.level = new_level; self.player_max_hp += 2; self.player_hp = self.player_max_hp;
            self.player_base_attack += 1; self.status_effects.clear();
            self.add_message("🌟 You feel stronger!", style::Color::Cyan);
            self.reveal_around_player();
        }

        pub fn tick_status_effects(&mut self) {
            let mut to_remove = Vec::new();
            for (i, effect) in self.status_effects.iter_mut().enumerate() {
                match effect.kind {
                    StatusKind::Poison => {
                        self.player_hp -= effect.damage;
                        self.add_message(format!("☠️ Poison deals {} damage!", effect.damage), style::Color::Red);
                        effect.duration -= 1;
                        if effect.duration <= 0 { to_remove.push(i); }
                    }
                    StatusKind::Starving => {}
                    StatusKind::Confused => {
                        effect.duration -= 1;
                        if effect.duration <= 0 { to_remove.push(i); self.add_message("🧠 You are no longer confused.", style::Color::Cyan); }
                    }
                }
                if self.player_hp <= 0 { self.player_hp = 0; self.game_over = true; self.add_message("💀 You succumb to poison!", style::Color::Red); return; }
            }
            for i in to_remove.into_iter().rev() { self.status_effects.remove(i); }
        }

        pub fn monster_turn(&mut self) {
            if self.game_over || self.paused { return; }
            let mut rng = rand::thread_rng();
            let player_pos = self.player_pos;
            for monster in &mut self.monsters {
                if !monster.is_alive() { continue; }
                match &monster.ability {
                    MonsterAbility::Teleport { range } => {
                        if rng.gen_bool(0.1) {
                            for _ in 0..10 {
                                let dx = rng.gen_range(-(*range)..=*range); let dy = rng.gen_range(-(*range)..=*range);
                                let new_x = monster.pos.x as i32 + dx; let new_y = monster.pos.y as i32 + dy;
                                if new_x >= 0 && new_x < MAP_WIDTH as i32 && new_y >= 0 && new_y < MAP_HEIGHT as i32 {
                                    let pos = Position { x: new_x as usize, y: new_y as usize };
                                    if self.map[pos.y][pos.x] != Tile::Wall && !self.monsters.iter().any(|m| m.is_alive() && m.pos == pos) && pos != player_pos {
                                        monster.pos = pos; self.add_message(format!("✨ {} teleports away!", monster.symbol), style::Color::Cyan); break;
                                    }
                                }
                            }
                        }
                    }
                    MonsterAbility::Summon { count } => {
                        if rng.gen_bool(0.05) {
                            for _ in 0..*count {
                                let dirs = [(0, -1), (0, 1), (-1, 0), (1, 0)];
                                for _ in 0..10 {
                                    let (dx, dy) = dirs[rng.gen_range(0..dirs.len())];
                                    let new_x = monster.pos.x as i32 + dx; let new_y = monster.pos.y as i32 + dy;
                                    if new_x >= 0 && new_x < MAP_WIDTH as i32 && new_y >= 0 && new_y < MAP_HEIGHT as i32 {
                                        let pos = Position { x: new_x as usize, y: new_y as usize };
                                        if self.map[pos.y][pos.x] != Tile::Wall && !self.monsters.iter().any(|m| m.is_alive() && m.pos == pos) && pos != player_pos {
                                            self.monsters.push(Monster::new(pos, self.level, false));
                                            self.add_message(format!("👾 {} summons a minion!", monster.symbol), style::Color::Yellow); break;
                                        }
                                    }
                                }
                            }
                        }
                    }
                    MonsterAbility::Heal { amount } => {
                        if monster.hp < monster.max_hp && rng.gen_bool(0.1) {
                            monster.hp = (monster.hp + amount).min(monster.max_hp);
                            self.add_message(format!("💚 {} heals itself!", monster.symbol), style::Color::Green);
                        }
                    }
                    MonsterAbility::Confuse { duration } => {
                        if rng.gen_bool(0.1) {
                            self.status_effects.push(StatusEffect::new_confused(*duration));
                            self.add_message(format!("🌀 {} confuses you!", monster.symbol), style::Color::Magenta);
                        }
                    }
                    MonsterAbility::Boss => { if monster.hp < monster.max_hp / 2 { monster.attack += 2; } }
                    _ => {}
                }
            }
            for monster in &mut self.monsters {
                if !monster.is_alive() { continue; }
                let dist = monster.pos.distance(player_pos);
                let can_see = dist <= monster.view_range as f64 && self.has_line_of_sight(monster.pos, player_pos);
                if let MonsterAbility::Ranged { damage, range } = &monster.ability {
                    if can_see && dist <= *range as f64 {
                        let dmg = (damage - self.equipment.total_defense()).max(1);
                        self.player_hp -= dmg;
                        self.add_message(format!("🏹 {} shoots you for {} damage!", monster.symbol, dmg), style::Color::Red);
                        if self.player_hp <= 0 { self.player_hp = 0; self.game_over = true; self.add_message("💀 You have been slain!", style::Color::Red); return; }
                        continue;
                    }
                }
                if (monster.pos.x as i32 - player_pos.x as i32).abs() <= 1 && (monster.pos.y as i32 - player_pos.y as i32).abs() <= 1 {
                    let dmg = (monster.attack - self.equipment.total_defense()).max(1);
                    self.player_hp -= dmg;
                    self.add_message(format!("💢 {} attacks you for {} damage!", monster.symbol, dmg), style::Color::Red);
                    self.apply_monster_ability(monster);
                    if self.player_hp <= 0 { self.player_hp = 0; self.game_over = true; self.add_message("💀 You have been slain!", style::Color::Red); return; }
                    continue;
                }
                if can_see {
                    let dx = (player_pos.x as i32 - monster.pos.x as i32).signum();
                    let dy = (player_pos.y as i32 - monster.pos.y as i32).signum();
                    let mut moves = vec![(dx, dy)];
                    if dx != 0 && dy != 0 { let mut opts = vec![(dx, 0), (0, dy)]; rng.shuffle(&mut opts); moves.extend(opts); }
                    for (dx, dy) in moves {
                        let new_x = monster.pos.x as i32 + dx; let new_y = monster.pos.y as i32 + dy;
                        if new_x < 0 || new_x >= MAP_WIDTH as i32 || new_y < 0 || new_y >= MAP_HEIGHT as i32 { continue; }
                        let new_pos = Position { x: new_x as usize, y: new_y as usize };
                        if self.map[new_pos.y][new_pos.x] == Tile::Wall { continue; }
                        if self.monsters.iter().any(|m| m.is_alive() && m.pos == new_pos && m.pos != monster.pos) { continue; }
                        if new_pos == player_pos { continue; }
                        monster.pos = new_pos; break;
                    }
                } else {
                    let dirs = [(0, -1), (0, 1), (-1, 0), (1, 0)];
                    let (dx, dy) = dirs[rng.gen_range(0..dirs.len())];
                    let new_x = monster.pos.x as i32 + dx; let new_y = monster.pos.y as i32 + dy;
                    if new_x < 0 || new_x >= MAP_WIDTH as i32 || new_y < 0 || new_y >= MAP_HEIGHT as i32 { continue; }
                    let new_pos = Position { x: new_x as usize, y: new_y as usize };
                    if self.map[new_pos.y][new_pos.x] == Tile::Wall { continue; }
                    if self.monsters.iter().any(|m| m.is_alive() && m.pos == new_pos && m.pos != monster.pos) { continue; }
                    if new_pos == player_pos { continue; }
                    monster.pos = new_pos;
                }
            }
        }

        pub fn use_scroll_teleport(&mut self) {
            if self.game_over || self.paused { return; }
            let idx = self.inventory.iter().position(|item| matches!(item.kind, ItemKind::ScrollTeleport));
            if let Some(idx) = idx {
                self.inventory.remove(idx);
                let mut rng = rand::thread_rng();
                for _ in 0..100 {
                    let x = rng.gen_range(1..MAP_WIDTH - 1); let y = rng.gen_range(1..MAP_HEIGHT - 1);
                    let pos = Position { x, y };
                    if self.map[y][x] != Tile::Wall && !self.monsters.iter().any(|m| m.is_alive() && m.pos == pos) && pos != self.player_pos {
                        self.player_pos = pos; self.reveal_around_player();
                        self.add_message("🌀 You teleport to a random location!", style::Color::Cyan); return;
                    }
                }
                self.add_message("Teleport failed!", style::Color::Red);
            } else { self.add_message("No scroll of teleport.", style::Color::Yellow); }
        }
        pub fn use_scroll_identify(&mut self) {
            if self.game_over || self.paused { return; }
            let idx = self.inventory.iter().position(|item| matches!(item.kind, ItemKind::ScrollIdentify));
            if let Some(idx) = idx {
                self.inventory.remove(idx);
                for y in 0..MAP_HEIGHT { for x in 0..MAP_WIDTH { self.explored[y][x] = true; } }
                self.add_message("📖 You identify the entire dungeon!", style::Color::Cyan);
            } else { self.add_message("No scroll of identify.", style::Color::Yellow); }
        }
        pub fn use_scroll_enchant_weapon(&mut self, bonus: i32) {
            if self.game_over || self.paused { return; }
            let idx = self.inventory.iter().position(|item| matches!(item.kind, ItemKind::ScrollEnchantWeapon { .. }));
            if let Some(idx) = idx { self.inventory.remove(idx); self.enchant_weapon(bonus); }
            else { self.add_message("No scroll of enchant weapon.", style::Color::Yellow); }
        }
        pub fn use_scroll_enchant_armor(&mut self, bonus: i32) {
            if self.game_over || self.paused { return; }
            let idx = self.inventory.iter().position(|item| matches!(item.kind, ItemKind::ScrollEnchantArmor { .. }));
            if let Some(idx) = idx { self.inventory.remove(idx); self.enchant_armor(bonus); }
            else { self.add_message("No scroll of enchant armor.", style::Color::Yellow); }
        }
        pub fn drink_potion_strength(&mut self, bonus: i32) {
            self.player_base_attack += bonus;
            self.add_message(format!("💪 You feel stronger! +{} attack", bonus), style::Color::Green);
        }
    }

    pub fn init_game() -> Game {
        let level = 1; let biome = biome::Biome::random();
        let (map, rooms) = map_gen::generate(level, biome);
        let player_pos = rooms[0].center();
        let mut rng = rand::thread_rng();
        let mut positions = rooms[1..].iter().map(|room| room.random_pos()).collect::<Vec<_>>();
        rng.shuffle(&mut positions);
        let mut idx = 0; let mut monsters = Vec::new();
        if let Some(boss_pos) = positions.get(idx) { monsters.push(Monster::new(*boss_pos, level, true)); idx += 1; }
        for _ in 0..map_gen::MAX_MONSTERS.min(positions.len() - idx) {
            if idx >= positions.len() { break; }
            let pos = positions[idx]; idx += 1;
            if pos != player_pos { monsters.push(Monster::new(pos, level, false)); }
        }
        let mut treasures = Vec::new();
        for _ in 0..map_gen::MAX_TREASURES.min(positions.len() - idx) {
            if idx >= positions.len() { break; }
            let pos = positions[idx]; idx += 1;
            if pos != player_pos { treasures.push(Treasure::new(pos)); }
        }
        let mut potions = Vec::new();
        for _ in 0..map_gen::MAX_POTIONS.min(positions.len() - idx) {
            if idx >= positions.len() { break; }
            let pos = positions[idx]; idx += 1;
            if pos != player_pos { potions.push(Potion::new(pos)); }
        }
        let item_templates = vec![new_sword(), new_shield(), new_helmet(), new_ring(), new_boots(), new_amulet(), new_cloak(), new_scroll_teleport(), new_scroll_identify(), new_scroll_enchant_weapon(1), new_scroll_enchant_armor(1), new_wand_magic_missile(3, 8), new_food(20), new_key(), new_potion_heal(8), new_potion_strength(1)];
        let mut ground_items = Vec::new();
        for template in item_templates {
            if idx < positions.len() { let pos = positions[idx]; idx += 1; if pos != player_pos { ground_items.push(GroundItem { pos, item: template.clone() }); } }
        }
        let mut traps = Vec::new();
        for _ in 0..rng.gen_range(2..=4) {
            if idx < positions.len() { let pos = positions[idx]; idx += 1; if pos != player_pos { traps.push(Trap::new(pos, level)); } }
        }
        let mut shops = Vec::new();
        if rng.gen_bool(0.3) {
            if idx < positions.len() { let pos = positions[idx]; idx += 1; if pos != player_pos { shops.push(Shop::new(pos, level)); } }
        }
        let stairs_pos = if idx < positions.len() { Some(positions[idx]) } else { Some(rooms[rooms.len() - 1].center()) };
        
        let mut game = Game::new(map, vec![vec![false; MAP_WIDTH]; MAP_HEIGHT], biome, player_pos, 20 + level * 2, 20 + level * 2, 3 + level, 0, 1, MAX_HUNGER, Equipment::new(), Vec::new(), (1, 0), monsters, treasures, potions, ground_items, stairs_pos.map(Stairs::new), Vec::new(), traps, shops, 0, level, false, false);
        game.add_message(format!("🌍 Biome: {:?}", biome), style::Color::White);
        game.add_message("Find the stairs 🪜 to go deeper. Defeat the boss 🐲 each level!", style::Color::White);
        game.add_message("1: Fireball  2: Heal  3: Wand  F: Arrow  I: Inventory  S: Save  P: Pause", style::Color::White);
        game.reveal_around_player();
        game
    }
}

// =============================================================================
// Module: rendering (EXPANDED with new tile emojis)
// =============================================================================
mod rendering {
    use super::*;
    use map_gen::{Tile, MAP_WIDTH, MAP_HEIGHT};
    use game::Game;
    use entities::StatusKind;

    pub fn render(game: &Game) -> Result<()> {
        let mut stdout = stdout();
        execute!(stdout, cursor::Hide, terminal::Clear(terminal::ClearType::All), cursor::MoveTo(0, 0))?;
        let border_color = style::Color::Blue;
        for x in 0..MAP_WIDTH + 2 {
            stdout.queue(cursor::MoveTo(x as u16, 0))?.queue(style::SetForegroundColor(border_color))?.queue(style::Print('▔'))?;
            stdout.queue(cursor::MoveTo(x as u16, MAP_HEIGHT as u16 + 1))?.queue(style::SetForegroundColor(border_color))?.queue(style::Print('▁'))?;
        }
        for y in 0..MAP_HEIGHT + 2 {
            stdout.queue(cursor::MoveTo(0, y as u16))?.queue(style::SetForegroundColor(border_color))?.queue(style::Print('▕'))?;
            stdout.queue(cursor::MoveTo(MAP_WIDTH as u16 + 1, y as u16))?.queue(style::SetForegroundColor(border_color))?.queue(style::Print('▏'))?;
        }
        for (y, row) in game.map.iter().enumerate() {
            for (x, tile) in row.iter().enumerate() {
                let display_x = x as u16 + 1; let display_y = y as u16 + 1;
                if !game.explored[y][x] {
                    stdout.queue(style::SetForegroundColor(style::Color::DarkGrey))?.queue(cursor::MoveTo(display_x, display_y))?.queue(style::Print('░'))?;
                    continue;
                }
                let mut is_trap = false;
                for trap in &game.traps {
                    if trap.pos.x == x && trap.pos.y == y && trap.is_active() {
                        is_trap = true;
                        stdout.queue(style::SetForegroundColor(style::Color::Yellow))?.queue(cursor::MoveTo(display_x, display_y))?.queue(style::Print('⚠'))?;
                        break;
                    }
                }
                if is_trap { continue; }
                let mut is_shop = false;
                for shop in &game.shops {
                    if shop.pos.x == x && shop.pos.y == y {
                        is_shop = true;
                        stdout.queue(style::SetForegroundColor(style::Color::Cyan))?.queue(cursor::MoveTo(display_x, display_y))?.queue(style::Print(shop.symbol))?;
                        break;
                    }
                }
                if is_shop { continue; }
                
                let (symbol, color) = match tile {
                    Tile::Wall => (game.biome.wall_tile(), game.biome.wall_color()),
                    Tile::Floor => (game.biome.floor_tile(), game.biome.floor_color()),
                    Tile::Door => ('🚪', style::Color::Yellow),
                    Tile::LockedDoor => ('🔒', style::Color::Red),
                    Tile::Water => ('🌊', style::Color::Cyan),
                    Tile::Lava => ('🌋', style::Color::Red),
                    Tile::SecretDoor => ('❓', style::Color::DarkGrey),
                    // NEW TILES
                    Tile::Ice => ('🧊', style::Color::Cyan),
                    Tile::Mud => ('🟤', style::Color::DarkGrey),
                    Tile::Web => ('🕸️', style::Color::White),
                    Tile::Sand => ('🟨', style::Color::Yellow),
                    Tile::Bridge => ('🌉', style::Color::DarkYellow),
                    Tile::Altar => ('🛐', style::Color::Magenta),
                    Tile::Chest => ('📦', style::Color::Yellow),
                };
                stdout.queue(style::SetForegroundColor(color))?.queue(cursor::MoveTo(display_x, display_y))?.queue(style::Print(symbol))?;
            }
        }
        for treasure in &game.treasures {
            if game.explored[treasure.pos.y][treasure.pos.x] {
                stdout.queue(style::SetForegroundColor(style::Color::Yellow))?.queue(cursor::MoveTo(treasure.pos.x as u16 + 1, treasure.pos.y as u16 + 1))?.queue(style::Print(treasure.symbol))?;
            }
        }
        for potion in &game.potions {
            if game.explored[potion.pos.y][potion.pos.x] {
                stdout.queue(style::SetForegroundColor(style::Color::Green))?.queue(cursor::MoveTo(potion.pos.x as u16 + 1, potion.pos.y as u16 + 1))?.queue(style::Print(potion.symbol))?;
            }
        }
        for ground in &game.ground_items {
            if game.explored[ground.pos.y][ground.pos.x] {
                stdout.queue(style::SetForegroundColor(style::Color::Cyan))?.queue(cursor::MoveTo(ground.pos.x as u16 + 1, ground.pos.y as u16 + 1))?.queue(style::Print(ground.item.symbol))?;
            }
        }
        for monster in &game.monsters {
            if monster.is_alive() && game.explored[monster.pos.y][monster.pos.x] {
                let color = if monster.is_boss { style::Color::Magenta } else { style::Color::Red };
                stdout.queue(style::SetForegroundColor(color))?.queue(cursor::MoveTo(monster.pos.x as u16 + 1, monster.pos.y as u16 + 1))?.queue(style::Print(monster.symbol))?;
            }
        }
        if let Some(stairs) = &game.stairs {
            if game.explored[stairs.pos.y][stairs.pos.x] {
                stdout.queue(style::SetForegroundColor(style::Color::Magenta))?.queue(cursor::MoveTo(stairs.pos.x as u16 + 1, stairs.pos.y as u16 + 1))?.queue(style::Print(stairs.symbol))?;
            }
        }
        stdout.queue(style::SetForegroundColor(style::Color::Cyan))?.queue(cursor::MoveTo(game.player_pos.x as u16 + 1, game.player_pos.y as u16 + 1))?.queue(style::Print('🧙'))?;

        let status_y = MAP_HEIGHT as u16 + 2;
        let attack_bonus = game.equipment.total_attack();
        let defense_bonus = game.equipment.total_defense();
        let speed_bonus = game.equipment.total_speed_bonus();
        let regen = game.equipment.total_regen();
        let status_effects_str = if game.status_effects.is_empty() { String::new() } else {
            game.status_effects.iter().map(|e| match e.kind {
                StatusKind::Poison => format!("☠️ Poisoned({})", e.duration),
                StatusKind::Starving => "🍽️ Starving".to_string(),
                StatusKind::Confused => "🌀 Confused".to_string(),
            }).collect::<Vec<_>>().join(" ")
        };
        let hp_percent = (game.player_hp as f32 / game.player_max_hp as f32 * 10.0).round() as usize;
        let hp_bar = "♥".repeat(hp_percent) + &"·".repeat(10 - hp_percent);
        let hunger_percent = (game.player_hunger as f32 / game::MAX_HUNGER as f32 * 10.0).round() as usize;
        let hunger_bar = "🍽️".repeat(hunger_percent) + &"·".repeat(10 - hunger_percent);
        let inv_count = game.inventory.len();
        let pause_indicator = if game.paused { "⏸️ PAUSED" } else { "" };
        let amulet_indicator = if game.has_amulet { "🏆" } else { "" };

        stdout.queue(cursor::MoveTo(1, status_y))?.queue(style::SetForegroundColor(style::Color::White))?.queue(style::Print(format!(
            "❤️ {}/{} [{}]  🍽️ {}/{}  ⚔️ {}+{}  🛡️ {}  💰 {}  Lv{}  XP {}/{}  📦{}/{}  🏃{:.0}%  ❤️‍🩹+{}  {}  {}  {}",
            game.player_hp, game.player_max_hp, hp_bar, game.player_hunger, game::MAX_HUNGER, hunger_bar,
            game.player_base_attack, attack_bonus, defense_bonus, game.score, game.player_level, game.player_xp,
            game.player_next_level_xp, inv_count, game::INVENTORY_SIZE, (1.0 / speed_bonus * 100.0), regen,
            status_effects_str, pause_indicator, amulet_indicator,
        )))?;

        let msg_y = status_y + 1;
        for (i, (msg, color)) in game.messages.iter().enumerate() {
            stdout.queue(cursor::MoveTo(1, msg_y + i as u16))?.queue(style::SetForegroundColor(*color))?.queue(style::Print(format!("{:<80}", msg)))?;
        }
        let instr_y = msg_y + game::MAX_MESSAGES as u16 + 1;
        stdout.queue(cursor::MoveTo(1, instr_y))?.queue(style::SetForegroundColor(style::Color::White))?.queue(style::Print("Move: arrows/WASD  1:Fireball  2:Heal  3:Wand  F:Arrow  I:Inventory  S:Save  P:Pause  Q:Quit"))?;
        stdout.flush()?;
        Ok(())
    }
}

// =============================================================================
// Module: input
// =============================================================================
mod input {
    use super::*;
    pub fn get_event_nonblocking() -> Option<event::Event> {
        event::poll(Duration::from_millis(0)).ok().and_then(|ready| if ready { event::read().ok() } else { None })
    }
    pub fn get_input_blocking() -> event::KeyCode {
        loop { if let Some(event::Event::Key(key_event)) = event::read().ok() { return key_event.code; } }
    }
}

// =============================================================================
// Module: save_load
// =============================================================================
mod save_load {
    use super::*;
    use game::Game;
    pub fn save_game(game: &Game) -> Result<()> {
        let serialized = serde_json::to_string_pretty(game)?;
        fs::write(SAVE_FILE, serialized)?;
        Ok(())
    }
    pub fn load_game() -> Result<Game> {
        let data = fs::read_to_string(SAVE_FILE)?;
        let game: Game = serde_json::from_str(&data)?;
        Ok(game)
    }
}

// =============================================================================
// Module: inventory_ui
// =============================================================================
mod inventory_ui {
    use super::*;
    use game::Game;
    use entities::GroundItem;
    use items::ItemKind;
    use input::get_input_blocking;
    use std::io::stdout;

    pub fn handle_inventory(game: &mut Game) {
        if game.inventory.is_empty() { game.add_message("Inventory is empty.", style::Color::Yellow); return; }
        loop {
            render_inventory(game);
            let key = get_input_blocking();
            match key {
                event::KeyCode::Esc | event::KeyCode::Char('i') => return,
                event::KeyCode::Char(c) if c.is_ascii_digit() && c != '0' => {
                    let idx = (c as u8 - '1' as u8) as usize;
                    if idx < game.inventory.len() { handle_item_action(game, idx); return; }
                }
                _ => {}
            }
        }
    }

    fn render_inventory(game: &Game) {
        let mut stdout = stdout();
        let start_x = 2; let start_y = 5; let width = 40; let height = game.inventory.len() as u16 + 4;
        for y in 0..height { for x in 0..width { stdout.queue(cursor::MoveTo(start_x + x, start_y + y)).unwrap().queue(style::Print(' ')).unwrap(); } }
        for x in 0..width {
            stdout.queue(cursor::MoveTo(start_x + x, start_y)).unwrap().queue(style::Print('▔')).unwrap();
            stdout.queue(cursor::MoveTo(start_x + x, start_y + height - 1)).unwrap().queue(style::Print('▁')).unwrap();
        }
        for y in 0..height {
            stdout.queue(cursor::MoveTo(start_x, start_y + y)).unwrap().queue(style::Print('▕')).unwrap();
            stdout.queue(cursor::MoveTo(start_x + width - 1, start_y + y)).unwrap().queue(style::Print('▏')).unwrap();
        }
        stdout.queue(cursor::MoveTo(start_x + 2, start_y + 1)).unwrap().queue(style::Print("--- Inventory ---")).unwrap();
        for (i, item) in game.inventory.iter().enumerate() {
            let stats = match &item.kind {
                ItemKind::Weapon { attack_bonus } => format!("+{} atk", attack_bonus),
                ItemKind::Shield { defense_bonus } | ItemKind::Helmet { defense_bonus } | ItemKind::Cloak { defense_bonus } => format!("+{} def", defense_bonus),
                ItemKind::Ring { attack_bonus, defense_bonus } => format!("+{} atk +{} def", attack_bonus, defense_bonus),
                ItemKind::Boots { defense_bonus, speed_bonus } => format!("+{} def, {:.0}% speed", defense_bonus, 1.0 / speed_bonus * 100.0),
                ItemKind::Amulet { health_regen } => format!("+{} regen", health_regen),
                ItemKind::ScrollTeleport => "teleport".to_string(), ItemKind::ScrollIdentify => "identify".to_string(),
                ItemKind::ScrollEnchantWeapon { bonus } | ItemKind::ScrollEnchantArmor { bonus } => format!("+{}", bonus),
                ItemKind::WandMagicMissile { charges, damage } => format!("{} dmg, {} chr", damage, charges),
                ItemKind::Food { hunger_restore } => format!("+{} hunger", hunger_restore),
                ItemKind::Key => "key".to_string(), ItemKind::PotionHeal { amount } => format!("heal {}", amount),
                ItemKind::PotionStrength { bonus } => format!("+{} atk", bonus), ItemKind::AmuletOfYendor => "🏆 WIN".to_string(),
            };
            stdout.queue(cursor::MoveTo(start_x + 2, start_y + 2 + i as u16)).unwrap().queue(style::Print(format!("{:<36}", format!(" {}) {} {}  [{}]", i+1, item.symbol, item.name, stats)))).unwrap();
        }
        stdout.queue(cursor::MoveTo(start_x + 2, start_y + height - 2)).unwrap().queue(style::Print("Press number, Esc to exit")).unwrap();
        stdout.flush().unwrap();
    }

    fn handle_item_action(game: &mut Game, idx: usize) {
        let item = game.inventory[idx].clone();
        match item.kind {
            ItemKind::ScrollTeleport => { game.use_scroll_teleport(); return; }
            ItemKind::ScrollIdentify => { game.use_scroll_identify(); return; }
            ItemKind::ScrollEnchantWeapon { bonus } => { game.use_scroll_enchant_weapon(bonus); game.inventory.remove(idx); return; }
            ItemKind::ScrollEnchantArmor { bonus } => { game.use_scroll_enchant_armor(bonus); game.inventory.remove(idx); return; }
            ItemKind::WandMagicMissile { .. } => { game.use_wand(); return; }
            ItemKind::Food { hunger_restore } => { game.eat_food(hunger_restore); game.inventory.remove(idx); return; }
            ItemKind::PotionHeal { amount } => { let healed = amount.min(game.player_max_hp - game.player_hp); game.player_hp += healed; game.add_message(format!("❤️ You heal for {} HP!", healed), style::Color::Green); game.inventory.remove(idx); return; }
            ItemKind::PotionStrength { bonus } => { game.drink_potion_strength(bonus); game.inventory.remove(idx); return; }
            ItemKind::Key => { game.add_message("You carry a key. Use it on a locked door.", style::Color::Yellow); return; }
            ItemKind::AmuletOfYendor => { game.add_message("You already have the Amulet! Head to level 5 and descend.", style::Color::Magenta); return; }
            _ => {}
        }
        loop {
            let mut stdout = stdout();
            let menu_x = 20; let menu_y = 10;
            for y in 0..6 { for x in 0..30 { stdout.queue(cursor::MoveTo(menu_x + x, menu_y + y)).unwrap().queue(style::Print(' ')).unwrap(); } }
            stdout.queue(cursor::MoveTo(menu_x, menu_y)).unwrap().queue(style::Print(format!("Item: {} {}", item.symbol, item.name))).unwrap();
            stdout.queue(cursor::MoveTo(menu_x, menu_y + 1)).unwrap().queue(style::Print("1) Equip")).unwrap();
            stdout.queue(cursor::MoveTo(menu_x, menu_y + 2)).unwrap().queue(style::Print("2) Drop")).unwrap();
            stdout.queue(cursor::MoveTo(menu_x, menu_y + 3)).unwrap().queue(style::Print("Esc) Cancel")).unwrap();
            stdout.flush().unwrap();
            let key = get_input_blocking();
            match key {
                event::KeyCode::Char('1') => { if equip_item(game, idx) { game.add_message(format!("Equipped {}.", item.name), style::Color::Cyan); } else { game.add_message("Cannot equip that item.", style::Color::Yellow); } return; }
                event::KeyCode::Char('2') => { let dropped = game.inventory.remove(idx); game.ground_items.push(GroundItem { pos: game.player_pos, item: dropped.clone() }); game.add_message(format!("Dropped {}.", dropped.name), style::Color::Cyan); return; }
                event::KeyCode::Esc => return,
                _ => {}
            }
        }
    }

    fn equip_item(game: &mut Game, inv_idx: usize) -> bool {
        use items::ItemKind;
        let item = game.inventory[inv_idx].clone();
        match &item.kind {
            ItemKind::Weapon { .. } => { if let Some(old) = game.equipment.weapon.take() { game.inventory.push(old); } game.equipment.weapon = Some(item); game.inventory.remove(inv_idx); true }
            ItemKind::Shield { .. } => { if let Some(old) = game.equipment.shield.take() { game.inventory.push(old); } game.equipment.shield = Some(item); game.inventory.remove(inv_idx); true }
            ItemKind::Helmet { .. } => { if let Some(old) = game.equipment.helmet.take() { game.inventory.push(old); } game.equipment.helmet = Some(item); game.inventory.remove(inv_idx); true }
            ItemKind::Ring { .. } => {
                if game.equipment.ring1.is_none() { game.equipment.ring1 = Some(item); game.inventory.remove(inv_idx); true }
                else if game.equipment.ring2.is_none() { game.equipment.ring2 = Some(item); game.inventory.remove(inv_idx); true }
                else { let old = game.equipment.ring1.take().unwrap(); game.inventory.push(old); game.equipment.ring1 = Some(item); game.inventory.remove(inv_idx); true }
            }
            ItemKind::Boots { .. } => { if let Some(old) = game.equipment.boots.take() { game.inventory.push(old); } game.equipment.boots = Some(item); game.inventory.remove(inv_idx); true }
            ItemKind::Amulet { .. } => { if let Some(old) = game.equipment.amulet.take() { game.inventory.push(old); } game.equipment.amulet = Some(item); game.inventory.remove(inv_idx); true }
            ItemKind::Cloak { .. } => { if let Some(old) = game.equipment.cloak.take() { game.inventory.push(old); } game.equipment.cloak = Some(item); game.inventory.remove(inv_idx); true }
            _ => false,
        }
    }
}

// =============================================================================
// Module: main_menu
// =============================================================================
mod main_menu {
    use super::*;
    use input::get_input_blocking;
    use std::io::stdout;

    pub enum MenuChoice { NewGame, LoadGame, Settings, Quit }

    pub fn show_main_menu() -> MenuChoice {
        loop {
            let mut stdout = stdout();
            execute!(stdout, cursor::MoveTo(0, 0), terminal::Clear(terminal::ClearType::All), style::SetForegroundColor(style::Color::White)).unwrap();
            stdout.queue(cursor::MoveTo(10, 5)).unwrap().queue(style::Print("🧙  Emoji Roguelike  🧙")).unwrap();
            stdout.queue(cursor::MoveTo(10, 7)).unwrap().queue(style::Print("1) New Game")).unwrap();
            stdout.queue(cursor::MoveTo(10, 8)).unwrap().queue(style::Print("2) Load Game")).unwrap();
            stdout.queue(cursor::MoveTo(10, 9)).unwrap().queue(style::Print("3) Settings")).unwrap();
            stdout.queue(cursor::MoveTo(10, 10)).unwrap().queue(style::Print("4) Quit")).unwrap();
            stdout.flush().unwrap();
            let key = get_input_blocking();
            match key {
                event::KeyCode::Char('1') => return MenuChoice::NewGame,
                event::KeyCode::Char('2') => return MenuChoice::LoadGame,
                event::KeyCode::Char('3') => return MenuChoice::Settings,
                event::KeyCode::Char('4') => return MenuChoice::Quit,
                _ => {}
            }
        }
    }
}

// =============================================================================
// Main
// =============================================================================
fn main() -> Result<()> {
    use map_gen::MAP_HEIGHT;
    use game::{Game, init_game, MAX_MESSAGES};
    use rendering::render;
    use save_load::{save_game, load_game};
    use input::{get_event_nonblocking, get_input_blocking};
    use inventory_ui::handle_inventory;
    use main_menu::{show_main_menu, MenuChoice};
    use settings::{Settings, load_settings, show_settings_menu, matches_key};

    let mut stdout = stdout();
    terminal::enable_raw_mode()?;
    execute!(stdout, terminal::EnterAlternateScreen, cursor::Hide, style::SetForegroundColor(style::Color::White))?;

    let mut settings = load_settings().unwrap_or_default();

    let mut game: Game;
    loop {
        match show_main_menu() {
            MenuChoice::NewGame => { game = init_game(); break; }
            MenuChoice::LoadGame => {
                match load_game() {
                    Ok(g) => { game = g; game.messages.clear(); game.messages.push_back(("Game loaded.".to_string(), style::Color::White)); break; }
                    Err(e) => {
                        execute!(stdout, cursor::MoveTo(10, 11), style::Print(format!("Load failed: {}. Press any key.", e)))?;
                        stdout.flush()?; get_input_blocking();
                    }
                }
            }
            MenuChoice::Settings => { show_settings_menu(&mut settings); }
            MenuChoice::Quit => {
                execute!(stdout, terminal::LeaveAlternateScreen, cursor::Show, style::SetForegroundColor(style::Color::White))?;
                terminal::disable_raw_mode()?; println!("Goodbye!"); return Ok(());
            }
        }
    }

    let mut player_timer = Instant::now();
    let mut monster_timer = Instant::now();
    let mut status_timer = Instant::now();
    let mut regen_timer = Instant::now();
    let mut hunger_timer = Instant::now();
    let regen_interval = Duration::from_secs(3);

    let mut key_up = false; let mut key_down = false; let mut key_left = false; let mut key_right = false;

    'main: loop {
        render(&game)?;
        if game.game_over {
            let status_y = MAP_HEIGHT as u16 + 2 + MAX_MESSAGES as u16 + 3;
            let msg = if game.won { "🎉 You won! Press any key to exit." } else { "💀 Game Over! Press any key to exit." };
            execute!(stdout, cursor::MoveTo(1, status_y), style::SetForegroundColor(style::Color::Yellow), style::Print(msg))?;
            stdout.flush()?;
            while event::read().ok().is_none() {}
            break;
        }

        while let Some(evt) = get_event_nonblocking() {
            if let event::Event::Key(key_event) = evt {
                let press = key_event.kind == event::KeyEventKind::Press;
                let release = key_event.kind == event::KeyEventKind::Release;
                let code = key_event.code;
                
                match code {
                    code if matches_key(&code, &settings.key_up) => { if press { key_up = true; } if release { key_up = false; } }
                    code if matches_key(&code, &settings.key_down) => { if press { key_down = true; } if release { key_down = false; } }
                    code if matches_key(&code, &settings.key_left) => { if press { key_left = true; } if release { key_left = false; } }
                    code if matches_key(&code, &settings.key_right) => { if press { key_right = true; } if release { key_right = false; } }
                    code if matches_key(&code, &settings.key_fireball) && press => game.fireball(),
                    code if matches_key(&code, &settings.key_heal) && press => game.heal(),
                    code if matches_key(&code, &settings.key_wand) && press => game.use_wand(),
                    code if matches_key(&code, &settings.key_inventory) && press => handle_inventory(&mut game),
                    code if matches_key(&code, &settings.key_save) && press => {
                        if let Err(e) = save_game(&game) { game.add_message(format!("❌ Save failed: {}", e), style::Color::Red); }
                        else { game.add_message("💾 Game saved.", style::Color::Cyan); }
                    }
                    code if matches_key(&code, &settings.key_pause) && press => {
                        game.paused = !game.paused;
                        game.add_message(if game.paused { "⏸️ Paused" } else { "▶️ Resumed" }, style::Color::Yellow);
                    }
                    code if matches_key(&code, &settings.key_quit) && press => { let _ = save_game(&game); break 'main; }
                    _ => {}
                }
            }
        }

        let mut dx = 0; let mut dy = 0;
        if key_up { dy -= 1; } if key_down { dy += 1; } if key_left { dx -= 1; } if key_right { dx += 1; }

        let speed_bonus = game.equipment.total_speed_bonus();
        let move_interval = Duration::from_secs_f32(PLAYER_MOVE_INTERVAL.as_secs_f32() * speed_bonus);

        if (dx != 0 || dy != 0) && player_timer.elapsed() >= move_interval && !game.paused {
            game.move_player(dx, dy); player_timer = Instant::now();
        }
        if monster_timer.elapsed() >= MONSTER_MOVE_INTERVAL && !game.paused { game.monster_turn(); monster_timer = Instant::now(); }
        if status_timer.elapsed() >= STATUS_TICK_INTERVAL && !game.paused { game.tick_status_effects(); status_timer = Instant::now(); }
        if hunger_timer.elapsed() >= HUNGER_TICK_INTERVAL && !game.paused { game.tick_hunger(); hunger_timer = Instant::now(); }

        let regen = game.equipment.total_regen();
        if regen > 0 && regen_timer.elapsed() >= regen_interval && !game.paused {
            let healed = regen.min(game.player_max_hp - game.player_hp);
            if healed > 0 { game.player_hp += healed; game.add_message(format!("❤️‍🩹 Amulet restores {} HP.", healed), style::Color::Green); }
            regen_timer = Instant::now();
        }
        std::thread::sleep(Duration::from_millis(10));
    }

    execute!(stdout, terminal::LeaveAlternateScreen, cursor::Show, style::SetForegroundColor(style::Color::White))?;
    terminal::disable_raw_mode()?;
    println!("Thanks for playing!");
    Ok(())
}