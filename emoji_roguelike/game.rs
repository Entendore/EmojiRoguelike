use crate::entity::{Enemy, Item, ItemKind, Player};
use crate::map::{GameMap, Tile, MAP_WIDTH, MAP_HEIGHT};
use rand::Rng;

pub struct CombatResult {
    pub player_msg: String,
    pub enemy_died: bool,
    #[allow(dead_code)]
    pub player_died: bool,
    pub xp_gained: usize,
    #[allow(dead_code)]
    pub leveled_up: bool,
}

pub fn player_attack_enemy(
    player: &Player,
    enemy: &mut Enemy,
) -> CombatResult {
    let base_damage = player.attack;
    let reduction = enemy.defense;
    let damage = if base_damage > reduction {
        base_damage - reduction + rand::thread_rng().gen_range(0..=2)
    } else {
        rand::thread_rng().gen_range(0..=1)
    };

    let actual_damage = damage.max(1);
    enemy.hp = enemy.hp.saturating_sub(actual_damage);
    let killed = enemy.hp == 0;
    if killed {
        enemy.alive = false;
    }

    let msg = if killed {
        format!(
            "⚔️ You hit {} for {} damage! {} defeated! +{} XP",
            enemy.name, actual_damage, enemy.emoji, enemy.xp_reward
        )
    } else {
        format!(
            "⚔️ You hit {} for {} damage ({} HP left)",
            enemy.name, actual_damage, enemy.hp
        )
    };

    CombatResult {
        player_msg: msg,
        enemy_died: killed,
        player_died: false,
        xp_gained: if killed { enemy.xp_reward } else { 0 },
        leveled_up: false,
    }
}

pub fn enemy_attack_player(enemy: &Enemy, player: &mut Player) -> String {
    let base_damage = enemy.attack;
    let reduction = player.defense;
    let damage = if base_damage > reduction {
        base_damage - reduction + rand::thread_rng().gen_range(0..=2)
    } else {
        rand::thread_rng().gen_range(0..=1)
    };

    let actual_damage = damage.max(1);
    player.hp = player.hp.saturating_sub(actual_damage);

    if player.hp == 0 {
        format!(
            "💥 {} hits you for {} damage! Slain!",
            enemy.emoji, actual_damage
        )
    } else {
        format!(
            "💥 {} hits you for {} damage! ({} HP left)",
            enemy.emoji, actual_damage, player.hp
        )
    }
}

/// Try to move the player. Returns combat message if enemy was bumped into.
pub fn try_move_player(
    dx: i32,
    dy: i32,
    player: &mut Player,
    map: &mut GameMap,
    enemies: &mut Vec<Enemy>,
) -> Option<CombatResult> {
    let nx = (player.x as i32 + dx) as usize;
    let ny = (player.y as i32 + dy) as usize;

    if nx >= MAP_WIDTH || ny >= MAP_HEIGHT {
        return None;
    }

    // Check for enemy at target position
    if let Some(enemy) = enemies.iter_mut().find(|e| e.alive && e.x == nx && e.y == ny) {
        let result = player_attack_enemy(player, enemy);
        return Some(result);
    }

    if map.is_walkable(nx, ny) {
        player.x = nx;
        player.y = ny;
    }

    None
}

/// Handle tile effects after the player has moved. Returns messages.
pub fn handle_tile_effects(player: &mut Player, map: &mut GameMap) -> Vec<String> {
    let mut messages = Vec::new();
    let tile = map.tiles[player.x][player.y];

    match tile {
        Tile::Lava => {
            let dmg = rand::thread_rng().gen_range(5..=8);
            player.hp = player.hp.saturating_sub(dmg);
            messages.push(format!("🌋 Lava burn! -{} HP", dmg));
        }
        Tile::Trap => {
            let triggered = map.trigger_trap(player.x, player.y);
            if triggered {
                let dmg = rand::thread_rng().gen_range(8..=15);
                player.hp = player.hp.saturating_sub(dmg);
                messages.push(format!("🔸 Spike trap! -{} HP", dmg));
            }
        }
        Tile::ShallowWater => {
            // Small chance of slipping (cosmetic message)
            if rand::thread_rng().gen_bool(0.1) {
                messages.push("🌊 You splash through shallow water.".to_string());
            }
        }
        Tile::Mud => {
            if rand::thread_rng().gen_bool(0.1) {
                messages.push("🟤 Squelch... thick mud slows your step.".to_string());
            }
        }
        Tile::Web => {
            // First time message
            if rand::thread_rng().gen_bool(0.5) {
                messages.push("🕸️ You push through sticky webs.".to_string());
            }
        }
        _ => {}
    }

    messages
}

/// Check if player stepped on an item. Returns messages.
pub fn check_item_pickup(
    player: &mut Player,
    items: &mut Vec<(usize, usize, Item)>,
) -> Vec<String> {
    let mut messages = Vec::new();
    items.retain(|(x, y, item)| {
        if *x == player.x && *y == player.y {
            if item.is_auto_use() {
                if let Some((msg, _)) = player.use_item(0) {
                    messages.push(msg);
                }
            } else {
                match player.pickup_item(item.clone()) {
                    Ok(()) => messages.push(format!("📦 Picked up {}", item.name)),
                    Err(e) => messages.push(format!("❌ {}", e)),
                }
            }
            false
        } else {
            true
        }
    });
    messages
}

/// Check if player is on stairs
pub fn check_stairs(player: &Player, map: &GameMap) -> bool {
    map.tiles[player.x][player.y] == Tile::StairsDown
}

/// Use a spellbook: damage all visible enemies
pub fn use_spellbook(_player: &Player, enemies: &mut Vec<Enemy>, map: &GameMap) -> String {
    let mut hit = 0;
    let mut total_dmg = 0;
    for enemy in enemies.iter_mut() {
        if enemy.alive && map.visible[enemy.x][enemy.y] {
            let dmg: usize = rand::thread_rng().gen_range(15..=25);
            let actual = dmg.saturating_sub(enemy.defense / 2).max(1);
            enemy.hp = enemy.hp.saturating_sub(actual);
            if enemy.hp == 0 {
                enemy.alive = false;
            }
            total_dmg += actual;
            hit += 1;
        }
    }
    format!("📗 Spellbook deals {} total damage to {} enemies!", total_dmg, hit)
}

/// Use a compass: reveal stairs direction
pub fn use_compass(player: &Player, map: &mut GameMap) -> String {
    // Find stairs
    let mut stairs_pos = None;
    for x in 0..MAP_WIDTH {
        for y in 0..MAP_HEIGHT {
            if map.tiles[x][y] == Tile::StairsDown && map.revealed[x][y] {
                stairs_pos = Some((x, y));
                break;
            }
        }
        if stairs_pos.is_some() {
            break;
        }
    }

    // If stairs not yet revealed, reveal them
    if stairs_pos.is_none() {
        for x in 0..MAP_WIDTH {
            for y in 0..MAP_HEIGHT {
                if map.tiles[x][y] == Tile::StairsDown {
                    map.revealed[x][y] = true;
                    stairs_pos = Some((x, y));
                    break;
                }
            }
            if stairs_pos.is_some() {
                break;
            }
        }
    }

    if let Some((sx, sy)) = stairs_pos {
        let dx = (sx as i32 - player.x as i32).signum();
        let dy = (sy as i32 - player.y as i32).signum();
        let dir = match (dx, dy) {
            (0, -1) => "North",
            (0, 1) => "South",
            (-1, 0) => "West",
            (1, 0) => "East",
            (1, -1) => "Northeast",
            (-1, -1) => "Northwest",
            (1, 1) => "Southeast",
            (-1, 1) => "Southwest",
            _ => "somewhere nearby",
        };
        let dist = (sx as i32 - player.x as i32).abs() + (sy as i32 - player.y as i32).abs();
        format!("🧭 Stairs are {} ({} tiles away)!", dir, dist)
    } else {
        "🧭 Compass spins... no stairs on this floor?".into()
    }
}

/// Place items on the map
pub fn place_items<R: Rng>(
    rng: &mut R,
    map: &GameMap,
    floor: usize,
    occupied: &mut std::collections::HashSet<(usize, usize)>,
) -> Vec<(usize, usize, Item)> {
    let mut items = Vec::new();
    let num_items = rng.gen_range(6..=10) + floor.min(4);

    for _ in 0..num_items {
        if map.rooms.is_empty() {
            continue;
        }
        let room_idx = rng.gen_range(0..map.rooms.len());
        if let Some((x, y)) = map.get_random_walkable(rng, room_idx) {
            if !occupied.contains(&(x, y)) {
                if let Some(item) = Item::random_floor_loot(rng, floor) {
                    items.push((x, y, item));
                    occupied.insert((x, y));
                }
            }
        }
    }

    // Place the Amulet on the final floor
    if floor == crate::map::MAX_FLOOR {
        if let Some(room) = map.rooms.last() {
            if let Some((x, y)) = Some(room.center()) {
                items.push((
                    x,
                    y,
                    Item::new(ItemKind::Amulet, "🔮", "Amulet of Yendor"),
                ));
            }
        }
    }

    items
}