mod map;
mod entity;
mod game;
mod render;

use crossterm::event::{self, Event, KeyCode, KeyEventKind};
use entity::{Enemy, Item, ItemKind, Player};
use game::{check_item_pickup, check_stairs, enemy_attack_player, handle_tile_effects, place_items, try_move_player, use_compass, use_spellbook};
use map::GameMap;
use map::MAX_FLOOR;
use render::Renderer;
use std::collections::HashSet;
use std::io;

const FOV_RADIUS: usize = 9;

#[derive(PartialEq)]
enum GameState {
    Title,
    Playing,
    Dead,
    Win,
}

struct Game {
    state: GameState,
    map: GameMap,
    player: Player,
    enemies: Vec<Enemy>,
    items: Vec<(usize, usize, Item)>,
    messages: Vec<String>,
    floor: usize,
    turn: usize,
    renderer: Renderer,
}

impl Game {
    fn new() -> Self {
        let renderer = Renderer::new();
        Self {
            state: GameState::Title,
            map: GameMap::new(),
            player: Player::new(0, 0),
            enemies: Vec::new(),
            items: Vec::new(),
            messages: Vec::new(),
            floor: 1,
            turn: 0,
            renderer,
        }
    }

    fn start_new_game(&mut self) {
        self.floor = 1;
        self.turn = 0;
        self.messages.clear();
        self.player = Player::new(0, 0);
        self.generate_floor();
        self.state = GameState::Playing;
        self.add_message("🏰 You enter the dungeon... Find the 🔮 Amulet!".to_string());
        self.add_message(format!("📍 Biome: {}", self.map.biome.name()));
        self.add_message("💡 WASD=Move  >=Descend  1-9=Item  G=Grab".to_string());
    }

    fn generate_floor(&mut self) {
        self.map.generate(self.floor);

        if let Some(room) = self.map.rooms.first() {
            let (px, py) = room.center();
            self.player.x = px;
            self.player.y = py;
        }

        let mut occupied = HashSet::new();
        occupied.insert((self.player.x, self.player.y));

        self.enemies = Enemy::generate_enemies(
            &mut rand::thread_rng(),
            self.floor,
            &self.map,
            &occupied,
        );

        self.items = place_items(&mut rand::thread_rng(), &self.map, self.floor, &mut occupied);

        self.map.compute_fov(self.player.x, self.player.y, FOV_RADIUS);

        self.add_message(format!("═══ Floor {} ═══", self.floor));
        self.add_message(format!("📍 {}", self.map.biome.emoji().to_string() + " " + self.map.biome.name()));
    }

    fn add_message(&mut self, msg: String) {
        self.messages.push(msg);
        if self.messages.len() > 100 {
            self.messages.remove(0);
        }
    }

    fn handle_player_move(&mut self, dx: i32, dy: i32) {
        let result = try_move_player(dx, dy, &mut self.player, &mut self.map, &mut self.enemies);
        if let Some(combat_result) = result {
            self.add_message(combat_result.player_msg.clone());

            if combat_result.enemy_died {
                if self.player.gain_xp(combat_result.xp_gained) {
                    self.add_message(format!(
                        "🎉 Level up! You are now level {}!",
                        self.player.level
                    ));
                    self.add_message(format!(
                        "   HP: {} | ATK: {} | DEF: {}",
                        self.player.max_hp, self.player.attack, self.player.defense
                    ));
                }
            }
        } else {
            // Item pickup
            let msgs = check_item_pickup(&mut self.player, &mut self.items);
            for msg in msgs {
                self.add_message(msg);
            }

            // Tile effects (lava, traps, etc.)
            let tile_msgs = handle_tile_effects(&mut self.player, &mut self.map);
            for msg in tile_msgs {
                self.add_message(msg);
            }
        }

        self.turn += 1;
        self.player.tick_buffs();

        // Check death from tile damage
        if self.player.hp == 0 {
            self.state = GameState::Dead;
            self.add_message("💀 You perished from environmental hazards!".to_string());
            return;
        }

        self.process_enemy_turns();
        self.update_fov();
    }

    fn process_enemy_turns(&mut self) {
        let px = self.player.x;
        let py = self.player.y;

        let all_positions: Vec<Option<(usize, usize)>> = self
            .enemies
            .iter()
            .map(|e| if e.alive { Some((e.x, e.y)) } else { None })
            .collect();

        let mut attack_msgs: Vec<String> = Vec::new();
        let mut player_died = false;

        // If player has speed buff, enemies act slower (skip every other turn)
        let skip_enemies = self.player.speed_turns > 0 && self.turn % 2 == 1;

        if !skip_enemies {
            for (i, enemy) in self.enemies.iter_mut().enumerate() {
                if !enemy.alive {
                    continue;
                }

                let old_x = enemy.x;
                let old_y = enemy.y;

                let others: Vec<(usize, usize)> = all_positions
                    .iter()
                    .enumerate()
                    .filter(|(j, pos)| *j != i && pos.is_some())
                    .map(|(_, pos)| pos.unwrap())
                    .collect();

                Self::move_enemy(enemy, px, py, &self.map, &others);

                if enemy.x == px && enemy.y == py {
                    enemy.x = old_x;
                    enemy.y = old_y;
                }

                let dist_x = (enemy.x as i32 - px as i32).abs();
                let dist_y = (enemy.y as i32 - py as i32).abs();

                if dist_x <= 1 && dist_y <= 1 && (enemy.x != px || enemy.y != py) {
                    let msg = enemy_attack_player(enemy, &mut self.player);
                    attack_msgs.push(msg);

                    if self.player.hp == 0 {
                        player_died = true;
                        break;
                    }
                }
            }
        }

        for msg in attack_msgs {
            self.add_message(msg);
        }

        if player_died {
            self.state = GameState::Dead;
        }
    }

    fn move_enemy(
        enemy: &mut crate::entity::Enemy,
        px: usize,
        py: usize,
        map: &GameMap,
        other_positions: &[(usize, usize)],
    ) {
        use rand::Rng;

        enemy.turn_counter += 1;
        if enemy.turn_counter < enemy.speed {
            return;
        }
        enemy.turn_counter = 0;

        let dist = ((enemy.x as i32 - px as i32).abs() + (enemy.y as i32 - py as i32).abs()) as usize;

        if dist <= 8 {
            let dx = (px as i32 - enemy.x as i32).signum();
            let dy = (py as i32 - enemy.y as i32).signum();

            let moves = if rand::thread_rng().gen_bool(0.5) {
                vec![(dx, 0i32), (0i32, dy)]
            } else {
                vec![(0i32, dy), (dx, 0i32)]
            };

            for (mx, my) in &moves {
                let nx = (enemy.x as i32 + mx) as usize;
                let ny = (enemy.y as i32 + my) as usize;

                if nx == px && ny == py {
                    return;
                }

                if map.is_walkable(nx, ny) {
                    let blocked = other_positions.iter().any(|(ox, oy)| *ox == nx && *oy == ny);
                    if !blocked {
                        // Enemies take damage from lava too
                        if map.tiles[nx][ny] == crate::map::Tile::Lava {
                            // Some enemies avoid lava (smart ones), others don't care
                            if rand::thread_rng().gen_bool(0.5) {
                                enemy.hp = enemy.hp.saturating_sub(3);
                                if enemy.hp == 0 {
                                    enemy.alive = false;
                                }
                            }
                        }
                        enemy.x = nx;
                        enemy.y = ny;
                        return;
                    }
                }
            }
        } else if rand::thread_rng().gen_bool(0.3) {
            let dirs = [(0i32, -1i32), (0, 1), (-1, 0), (1, 0)];
            let (dx, dy) = dirs[rand::thread_rng().gen_range(0..4)];
            let nx = (enemy.x as i32 + dx) as usize;
            let ny = (enemy.y as i32 + dy) as usize;
            if map.is_walkable(nx, ny)
                && !other_positions.iter().any(|(ox, oy)| *ox == nx && *oy == ny)
            {
                enemy.x = nx;
                enemy.y = ny;
            }
        }
    }

    fn try_descend(&mut self) {
        if check_stairs(&self.player, &self.map) {
            if self.floor >= MAX_FLOOR {
                self.state = GameState::Win;
                return;
            }
            self.floor += 1;
            self.generate_floor();
            let heal = 5;
            self.player.hp = (self.player.hp + heal).min(self.player.max_hp);
            self.add_message(format!("🪜 Descended to floor {}. +{} HP", self.floor, heal));
        } else {
            self.add_message("❌ No stairs here!".to_string());
        }
    }

    fn use_inventory_item(&mut self, index: usize) {
        if index == 0 || index > self.player.inventory.len() {
            return;
        }
        let idx = index - 1;

        // Pre-use effects for items that need map access
        let item_kind = self.player.inventory.get(idx).map(|i| i.kind.clone());
        if let Some(kind) = item_kind.clone() {
            match kind {
                ItemKind::ScrollOfMapping => {
                    for x in 0..map::MAP_WIDTH {
                        for y in 0..map::MAP_HEIGHT {
                            self.map.revealed[x][y] = true;
                        }
                    }
                }
                ItemKind::Compass => {
                    let msg = use_compass(&self.player, &mut self.map);
                    self.add_message(msg);
                }
                ItemKind::Spellbook => {
                    let msg = use_spellbook(&self.player, &mut self.enemies, &self.map);
                    self.add_message(msg);
                }
                _ => {}
            }
        }

        if let Some((msg, kind)) = self.player.use_item(idx) {
            // Don't double-print for items we already handled above
            if !matches!(kind, ItemKind::ScrollOfMapping | ItemKind::Compass | ItemKind::Spellbook) {
                self.add_message(msg);
            }
            if kind == ItemKind::Amulet {
                self.state = GameState::Win;
            }
        }
    }

    fn update_fov(&mut self) {
        self.map.compute_fov(self.player.x, self.player.y, FOV_RADIUS);
    }

    fn handle_input(&mut self) -> io::Result<bool> {
        if event::poll(std::time::Duration::from_millis(50))? {
            if let Event::Key(key) = event::read()? {
                if key.kind != KeyEventKind::Press {
                    return Ok(true);
                }

                match self.state {
                    GameState::Title => {
                        self.start_new_game();
                    }
                    GameState::Playing => {
                        match key.code {
                            KeyCode::Char('w') | KeyCode::Up => self.handle_player_move(0, -1),
                            KeyCode::Char('s') | KeyCode::Down => self.handle_player_move(0, 1),
                            KeyCode::Char('a') | KeyCode::Left => self.handle_player_move(-1, 0),
                            KeyCode::Char('d') | KeyCode::Right => self.handle_player_move(1, 0),
                            KeyCode::Char('>') | KeyCode::Char('.') => self.try_descend(),
                            KeyCode::Char('q') | KeyCode::Esc => return Ok(false),
                            KeyCode::Char(c) if c.is_ascii_digit() && c != '0' => {
                                self.use_inventory_item(c.to_digit(10).unwrap() as usize);
                            }
                            KeyCode::Char('g') => {
                                let msgs = check_item_pickup(&mut self.player, &mut self.items);
                                if msgs.is_empty() {
                                    self.add_message("❌ Nothing to pick up here.".to_string());
                                } else {
                                    for msg in msgs {
                                        self.add_message(msg);
                                    }
                                }
                            }
                            _ => {}
                        }
                    }
                    GameState::Dead | GameState::Win => {
                        match key.code {
                            KeyCode::Char('r') | KeyCode::Char('R') => {
                                self.start_new_game();
                            }
                            KeyCode::Char('q') | KeyCode::Esc => return Ok(false),
                            _ => {}
                        }
                    }
                }
            }
        }
        Ok(true)
    }

    fn run(&mut self) -> io::Result<()> {
        self.renderer.init()?;

        self.renderer.render_title_screen()?;

        loop {
            if event::poll(std::time::Duration::from_millis(100))? {
                if let Event::Key(key) = event::read()? {
                    if key.kind == KeyEventKind::Press {
                        break;
                    }
                }
            }
        }

        self.start_new_game();

        let mut running = true;
        while running {
            match self.state {
                GameState::Playing => {
                    self.renderer.render(
                        &self.map,
                        &self.player,
                        &self.enemies,
                        &self.items,
                        &self.messages,
                        self.floor,
                        self.turn,
                    )?;
                    running = self.handle_input()?;
                }
                GameState::Dead => {
                    self.renderer.render_death_screen(&self.player, self.floor, self.turn)?;
                    running = self.handle_input()?;
                }
                GameState::Win => {
                    self.renderer.render_win_screen(&self.player, self.floor, self.turn)?;
                    running = self.handle_input()?;
                }
                _ => {}
            }
        }

        self.renderer.cleanup()?;
        Ok(())
    }
}

fn main() -> io::Result<()> {
    let mut game = Game::new();
    game.run()
}