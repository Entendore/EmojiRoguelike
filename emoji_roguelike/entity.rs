use rand::Rng;
use std::collections::HashSet;

// ─── Item Definitions ───────────────────────────────────────────────

#[derive(Clone, Debug, PartialEq)]
pub enum ItemKind {
    // Potions / Consumables
    HealthPotion,
    BigHealthPotion,
    StrengthPotion,
    DefensePotion,
    SpeedPotion,
    Meat,
    Bread,
    Mushroom,        // random effect
    // Equipment
    Sword,
    Shield,
    Boots,
    Amulet,
    // Special
    Gold(usize),
    Gem,             // valuable
    ScrollOfMapping,
    Compass,         // reveals stairs direction
    Spellbook,       // damages all visible enemies
    TreasureChest,   // random loot burst
}

#[derive(Clone, Debug)]
pub struct Item {
    pub kind: ItemKind,
    pub emoji: String,
    pub name: String,
}

impl Item {
    pub fn new(kind: ItemKind, emoji: &str, name: &str) -> Self {
        Self {
            kind,
            emoji: emoji.to_string(),
            name: name.to_string(),
        }
    }

    #[allow(dead_code)]
    pub fn description(&self) -> String {
        match &self.kind {
            ItemKind::HealthPotion => "Restores 20 HP".into(),
            ItemKind::BigHealthPotion => "Restores 50 HP".into(),
            ItemKind::StrengthPotion => "+2 Attack permanently".into(),
            ItemKind::DefensePotion => "+1 Defense permanently".into(),
            ItemKind::SpeedPotion => "Next 20 turns: enemies act half-speed".into(),
            ItemKind::Meat => "Restores 10 HP".into(),
            ItemKind::Bread => "Restores 8 HP".into(),
            ItemKind::Mushroom => "Random effect: great boon or curse!".into(),
            ItemKind::Gold(n) => format!("Worth {} gold", n),
            ItemKind::Gem => "Worth 50-100 gold".into(),
            ItemKind::ScrollOfMapping => "Reveals the entire floor".into(),
            ItemKind::Compass => "Reveals staircase direction".into(),
            ItemKind::Spellbook => "Deals 15-25 damage to all visible enemies".into(),
            ItemKind::TreasureChest => "Contains a random powerful item!".into(),
            ItemKind::Sword => "+3 Attack permanently".into(),
            ItemKind::Shield => "+2 Defense permanently".into(),
            ItemKind::Boots => "+1 to movement, harder for enemies to catch you".into(),
            ItemKind::Amulet => "The Amulet of Yendor! You win!".into(),
        }
    }

    /// Auto-used items (go to inventory = false, these trigger immediately on pickup)
    pub fn is_auto_use(&self) -> bool {
        matches!(
            &self.kind,
            ItemKind::Gold(_)
                | ItemKind::Gem
                | ItemKind::Sword
                | ItemKind::Shield
                | ItemKind::Boots
                | ItemKind::TreasureChest
                | ItemKind::Amulet
        )
    }

    pub fn random_floor_loot<R: Rng>(rng: &mut R, floor: usize) -> Option<Self> {
        let roll: f64 = rng.gen();
        if roll < 0.18 {
            Some(Item::new(ItemKind::Gold(rng.gen_range(5..=15 + floor * 5)), "💰", "Gold"))
        } else if roll < 0.30 {
            Some(Item::new(ItemKind::HealthPotion, "❤️", "Health Potion"))
        } else if roll < 0.38 {
            Some(Item::new(ItemKind::Meat, "🍖", "Meat"))
        } else if roll < 0.44 {
            Some(Item::new(ItemKind::Bread, "🍞", "Bread"))
        } else if roll < 0.52 {
            Some(Item::new(ItemKind::StrengthPotion, "🧪", "Str Potion"))
        } else if roll < 0.59 {
            Some(Item::new(ItemKind::DefensePotion, "🔵", "Def Potion"))
        } else if roll < 0.65 {
            Some(Item::new(ItemKind::ScrollOfMapping, "📜", "Map Scroll"))
        } else if roll < 0.71 {
            Some(Item::new(ItemKind::Mushroom, "🍄", "Mushroom"))
        } else if roll < 0.76 {
            Some(Item::new(ItemKind::Gem, "💎", "Gem"))
        } else if roll < 0.81 {
            Some(Item::new(ItemKind::Compass, "🧭", "Compass"))
        } else if roll < 0.85 {
            if floor >= 5 {
                Some(Item::new(ItemKind::BigHealthPotion, "💖", "Big HP Potion"))
            } else {
                Some(Item::new(ItemKind::HealthPotion, "❤️", "Health Potion"))
            }
        } else if roll < 0.89 {
            if floor >= 3 {
                Some(Item::new(ItemKind::SpeedPotion, "⚡", "Speed Potion"))
            } else {
                Some(Item::new(ItemKind::Meat, "🍖", "Meat"))
            }
        } else if roll < 0.92 {
            if floor >= 4 {
                Some(Item::new(ItemKind::Spellbook, "📗", "Spellbook"))
            } else {
                Some(Item::new(ItemKind::Bread, "🍞", "Bread"))
            }
        } else if roll < 0.95 {
            if floor >= 3 {
                Some(Item::new(ItemKind::Sword, "⚔️", "Sword"))
            } else {
                Some(Item::new(ItemKind::Meat, "🍖", "Meat"))
            }
        } else if roll < 0.97 {
            if floor >= 4 {
                Some(Item::new(ItemKind::Shield, "🛡️", "Shield"))
            } else {
                Some(Item::new(ItemKind::HealthPotion, "❤️", "Health Potion"))
            }
        } else if roll < 0.99 {
            if floor >= 6 {
                Some(Item::new(ItemKind::Boots, "👢", "Boots"))
            } else {
                Some(Item::new(ItemKind::DefensePotion, "🔵", "Def Potion"))
            }
        } else {
            if floor >= 7 {
                Some(Item::new(ItemKind::TreasureChest, "📦", "Treasure Chest"))
            } else {
                Some(Item::new(ItemKind::Gem, "💎", "Gem"))
            }
        }
    }
}

// ─── Enemy Definitions ──────────────────────────────────────────────

#[derive(Clone, Debug)]
pub struct EnemyTemplate {
    pub name: String,
    pub emoji: String,
    pub hp: usize,
    pub attack: usize,
    pub defense: usize,
    pub xp_reward: usize,
    pub min_floor: usize,
    pub speed: usize,
    /// Biome preference: None = any biome, Some = more likely in this biome
    #[allow(dead_code)]
    pub biome: Option<usize>,
}

fn enemy_templates() -> Vec<EnemyTemplate> {
    vec![
        // ── Floor 1-2: Stone Dungeon ──
        EnemyTemplate { name: "Rat".into(),         emoji: "🐀".into(), hp: 8,  attack: 2,  defense: 0, xp_reward: 5,  min_floor: 1,  speed: 1, biome: None },
        EnemyTemplate { name: "Spider".into(),       emoji: "🕷️".into(), hp: 10, attack: 3,  defense: 0, xp_reward: 7,  min_floor: 1,  speed: 1, biome: None },
        EnemyTemplate { name: "Bat".into(),          emoji: "🦇".into(), hp: 6,  attack: 4,  defense: 0, xp_reward: 6,  min_floor: 1,  speed: 2, biome: None },
        EnemyTemplate { name: "Snake".into(),        emoji: "🐍".into(), hp: 7,  attack: 3,  defense: 0, xp_reward: 6,  min_floor: 1,  speed: 1, biome: None },
        EnemyTemplate { name: "Wolf".into(),         emoji: "🐺".into(), hp: 14, attack: 4,  defense: 1, xp_reward: 10, min_floor: 1,  speed: 1, biome: None },
        // ── Floor 2-3: Early threats ──
        EnemyTemplate { name: "Skeleton".into(),     emoji: "💀".into(), hp: 18, attack: 5,  defense: 2, xp_reward: 15, min_floor: 2,  speed: 1, biome: None },
        EnemyTemplate { name: "Scorpion".into(),     emoji: "🦂".into(), hp: 12, attack: 6,  defense: 1, xp_reward: 12, min_floor: 2,  speed: 1, biome: None },
        EnemyTemplate { name: "Boar".into(),         emoji: "🐗".into(), hp: 20, attack: 5,  defense: 2, xp_reward: 13, min_floor: 2,  speed: 2, biome: None },
        // ── Floor 3-4: Crystal Cavern ──
        EnemyTemplate { name: "Ghost".into(),        emoji: "👻".into(), hp: 15, attack: 6,  defense: 1, xp_reward: 18, min_floor: 3,  speed: 1, biome: None },
        EnemyTemplate { name: "Crab".into(),         emoji: "🦀".into(), hp: 22, attack: 4,  defense: 5, xp_reward: 16, min_floor: 3,  speed: 2, biome: None },
        EnemyTemplate { name: "Slime".into(),        emoji: "🦠".into(), hp: 16, attack: 5,  defense: 2, xp_reward: 14, min_floor: 3,  speed: 1, biome: None },
        // ── Floor 4-5: Mid-game ──
        EnemyTemplate { name: "Zombie".into(),       emoji: "🧟".into(), hp: 25, attack: 6,  defense: 3, xp_reward: 20, min_floor: 4,  speed: 2, biome: None },
        EnemyTemplate { name: "Eagle".into(),        emoji: "🦅".into(), hp: 14, attack: 8,  defense: 1, xp_reward: 22, min_floor: 4,  speed: 1, biome: None },
        EnemyTemplate { name: "Crocodile".into(),    emoji: "🐊".into(), hp: 30, attack: 7,  defense: 4, xp_reward: 24, min_floor: 4,  speed: 2, biome: None },
        // ── Floor 5-6: Enchanted Forest ──
        EnemyTemplate { name: "Demon".into(),        emoji: "👹".into(), hp: 35, attack: 8,  defense: 4, xp_reward: 30, min_floor: 5,  speed: 1, biome: None },
        EnemyTemplate { name: "Vampire".into(),      emoji: "🧛".into(), hp: 30, attack: 9,  defense: 3, xp_reward: 32, min_floor: 5,  speed: 1, biome: None },
        // ── Floor 6-7: ──
        EnemyTemplate { name: "Ogre".into(),         emoji: "👹".into(), hp: 40, attack: 9,  defense: 5, xp_reward: 35, min_floor: 6,  speed: 1, biome: None },
        EnemyTemplate { name: "Golem".into(),        emoji: "🗿".into(), hp: 55, attack: 7,  defense: 8, xp_reward: 38, min_floor: 6,  speed: 3, biome: None },
        // ── Floor 7-8: Frozen Depths ──
        EnemyTemplate { name: "FrostWraith".into(),  emoji: "❄️".into(), hp: 28, attack: 10, defense: 3, xp_reward: 36, min_floor: 7,  speed: 1, biome: None },
        EnemyTemplate { name: "PolarBear".into(),    emoji: "🐻‍❄️".into(), hp: 45, attack: 10, defense: 5, xp_reward: 40, min_floor: 7,  speed: 2, biome: None },
        // ── Floor 8-9: Volcanic Core ──
        EnemyTemplate { name: "Dragon".into(),       emoji: "🐉".into(), hp: 60, attack: 12, defense: 6, xp_reward: 50, min_floor: 8,  speed: 2, biome: None },
        EnemyTemplate { name: "FireSalamander".into(), emoji: "🦎".into(), hp: 35, attack: 11, defense: 4, xp_reward: 42, min_floor: 8,  speed: 1, biome: None },
        // ── Floor 9-10: Lava Boss tier ──
        EnemyTemplate { name: "Lich".into(),         emoji: "🧙".into(), hp: 50, attack: 11, defense: 6, xp_reward: 48, min_floor: 9,  speed: 1, biome: None },
        EnemyTemplate { name: "Phoenix".into(),      emoji: "🔥".into(), hp: 40, attack: 14, defense: 4, xp_reward: 55, min_floor: 9,  speed: 1, biome: None },
        // ── Floor 10-12: Swamp & Graveyard ──
        EnemyTemplate { name: "SwampThing".into(),   emoji: "🐲".into(), hp: 50, attack: 10, defense: 7, xp_reward: 52, min_floor: 10, speed: 2, biome: None },
        EnemyTemplate { name: "Banshee".into(),      emoji: "😱".into(), hp: 35, attack: 13, defense: 3, xp_reward: 50, min_floor: 11, speed: 1, biome: None },
        // ── Floor 12-15: Final depths ──
        EnemyTemplate { name: "DeathKnight".into(),  emoji: "⚔️".into(), hp: 65, attack: 14, defense: 7, xp_reward: 60, min_floor: 12, speed: 1, biome: None },
        EnemyTemplate { name: "ShadowFiend".into(),  emoji: "🌑".into(), hp: 55, attack: 16, defense: 5, xp_reward: 65, min_floor: 13, speed: 1, biome: None },
        EnemyTemplate { name: "EldritchHorror".into(), emoji: "👁️".into(), hp: 70, attack: 15, defense: 6, xp_reward: 70, min_floor: 14, speed: 2, biome: None },
    ]
}

#[derive(Clone, Debug)]
pub struct Enemy {
    pub name: String,
    pub emoji: String,
    pub x: usize,
    pub y: usize,
    pub hp: usize,
    pub max_hp: usize,
    pub attack: usize,
    pub defense: usize,
    pub xp_reward: usize,
    pub speed: usize,
    pub turn_counter: usize,
    pub alive: bool,
}

impl Enemy {
    pub fn from_template(template: &EnemyTemplate, x: usize, y: usize, floor: usize) -> Self {
        let scale = 1.0 + (floor.saturating_sub(template.min_floor)) as f64 * 0.12;
        let hp = (template.hp as f64 * scale) as usize;
        let attack = (template.attack as f64 * scale) as usize;
        let defense = (template.defense as f64 * scale) as usize;
        let xp = (template.xp_reward as f64 * scale) as usize;

        Self {
            name: template.name.clone(),
            emoji: template.emoji.clone(),
            x,
            y,
            hp,
            max_hp: hp,
            attack,
            defense,
            xp_reward: xp,
            speed: template.speed,
            turn_counter: 0,
            alive: true,
        }
    }

    pub fn generate_enemies<R: Rng>(
        rng: &mut R,
        floor: usize,
        map_tiles: &crate::map::GameMap,
        occupied: &HashSet<(usize, usize)>,
    ) -> Vec<Self> {
        let templates = enemy_templates();
        let available: Vec<&EnemyTemplate> = templates
            .iter()
            .filter(|t| t.min_floor <= floor)
            .collect();

        if available.is_empty() {
            return Vec::new();
        }

        let num_enemies = rng.gen_range(5..=8) + floor.min(6);
        let mut enemies = Vec::new();
        let mut occ = occupied.clone();

        for _ in 0..num_enemies {
            if map_tiles.rooms.len() <= 1 {
                continue;
            }
            let room_idx = rng.gen_range(1..map_tiles.rooms.len());

            if let Some((x, y)) = map_tiles.get_random_walkable(rng, room_idx) {
                if !occ.contains(&(x, y)) {
                    let template = available[rng.gen_range(0..available.len())];
                    enemies.push(Enemy::from_template(template, x, y, floor));
                    occ.insert((x, y));
                }
            }
        }

        // Boss on every 5th floor
        if floor % 5 == 0 && floor > 0 {
            if let Some((x, y)) = map_tiles.get_random_walkable(rng, map_tiles.rooms.len() - 1) {
                if !occ.contains(&(x, y)) {
                    let boss_name = match floor {
                        5 => "Forest Guardian",
                        10 => "Volcanic Overlord",
                        15 => "The Dark Lord",
                        _ => "Dungeon Boss",
                    };
                    let boss_emoji = match floor {
                        5 => "🦌",
                        10 => "👹",
                        15 => "👿",
                        _ => "👿",
                    };
                    let boss = EnemyTemplate {
                        name: boss_name.into(),
                        emoji: boss_emoji.into(),
                        hp: 80 + floor * 12,
                        attack: 12 + floor * 2,
                        defense: 6 + floor,
                        xp_reward: 100 + floor * 15,
                        min_floor: floor,
                        speed: 1,
                        biome: None,
                    };
                    enemies.push(Enemy::from_template(&boss, x, y, floor));
                }
            }
        }

        enemies
    }

    #[allow(dead_code)]
    pub fn take_turn(
        &mut self,
        px: usize,
        py: usize,
        map: &crate::map::GameMap,
        enemies: &[Enemy],
        _turn: usize,
    ) -> Option<(usize, usize)> {
        self.turn_counter += 1;
        if self.turn_counter < self.speed {
            return None;
        }
        self.turn_counter = 0;

        let dist = ((self.x as i32 - px as i32).abs() + (self.y as i32 - py as i32).abs()) as usize;

        if dist <= 8 {
            let dx = (px as i32 - self.x as i32).signum() as i32;
            let dy = (py as i32 - self.y as i32).signum() as i32;

            let moves = if rand::thread_rng().gen_bool(0.5) {
                vec![(dx, 0i32), (0i32, dy)]
            } else {
                vec![(0i32, dy), (dx, 0i32)]
            };

            for (mx, my) in &moves {
                let nx = (self.x as i32 + mx) as usize;
                let ny = (self.y as i32 + my) as usize;

                if nx == px && ny == py {
                    return None;
                }

                if map.is_walkable(nx, ny) {
                    let blocked = enemies
                        .iter()
                        .any(|e| e.alive && e.x == nx && e.y == ny && e.x != self.x && e.y != self.y);
                    if !blocked {
                        self.x = nx;
                        self.y = ny;
                        return Some((nx, ny));
                    }
                }
            }
        } else if rand::thread_rng().gen_bool(0.3) {
            let dirs = [(0, -1i32), (0, 1), (-1, 0), (1, 0)];
            let (dx, dy) = dirs[rand::thread_rng().gen_range(0..4)];
            let nx = (self.x as i32 + dx) as usize;
            let ny = (self.y as i32 + dy) as usize;
            if map.is_walkable(nx, ny)
                && !enemies
                    .iter()
                    .any(|e| e.alive && e.x == nx && e.y == ny && (e.x != self.x || e.y != self.y))
            {
                self.x = nx;
                self.y = ny;
            }
        }

        None
    }
}

// ─── Player ─────────────────────────────────────────────────────────

#[derive(Clone, Debug)]
pub struct Player {
    pub x: usize,
    pub y: usize,
    pub hp: usize,
    pub max_hp: usize,
    pub attack: usize,
    pub defense: usize,
    pub level: usize,
    pub xp: usize,
    pub xp_to_next: usize,
    pub gold: usize,
    pub inventory: Vec<Item>,
    pub max_inventory: usize,
    pub speed_turns: usize,  // remaining turns of speed buff
}

impl Player {
    pub fn new(x: usize, y: usize) -> Self {
        Self {
            x,
            y,
            hp: 40,
            max_hp: 40,
            attack: 5,
            defense: 2,
            level: 1,
            xp: 0,
            xp_to_next: 20,
            gold: 0,
            inventory: Vec::new(),
            max_inventory: 16,
            speed_turns: 0,
        }
    }

    pub fn gain_xp(&mut self, amount: usize) -> bool {
        self.xp += amount;
        let mut leveled = false;
        while self.xp >= self.xp_to_next {
            self.xp -= self.xp_to_next;
            self.level += 1;
            self.max_hp += 8;
            self.hp = self.max_hp;
            self.attack += 1;
            self.defense += 1;
            self.xp_to_next = (self.xp_to_next as f64 * 1.4) as usize;
            leveled = true;
        }
        leveled
    }

    pub fn pickup_item(&mut self, item: Item) -> Result<(), String> {
        if self.inventory.len() >= self.max_inventory {
            return Err("Inventory full!".into());
        }
        self.inventory.push(item);
        Ok(())
    }

    /// Use item from inventory. Returns (message, item_kind).
    pub fn use_item(&mut self, index: usize) -> Option<(String, ItemKind)> {
        if index >= self.inventory.len() {
            return None;
        }
        let item = self.inventory.remove(index);
        let msg = match &item.kind {
            ItemKind::HealthPotion => {
                let healed = 20.min(self.max_hp - self.hp);
                self.hp += healed;
                format!("❤️ Health Potion! +{} HP", healed)
            }
            ItemKind::BigHealthPotion => {
                let healed = 50.min(self.max_hp - self.hp);
                self.hp += healed;
                format!("💖 Big Health Potion! +{} HP", healed)
            }
            ItemKind::StrengthPotion => {
                self.attack += 2;
                "🧪 Strength Potion! +2 Attack".into()
            }
            ItemKind::DefensePotion => {
                self.defense += 1;
                "🔵 Defense Potion! +1 Defense".into()
            }
            ItemKind::SpeedPotion => {
                self.speed_turns = 30;
                "⚡ Speed Potion! Enemies move slower for 30 turns!".into()
            }
            ItemKind::Meat => {
                let healed = 10.min(self.max_hp - self.hp);
                self.hp += healed;
                format!("🍖 Ate Meat! +{} HP", healed)
            }
            ItemKind::Bread => {
                let healed = 8.min(self.max_hp - self.hp);
                self.hp += healed;
                format!("🍞 Ate Bread! +{} HP", healed)
            }
            ItemKind::Mushroom => {
                use rand::Rng;
                let roll: f64 = rand::thread_rng().gen();
                if roll < 0.3 {
                    // Great boon
                    self.hp = self.max_hp;
                    self.attack += 2;
                    self.defense += 1;
                    "🍄 Magic Mushroom! Full HP +2 ATK +1 DEF!".into()
                } else if roll < 0.6 {
                    // Good
                    let healed = 30.min(self.max_hp - self.hp);
                    self.hp += healed;
                    format!("🍄 Tasty Mushroom! +{} HP", healed)
                } else if roll < 0.85 {
                    // Neutral/bad
                    self.hp = self.hp.saturating_sub(5);
                    "🍄 Poisonous Mushroom! -5 HP...".into()
                } else {
                    // Terrible
                    self.hp = self.hp.saturating_sub(15);
                    self.attack = self.attack.saturating_sub(1);
                    "🍄 Deadly Mushroom! -15 HP -1 ATK!".into()
                }
            }
            ItemKind::Gold(n) => {
                self.gold += n;
                format!("💰 Picked up {} gold!", n)
            }
            ItemKind::Gem => {
                let value = rand::thread_rng().gen_range(50..=100);
                self.gold += value;
                format!("💎 Sold Gem for {} gold!", value)
            }
            ItemKind::ScrollOfMapping => {
                "📜 Scroll used! (map revealed)".into()
            }
            ItemKind::Compass => {
                "🧭 Compass used! (stairs revealed)".into()
            }
            ItemKind::Spellbook => {
                "📗 Spellbook channeled! (enemies hit!)".into()
            }
            ItemKind::TreasureChest => {
                // Give a random bonus
                use rand::Rng;
                let roll: f64 = rand::thread_rng().gen();
                if roll < 0.33 {
                    self.attack += 3;
                    "📦 Chest: Found an Enchanted Sword! +3 ATK".into()
                } else if roll < 0.66 {
                    self.defense += 2;
                    self.max_hp += 10;
                    self.hp = (self.hp + 10).min(self.max_hp);
                    "📦 Chest: Found Armor Set! +2 DEF +10 Max HP".into()
                } else {
                    let gold = rand::thread_rng().gen_range(50..=150);
                    self.gold += gold;
                    format!("📦 Chest: Found {} gold!", gold)
                }
            }
            ItemKind::Sword => {
                self.attack += 3;
                "⚔️ Found a Sword! +3 Attack".into()
            }
            ItemKind::Shield => {
                self.defense += 2;
                "🛡️ Found a Shield! +2 Defense".into()
            }
            ItemKind::Boots => {
                "👢 Found Swift Boots! You move faster!".into()
            }
            ItemKind::Amulet => {
                "🔮 You found the Amulet of Yendor!".into()
            }
        };
        Some((msg, item.kind))
    }

    /// Tick down timed buffs
    pub fn tick_buffs(&mut self) {
        if self.speed_turns > 0 {
            self.speed_turns -= 1;
        }
    }
}