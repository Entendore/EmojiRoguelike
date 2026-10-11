use crossterm::{
    cursor::MoveTo,
    execute,
    queue,
    style::{Color, Print, SetBackgroundColor, SetForegroundColor},
    terminal::{Clear, ClearType},
};
use std::io::{self, Write};

use crate::entity::{Enemy, Item, Player};
use crate::map::{Biome, GameMap, Tile};

const VIEWPORT_W: usize = 40;
const VIEWPORT_H: usize = 22;
const UI_X: usize = 82;

pub struct Renderer {
    pub stdout: io::Stdout,
}

impl Renderer {
    pub fn new() -> Self {
        Self {
            stdout: io::stdout(),
        }
    }

    pub fn init(&mut self) -> io::Result<()> {
        crossterm::terminal::enable_raw_mode()?;
        execute!(
            self.stdout,
            crossterm::terminal::EnterAlternateScreen,
            Clear(ClearType::All),
            crossterm::cursor::Hide
        )
    }

    pub fn cleanup(&mut self) -> io::Result<()> {
        execute!(
            self.stdout,
            crossterm::cursor::Show,
            crossterm::terminal::LeaveAlternateScreen,
        )?;
        crossterm::terminal::disable_raw_mode()
    }

    pub fn render(
        &mut self,
        map: &GameMap,
        player: &Player,
        enemies: &[Enemy],
        items: &[(usize, usize, Item)],
        messages: &[String],
        floor: usize,
        turn: usize,
    ) -> io::Result<()> {
        queue!(self.stdout, Clear(ClearType::All))?;

        self.render_map(map, player, enemies, items)?;
        self.render_ui(player, messages, floor, turn, map.biome)?;
        self.render_minimap(map, player, enemies)?;

        self.stdout.flush()
    }

    fn render_map(
        &mut self,
        map: &GameMap,
        player: &Player,
        enemies: &[Enemy],
        items: &[(usize, usize, Item)],
    ) -> io::Result<()> {
        let cam_x = player.x.saturating_sub(VIEWPORT_W / 2);
        let cam_y = player.y.saturating_sub(VIEWPORT_H / 2);
        let cam_x = cam_x.min(crate::map::MAP_WIDTH.saturating_sub(VIEWPORT_W));
        let cam_y = cam_y.min(crate::map::MAP_HEIGHT.saturating_sub(VIEWPORT_H));

        let bg = map.biome.bg_color();

        for vy in 0..VIEWPORT_H {
            for vx in 0..VIEWPORT_W {
                let mx = cam_x + vx;
                let my = cam_y + vy;

                let term_x = (vx * 2) as u16;
                let term_y = vy as u16;

                if mx >= crate::map::MAP_WIDTH || my >= crate::map::MAP_HEIGHT {
                    queue!(
                        self.stdout,
                        MoveTo(term_x, term_y),
                        SetBackgroundColor(Color::Rgb { r: 0, g: 0, b: 0 }),
                        Print("  ")
                    )?;
                    continue;
                }

                let visible = map.visible[mx][my];
                let revealed = map.revealed[mx][my];

                if visible {
                    // Player
                    if mx == player.x && my == player.y {
                        queue!(
                            self.stdout,
                            MoveTo(term_x, term_y),
                            SetBackgroundColor(Color::Rgb { r: bg.0, g: bg.1, b: bg.2 }),
                            SetForegroundColor(Color::Yellow),
                            Print("🧙")
                        )?;
                        continue;
                    }

                    // Enemies
                    if let Some(enemy) = enemies.iter().find(|e| e.alive && e.x == mx && e.y == my) {
                        let color = if enemy.hp < enemy.max_hp / 2 {
                            Color::Red
                        } else {
                            Color::Rgb { r: 255, g: 100, b: 100 }
                        };
                        queue!(
                            self.stdout,
                            MoveTo(term_x, term_y),
                            SetBackgroundColor(Color::Rgb { r: bg.0, g: bg.1, b: bg.2 }),
                            SetForegroundColor(color),
                            Print(&enemy.emoji)
                        )?;
                        continue;
                    }

                    // Items
                    if let Some(item) = items.iter().find(|(ix, iy, _)| *ix == mx && *iy == my) {
                        queue!(
                            self.stdout,
                            MoveTo(term_x, term_y),
                            SetBackgroundColor(Color::Rgb { r: bg.0, g: bg.1, b: bg.2 }),
                            SetForegroundColor(Color::Cyan),
                            Print(&item.2.emoji)
                        )?;
                        continue;
                    }

                    // Tiles
                    self.render_tile(term_x, term_y, map.tiles[mx][my], map.biome, false)?;
                } else if revealed {
                    self.render_tile(term_x, term_y, map.tiles[mx][my], map.biome, true)?;
                } else {
                    queue!(
                        self.stdout,
                        MoveTo(term_x, term_y),
                        SetBackgroundColor(Color::Black),
                        Print("  ")
                    )?;
                }
            }
        }

        Ok(())
    }

    fn render_tile(
        &mut self,
        x: u16,
        y: u16,
        tile: Tile,
        biome: Biome,
        dim: bool,
    ) -> io::Result<()> {
        let bg = biome.bg_color();

        let (display, color) = match tile {
            Tile::Wall => {
                let (r, g, b) = biome.wall_color();
                (biome.wall_emoji().to_string(), Color::Rgb { r, g, b })
            }
            Tile::Floor => {
                let (r, g, b) = biome.floor_color();
                (biome.floor_char().to_string(), Color::Rgb { r, g, b })
            }
            Tile::StairsDown => ("🪜".into(), Color::Yellow),
            Tile::Door => ("🚪".into(), Color::Rgb { r: 139, g: 90, b: 43 }),
            Tile::Water => ("💧".into(), Color::Rgb { r: 30, g: 80, b: 180 }),
            Tile::ShallowWater => ("🌊".into(), Color::Rgb { r: 60, g: 120, b: 200 }),
            Tile::Lava => ("🪰".into(), Color::Rgb { r: 255, g: 80, b: 0 }),
            Tile::Trap => ("·".into(), Color::Rgb { r: 60, g: 60, b: 60 }), // hidden!
            Tile::Ice => ("❄️".into(), Color::Rgb { r: 180, g: 220, b: 255 }),
            Tile::Grass => ("🌿".into(), Color::Rgb { r: 50, g: 140, b: 40 }),
            Tile::Mud => ("🟤".into(), Color::Rgb { r: 100, g: 70, b: 40 }),
            Tile::Moss => ("🟢".into(), Color::Rgb { r: 60, g: 120, b: 50 }),
            Tile::Crystal => ("💎".into(), Color::Rgb { r: 180, g: 130, b: 255 }),
            Tile::Rubble => ("🪨".into(), Color::Rgb { r: 120, g: 110, b: 100 }),
            Tile::Blood => ("🩸".into(), Color::Rgb { r: 180, g: 30, b: 30 }),
            Tile::Bones => ("🦴".into(), Color::Rgb { r: 200, g: 190, b: 170 }),
            Tile::Web => ("🕸️".into(), Color::Rgb { r: 180, g: 180, b: 180 }),
        };

        let fg = if dim {
            Color::Rgb { r: 50, g: 50, b: 50 }
        } else {
            color
        };

        // For single-char floor tiles, pad to 2 columns
        let display_str = if display.chars().count() == 1 {
            format!(" {}", display)
        } else {
            display
        };

        queue!(
            self.stdout,
            MoveTo(x, y),
            SetForegroundColor(fg),
            SetBackgroundColor(Color::Rgb { r: bg.0, g: bg.1, b: bg.2 }),
            Print(display_str)
        )
    }

    fn render_ui(
        &mut self,
        player: &Player,
        messages: &[String],
        floor: usize,
        turn: usize,
        biome: Biome,
    ) -> io::Result<()> {
        let x = UI_X as u16;

        // Title with biome
        queue!(
            self.stdout,
            MoveTo(x, 0),
            SetForegroundColor(Color::Magenta),
            Print(format!("═══ {} Emoji Roguelike ═══", biome.emoji()))
        )?;

        // Biome name
        queue!(
            self.stdout,
            MoveTo(x, 1),
            SetForegroundColor(Color::Rgb {
                r: biome.wall_color().0,
                g: biome.wall_color().1,
                b: biome.wall_color().2
            }),
            Print(format!("  📍 {}", biome.name()))
        )?;

        // Player stats
        queue!(
            self.stdout,
            MoveTo(x, 3),
            SetForegroundColor(Color::Yellow),
            Print("🧙 Hero Stats")
        )?;

        // HP bar
        let hp_ratio = if player.max_hp > 0 { player.hp as f64 / player.max_hp as f64 } else { 0.0 };
        let hp_bar_len = 16;
        let filled = (hp_ratio * hp_bar_len as f64) as usize;
        let hp_color = if hp_ratio > 0.6 {
            Color::Green
        } else if hp_ratio > 0.3 {
            Color::Yellow
        } else {
            Color::Red
        };

        queue!(
            self.stdout,
            MoveTo(x, 4),
            SetForegroundColor(Color::White),
            Print("HP ")
        )?;
        queue!(
            self.stdout,
            SetForegroundColor(hp_color),
            Print("█".repeat(filled))
        )?;
        queue!(
            self.stdout,
            SetForegroundColor(Color::DarkGrey),
            Print("░".repeat(hp_bar_len - filled))
        )?;
        queue!(
            self.stdout,
            SetForegroundColor(Color::White),
            Print(format!(" {}/{}", player.hp, player.max_hp))
        )?;

        // Stats
        let stats = vec![
            format!("⚔️  Attack : {}", player.attack),
            format!("🛡️  Defense: {}", player.defense),
            format!("⭐  Level : {} (XP: {}/{})", player.level, player.xp, player.xp_to_next),
            format!("💰  Gold  : {}", player.gold),
            format!("📅  Floor : {}/{}", floor, crate::map::MAX_FLOOR),
            format!("🕐  Turn  : {}", turn),
        ];

        for (i, stat) in stats.iter().enumerate() {
            queue!(
                self.stdout,
                MoveTo(x, 6 + i as u16),
                SetForegroundColor(Color::White),
                Print(stat)
            )?;
        }

        // Active buffs
        let mut buff_y = 13u16;
        if player.speed_turns > 0 {
            queue!(
                self.stdout,
                MoveTo(x, buff_y),
                SetForegroundColor(Color::Yellow),
                Print(format!("⚡ Speed: {} turns", player.speed_turns))
            )?;
            buff_y += 1;
        }

        // Controls
        queue!(
            self.stdout,
            MoveTo(x, buff_y),
            SetForegroundColor(Color::Cyan),
            Print("═══ Controls ═══")
        )?;
        let controls = vec![
            "WASD/Arrows: Move",
            "> / .      : Descend",
            "1-9        : Use item",
            "G          : Pick up",
            "Q / Esc    : Quit",
        ];
        for (i, c) in controls.iter().enumerate() {
            queue!(
                self.stdout,
                MoveTo(x, buff_y + 1 + i as u16),
                SetForegroundColor(Color::Grey),
                Print(c)
            )?;
        }

        // Inventory
        let inv_y = buff_y + 7;
        queue!(
            self.stdout,
            MoveTo(x, inv_y),
            SetForegroundColor(Color::Magenta),
            Print("═══ Inventory ═══")
        )?;

        if player.inventory.is_empty() {
            queue!(
                self.stdout,
                MoveTo(x, inv_y + 1),
                SetForegroundColor(Color::DarkGrey),
                Print("  (empty)")
            )?;
        } else {
            for (i, item) in player.inventory.iter().take(8).enumerate() {
                queue!(
                    self.stdout,
                    MoveTo(x, inv_y + 1 + i as u16),
                    SetForegroundColor(Color::White),
                    Print(format!("{}. {} {}", i + 1, item.emoji, item.name))
                )?;
            }
            if player.inventory.len() > 8 {
                queue!(
                    self.stdout,
                    MoveTo(x, inv_y + 9),
                    SetForegroundColor(Color::DarkGrey),
                    Print(format!("  +{} more...", player.inventory.len() - 8))
                )?;
            }
        }

        // Message log
        let msg_y = inv_y + 11;
        queue!(
            self.stdout,
            MoveTo(x, msg_y),
            SetForegroundColor(Color::Cyan),
            Print("═══ Log ═══")
        )?;

        let visible_msgs: Vec<_> = messages.iter().rev().take(8).collect();
        for (i, msg) in visible_msgs.iter().enumerate() {
            let truncated = if msg.len() > 28 {
                &msg[..28]
            } else {
                msg
            };
            queue!(
                self.stdout,
                MoveTo(x, msg_y + 1 + i as u16),
                SetForegroundColor(Color::Grey),
                Print(truncated)
            )?;
        }

        Ok(())
    }

    fn render_minimap(
        &mut self,
        map: &GameMap,
        player: &Player,
        enemies: &[Enemy],
    ) -> io::Result<()> {
        let ox = 2u16;
        let oy = (VIEWPORT_H + 1) as u16;

        queue!(
            self.stdout,
            MoveTo(ox, oy),
            SetForegroundColor(Color::Cyan),
            Print("── Mini Map ──")
        )?;

        for x in 0..crate::map::MAP_WIDTH {
            for y in 0..crate::map::MAP_HEIGHT {
                if !map.revealed[x][y] {
                    continue;
                }
                let tx = ox + x as u16;
                let ty = oy + 1 + y as u16 + 1;

                let ch = if x == player.x && y == player.y {
                    "@"
                } else if enemies.iter().any(|e| e.alive && e.x == x && e.y == y) {
                    "e"
                } else if map.tiles[x][y] == Tile::StairsDown {
                    ">"
                } else if map.tiles[x][y].is_floor_variant() || map.tiles[x][y] == Tile::Floor {
                    "."
                } else {
                    "#"
                };

                let color = if x == player.x && y == player.y {
                    Color::Yellow
                } else if map.visible[x][y] {
                    Color::Grey
                } else {
                    Color::DarkGrey
                };

                queue!(
                    self.stdout,
                    MoveTo(tx, ty),
                    SetForegroundColor(color),
                    Print(ch)
                )?;
            }
        }

        Ok(())
    }

    pub fn render_title_screen(&mut self) -> io::Result<()> {
        queue!(self.stdout, Clear(ClearType::All))?;

        let title = vec![
            "",
            "    ╔══════════════════════════════════════╗",
            "    ║     🏰  EMOJI  ROGUELIKE  🏰        ║",
            "    ╚══════════════════════════════════════╝",
            "",
            "    🧙 Descend through 7 unique biomes...",
            "    🏰🏰💎🌲❄️🌋🌿🪦",
            "    👹 Fight 28 unique emoji monsters...",
            "    💰 Collect 19 item types...",
            "    🔮 Find the Amulet of Yendor!",
            "",
            "    ─── Biomes ──────────────────────",
            "    🏰 Stone Dungeon   💎 Crystal Cavern",
            "    🌲 Enchanted Forest ❄️ Frozen Depths",
            "    🌋 Volcanic Core   🌿 Poison Swamp",
            "    🪦 Haunted Graveyard",
            "",
            "    ─── Controls ───────────────────",
            "    WASD / Arrow Keys : Move & Attack",
            "    > or .           : Descend stairs",
            "    1-9              : Use inventory item",
            "    G                : Grab nearby item",
            "    Q / Esc          : Quit",
            "",
            "    Press any key to begin! 🎮",
        ];

        for (i, line) in title.iter().enumerate() {
            queue!(
                self.stdout,
                MoveTo(3, 1 + i as u16),
                SetForegroundColor(Color::Magenta),
                Print(*line)
            )?;
        }

        self.stdout.flush()
    }

    pub fn render_death_screen(&mut self, player: &Player, floor: usize, turn: usize) -> io::Result<()> {
        queue!(self.stdout, Clear(ClearType::All))?;

        let lines: Vec<String> = vec![
            "".into(),
            "    ╔══════════════════════════════════════╗".into(),
            "    ║         💀  GAME  OVER  💀           ║".into(),
            "    ╚══════════════════════════════════════╝".into(),
            "".into(),
            format!("    🧙 Level {} Hero fell on floor {}", player.level, floor),
            format!("    ⚔️  Attack: {}   🛡️ Defense: {}", player.attack, player.defense),
            format!("    💰 Gold collected: {}", player.gold),
            format!("    🕐 Survived {} turns", turn),
            "".into(),
            "".into(),
            "    The dungeon claims another soul... 🪦".into(),
            "".into(),
            "    Press R to restart or Q to quit".into(),
        ];

        for (i, line) in lines.iter().enumerate() {
            queue!(
                self.stdout,
                MoveTo(5, 2 + i as u16),
                SetForegroundColor(Color::Red),
                Print(line as &str)
            )?;
        }

        self.stdout.flush()
    }

    pub fn render_win_screen(&mut self, player: &Player, floor: usize, turn: usize) -> io::Result<()> {
        queue!(self.stdout, Clear(ClearType::All))?;

        let lines: Vec<String> = vec![
            "".into(),
            "    ╔══════════════════════════════════════╗".into(),
            "    ║        🏆  YOU  WIN!  🏆             ║".into(),
            "    ╚══════════════════════════════════════╝".into(),
            "".into(),
            "    🔮 You found the Amulet of Yendor!".into(),
            "".into(),
            format!("    🧙 Level {} Hero conquered floor {}", player.level, floor),
            format!("    ⚔️  Attack: {}   🛡️ Defense: {}", player.attack, player.defense),
            format!("    💰 Gold collected: {}", player.gold),
            format!("    🕐 Completed in {} turns", turn),
            "".into(),
            "    🎉 You are a true roguelike champion! 🎉".into(),
            "".into(),
            "    Press R to play again or Q to quit".into(),
        ];

        for (i, line) in lines.iter().enumerate() {
            queue!(
                self.stdout,
                MoveTo(5, 2 + i as u16),
                SetForegroundColor(Color::Yellow),
                Print(line as &str)
            )?;
        }

        self.stdout.flush()
    }
}