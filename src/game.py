import pygame
import time
import math
from src.parser import GameConfiguration
from src.states import GameState
from src.maze_loader import build_level_maze
from typing import Optional
from sprites import (spawn_pellets, spawn_megapellets,
                     PacMan, SpriteGroup, PelletGroup,
                     MegaPelletGroup, GhostGroup, init_ghosts)
from src.screens import (MainMenu, PauseMenu,
                         InputScreen, VictoryScreen, GameOverScreen,
                         InstructionsScreen, HighscoreScreen,
                         load_pixel_font)

DIRECTION_KEYS = {pygame.K_LEFT: 'left', pygame.K_RIGHT: 'right',
                  pygame.K_UP: 'up', pygame.K_DOWN: 'down',
                  pygame.K_a: 'left', pygame.K_w: 'up',
                  pygame.K_s: 'down', pygame.K_d: 'right'}

MIN_CELL_SIZE = 24
MAX_CELL_SIZE = 80
BASE_CELL_SIZE = 80
BASE_SPRITE_SCALE = 3.0
BASE_PACMAN_SPEED = 250.0
BASE_GHOST_SPEED = 150.0
HUD_TO_CELL_RATIO = 130 / BASE_CELL_SIZE
WALL_CORE_COLOR = (70, 160, 255)
WALL_GLOW_COLOR = (40, 110, 255)


class Game:
    """
    Main class of the game. Owns the window, the game state, the
    sprites and the game loop.

    Parameters
    ----------
    config: GameConfiguration
        Validated game configuration.
    """
    def __init__(self, config: GameConfiguration):
        pygame.init()
        self.config = config
        self.state = GameState.MENU
        self.current_level = 1
        self.lives = config.lives
        self.score = 0
        self.time_left = float(config.level_max_time)
        self.pacgums_nb = config.pacgums
        self.grid: list[list[int]] = []

        self.wall_color = WALL_CORE_COLOR
        self.menu = MainMenu()
        self.pause_menu = PauseMenu()
        self.highscores = HighscoreScreen(config.highscore_filename)
        self.instructions = InstructionsScreen()
        self.active_input_screen: Optional[InputScreen] = None
        self.running = True
        self.clock = pygame.time.Clock()
        self.offset_y = 40
        self.max_screen_width, self.max_screen_height = (
            self.get_display_bounds())
        self.cell_size = BASE_CELL_SIZE
        self.margin = self.cell_size
        self.hud_main_height = round(self.cell_size * HUD_TO_CELL_RATIO)
        self.cheat_line_height = 0
        self.hud_height = self.hud_main_height
        self.sprite_scale = BASE_SPRITE_SCALE
        self.pacman_speed = BASE_PACMAN_SPEED
        self.ghost_speed = BASE_GHOST_SPEED
        self.screen_width, self.screen_height = self.initial_window_size()
        self.screen = pygame.display.set_mode(
            (self.screen_width, self.screen_height + self.hud_height))
        self.megapellets: MegaPelletGroup
        self.pellets: PelletGroup
        self.screen_grid: list[list[tuple[float, float]]]
        self.pacman: PacMan
        self.ghosts: GhostGroup
        self.previous_time: float
        self.current_time: float
        self.all_sprites = SpriteGroup()
        self.hud_font = load_pixel_font(20)
        self.cheat_font = load_pixel_font(14)
        self.wall_glow_surface = pygame.Surface((1, 1), pygame.SRCALPHA)
        self.cheat: bool = False
        self.cheat_invincible: bool = False
        self.pacman_base_speed: float = 400

    @staticmethod
    def get_display_bounds() -> tuple[int, int]:
        """
        Determines how much screen space is safe to use on the
        current computer, leaving room for the taskbar/window chrome.
        """
        try:
            desktop_w, desktop_h = pygame.display.get_desktop_sizes()[0]
        except (pygame.error, IndexError):
            desktop_w, desktop_h = 1600, 900
        return int(desktop_w * 0.95), int(desktop_h * 0.85)

    def initial_window_size(self) -> tuple[int, int]:
        """
        Computes the menu window size, scaled down to fit the current
        display when the default size would be too large for it.
        """
        default_width, default_height = 1600, 1300
        available_height = self.max_screen_height - self.hud_height
        scale = min(1.0, self.max_screen_width / default_width,
                    available_height / default_height)
        return (round(default_width * scale), round(default_height * scale))

    def compute_cell_size(self, grid_width: int, grid_height: int) -> int:
        """
        Picks the largest cell size that still lets the maze, its
        margins and the HUD fit within the available screen space.
        """
        width_limit = self.max_screen_width / (grid_width + 2)
        height_limit = self.max_screen_height / (
            grid_height + 2 + HUD_TO_CELL_RATIO)
        cell_size = min(MAX_CELL_SIZE, width_limit, height_limit)
        return max(MIN_CELL_SIZE, int(cell_size))

    def resize_screen(self) -> None:
        """
        Adapts screen size to the current maze and to the available
        screen space of the computer running the game.
        """
        level_maze = build_level_maze(self.config, self.current_level - 1)
        self.grid = level_maze.grid
        self.cell_size = self.compute_cell_size(
            len(self.grid[0]), len(self.grid))
        self.margin = self.cell_size
        self.hud_main_height = round(self.cell_size * HUD_TO_CELL_RATIO)
        speed_scale = self.cell_size / BASE_CELL_SIZE
        self.sprite_scale = BASE_SPRITE_SCALE * speed_scale
        self.pacman_speed = BASE_PACMAN_SPEED * speed_scale
        self.ghost_speed = BASE_GHOST_SPEED * speed_scale
        maze_pixel_width = len(self.grid[0]) * self.cell_size
        maze_pixel_height = len(self.grid) * self.cell_size
        self.screen_width = maze_pixel_width + self.margin * 2
        self.screen_height = maze_pixel_height + self.margin * 2
        cheat_font_size = self.cheat_font_size()
        self.cheat_font = load_pixel_font(cheat_font_size)
        self.cheat_line_height = round(cheat_font_size * 1.5)
        self.hud_height = self.hud_main_height + self.cheat_line_height
        self.screen = pygame.display.set_mode(
            (self.screen_width, self.screen_height + self.hud_height))
        self.hud_font = load_pixel_font(self.hud_font_size())

    def hud_font_size(self) -> int:
        """
        Computes the HUD font size so the text fits the screen width,
        shrinking further if needed for very small windows.
        """
        sample_text = "LEVEL 10  LIVES 3  SCORE 999999  TIME 00:00"
        size = min(48, max(14, self.screen_width // 22))
        while size > 10:
            if load_pixel_font(size).size(
                    sample_text)[0] <= self.screen_width - 20:
                break
            size -= 2
        return size

    def cheat_font_size(self) -> int:
        """
        Computes the cheat legend font size so it fits in a single
        line within the screen width, staying noticeably smaller
        than the main HUD text.
        """
        sample_text = "CHEAT  L:SKIP  I:INVINCIBLE  X:+LIFE  Z:SPEED"
        size = min(18, max(6, self.screen_width // 45))
        while size > 6:
            if load_pixel_font(size).size(
                    sample_text)[0] <= self.screen_width - 20:
                break
            size -= 1
        max_relative = max(6, round(self.hud_font_size() * 0.72))
        return min(size, max_relative)

    def load_level(self) -> None:
        """
        Generates the maze for the current level and precomputes where
        it should be drawn so it appears centered on screen.
        """
        self.resize_screen()
        self.offset_y = self.hud_height + self.margin
        self.screen_grid = self.screen_gridder()
        self.forbidden_cells()
        self.time_left = float(self.config.level_max_time)
        self.wall_glow_surface = self.build_wall_glow()

    def wall_width(self) -> int:
        """
        Scales the wall stroke thickness together with the cell size.
        """
        return max(2, round(self.cell_size * 0.0625))

    def wall_segments(self) -> list[tuple[tuple[float, float],
                                          tuple[float, float]]]:
        """
        Computes the on-screen endpoints of every wall segment in the
        current maze.
        """
        segments: list[tuple[tuple[float, float],
                             tuple[float, float]]] = []
        for y, row in enumerate(self.grid):
            for x, val in enumerate(row):
                top_left = (self.margin + x * self.cell_size,
                            self.offset_y + y * self.cell_size)
                top_right = (self.margin + (x + 1) * self.cell_size,
                             self.offset_y + y * self.cell_size)
                bottom_left = (self.margin + x * self.cell_size,
                               self.offset_y + (y + 1) * self.cell_size)
                bottom_right = (self.margin + (x + 1) * self.cell_size,
                                self.offset_y + (y + 1) * self.cell_size)
                if val & 1:
                    segments.append((top_left, top_right))
                if val & 2:
                    segments.append((top_right, bottom_right))
                if val & 4:
                    segments.append((bottom_left, bottom_right))
                if val & 8:
                    segments.append((top_left, bottom_left))
        return segments

    def build_wall_glow(self) -> pygame.Surface:
        """
        Pre-renders a soft neon halo behind the maze walls onto a
        transparent surface, blitted once per frame under the crisp
        wall lines for a cheap glow effect.
        """
        glow = pygame.Surface(
            (self.screen_width, self.screen_height + self.hud_height),
            pygame.SRCALPHA)
        base_width = self.wall_width()
        passes = ((base_width + 10, 20), (base_width + 6, 40),
                  (base_width + 2, 80))
        segments = self.wall_segments()
        for extra_width, alpha in passes:
            color = (*WALL_GLOW_COLOR, alpha)
            radius = extra_width // 2
            for p1, p2 in segments:
                pygame.draw.line(glow, color, p1, p2, extra_width)
                pygame.draw.circle(glow, color, p1, radius)
                pygame.draw.circle(glow, color, p2, radius)
        return glow

    def draw_maze(self) -> None:
        """
        Draws the maze walls onto the given pygame surface, with
        rounded joints so segments meet cleanly.
        """
        width = self.wall_width()
        radius = width // 2
        for p1, p2 in self.wall_segments():
            pygame.draw.line(self.screen, self.wall_color, p1, p2, width)
            pygame.draw.circle(self.screen, self.wall_color, p1, radius)
            pygame.draw.circle(self.screen, self.wall_color, p2, radius)

    def screen_gridder(self) -> list[list[tuple[float, float]]]:
        """
        Computes the on-screen center coordinates of every maze cell.
        """
        screen_grid = []
        width = len(self.grid[0])
        height = len(self.grid)
        for y in range(height):
            row = []
            c_y = self.offset_y + self.cell_size * y + self.cell_size / 2
            for x in range(width):
                c_x = self.margin + self.cell_size * x + self.cell_size / 2
                row.append((c_x, c_y))
            screen_grid.append(row)

        return screen_grid

    def forbidden_cells(self) -> None:
        """
        Computes the cells that form the '42' pattern in the center of
        the maze (four_coord and two_coord) and PacMan's starting
        cell (pac_house).
        """
        grid = self.grid
        width = len(grid[0])
        height = len(grid)
        xy_4 = [((width - 7) // 2, (height - 5) // 2)]
        self.pac_house = (xy_4[0][0] + 3, xy_4[0][1] + 2)
        xy_2 = [(xy_4[0][0] + 4, xy_4[0][1])]
        dir4 = [(0, 1), (0, 1), (1, 0), (1, 0), (0, 1), (0, 1)]
        dir2 = [(1, 0), (1, 0), (0, 1), (0, 1), (-1, 0), (-1, 0),
                (0, 1), (0, 1), (1, 0), (1, 0)]
        for init, dirs in zip([xy_4, xy_2], [dir4, dir2]):
            x, y = init[0]
            for dir in dirs:
                x, y = x + dir[0], y + dir[1]
                init.append((x, y))
        self.four_coord = xy_4
        self.two_coord = xy_2

    def draw_hud(self) -> None:
        """
        Render the in-game HUD information.
        """
        total_seconds = math.ceil(self.time_left)
        time_minutes = total_seconds // 60
        time_seconds = total_seconds % 60

        hud_text = (f"LEVEL {self.current_level}  "
                    f"LIVES {self.lives}  "
                    f"SCORE {self.score}  "
                    f"TIME {time_minutes:02d}:{time_seconds:02d}")

        text_surface = self.hud_font.render(hud_text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(
            center=(self.screen_width // 2, self.hud_main_height // 2))
        text_rect.x = max(0, min(text_rect.x,
                                 self.screen_width - text_rect.width))
        self.screen.blit(text_surface, text_rect)

    def draw_cheat_legend(self) -> None:
        """
        Draws a compact, one-line cheat key legend in the reserved
        strip below the main HUD, above the maze, when cheat mode
        is active.
        """
        if not self.cheat:
            return
        legend = "CHEAT  L:SKIP  I:INVINCIBLE  X:+LIFE  Z:SPEED"
        surf = self.cheat_font.render(legend, True, (255, 255, 0))
        legend_y = self.hud_main_height + self.cheat_line_height // 2
        rect = surf.get_rect(
            center=(self.screen_width // 2, legend_y))
        rect.x = max(0, min(rect.x, self.screen_width - rect.width))
        self.screen.blit(surf, rect)

    def begin_sprites(self) -> None:
        """
        Creates the pellets, PacMan and the ghosts of the current level
        and gives them the maze information.
        """
        self.all_sprites.clear()
        self.pellets = spawn_pellets(self.grid, self.screen_grid,
                                     self.pacgums_nb, self.sprite_scale)
        self.megapellets = spawn_megapellets(
            self.grid, self.screen_grid, self.sprite_scale)
        self.all_sprites.extend(self.megapellets)
        self.all_sprites.extend(self.pellets)
        self.pacman = PacMan(0, 0, self.sprite_scale,
                             speed=self.pacman_speed)
        self.pacman_base_speed = self.pacman.speed
        self.ghosts = init_ghosts(self.screen_grid, self.sprite_scale,
                                  self.ghost_speed)
        self.ghosts.get_forbidden(self.four_coord)
        self.ghosts.get_forbidden(self.two_coord)
        self.all_sprites.add(self.pacman)
        self.all_sprites.extend(self.ghosts)
        self.all_sprites.update_grid_screen(self.grid, self.screen_grid)
        self.pacman.init_cell_position(*self.pac_house)

    def reset_game(self) -> None:
        """
        Resets score, lives and cheats, and starts again at level 1.
        """
        self.cheat = False
        self.cheat_invincible = False
        self.current_level = 1
        self.score = 0
        self.lives = self.config.lives
        self.load_level()
        self.begin_sprites()

    def run(self) -> None:
        """
        Main game loop: reads events, updates game state, and draws
        the screen that corresponds to the current state.
        """
        self.previous_time = time.monotonic()

        while self.running:

            self.current_time = time.monotonic()
            dt = self.current_time - self.previous_time
            self.previous_time = self.current_time
            dt = min(dt, 0.05)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                elif self.state == GameState.MENU:
                    choice = self.menu.handle_events(event)
                    if choice == "START GAME":
                        self.reset_game()
                        self.state = GameState.PLAYING
                    elif choice == "VIEW HIGHSCORES":
                        self.highscores.load_scores()
                        self.state = GameState.HIGHSCORES
                    elif choice == "INSTRUCTIONS":
                        self.state = GameState.INSTRUCTIONS
                    elif choice == "EXIT":
                        self.running = False

                elif self.state == GameState.PLAYING:
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            self.state = GameState.PAUSED
                        elif event.key in DIRECTION_KEYS:
                            self.pacman.request_direction(
                                DIRECTION_KEYS[event.key])

                        elif event.key == pygame.K_c:
                            self.cheat = not self.cheat
                            if not self.cheat:
                                self.cheat_invincible = False
                                self.pacman.speed = self.pacman_base_speed
                        if self.cheat is True and event.key == pygame.K_l:
                            if self.current_level < self.config.level_nb:
                                self.current_level += 1
                                self.load_level()
                                self.begin_sprites()
                            elif self.current_level == self.config.level_nb:
                                self.active_input_screen = VictoryScreen(
                                    self.score, self.config.highscore_filename)
                                self.state = GameState.VICTORY
                        elif self.cheat is True and event.key == pygame.K_x:
                            self.lives += 1
                        elif self.cheat is True and event.key == pygame.K_i:
                            self.cheat_invincible = not self.cheat_invincible
                        elif self.cheat is True and event.key == pygame.K_z:
                            if self.pacman.speed == self.pacman_base_speed:
                                self.pacman.speed *= 2
                            else:
                                self.pacman.speed = self.pacman_base_speed

                elif self.state == GameState.PAUSED:
                    choice = self.pause_menu.handle_events(event)
                    if choice == "RESUME THE GAME":
                        self.state = GameState.PLAYING
                    elif choice == "RETURN TO THE MAIN MENU":
                        self.state = GameState.MENU

                elif self.state in (GameState.GAME_OVER, GameState.VICTORY):
                    assert self.active_input_screen is not None
                    name = self.active_input_screen.handle_events(event)
                    if name is not None:
                        self.active_input_screen = None
                        self.state = GameState.MENU

                elif self.state in (GameState.HIGHSCORES,
                                    GameState.INSTRUCTIONS):
                    if self.state == GameState.HIGHSCORES:
                        choice = self.highscores.handle_events(event)
                    else:
                        choice = self.instructions.handle_events(event)
                    if choice == "MAIN MENU":
                        self.state = GameState.MENU
            # DRAW
            if self.state == GameState.MENU:
                self.menu.draw(self.screen)
            elif self.state == GameState.PLAYING:
                if self.lives == 0:
                    self.active_input_screen = GameOverScreen(
                        self.score, self.config.highscore_filename)
                    self.state = GameState.GAME_OVER
                if (
                    not self.megapellets.sprites and not self.pellets.sprites
                ):
                    if self.current_level < self.config.level_nb:
                        self.current_level += 1
                        self.load_level()
                        self.begin_sprites()
                    elif self.current_level == self.config.level_nb:
                        self.active_input_screen = VictoryScreen(
                            self.score, self.config.highscore_filename)
                        self.state = GameState.VICTORY
                self.time_left = max(0, self.time_left - dt)
                self.screen.fill((0, 0, 0))
                glow_alpha = 165 + int(70 * math.sin(self.current_time * 2.4))
                self.wall_glow_surface.set_alpha(
                    max(0, min(255, glow_alpha)))
                self.screen.blit(self.wall_glow_surface, (0, 0))
                self.draw_maze()
                self.score += self.pellets.death_on_collision(
                    self.pacman, self.config.points_per_pacgum)
                self.score += self.megapellets.trigger_fright(
                    self.pacman, self.ghosts,
                    self.config.points_per_super_pacgum)
                if self.pacman.alive:
                    self.score += self.ghosts.check_collision(
                        self.pacman,
                        self.config.points_per_ghost,
                        self.cheat_invincible)
                if self.time_left == 0 or (
                    not self.pacman.alive and
                    self.pacman.current_frame >= len(
                        self.pacman.sprites['death'])
                ):
                    self.lives -= 1
                    if self.time_left == 0:
                        self.time_left = float(self.config.level_max_time)
                    for ghost in self.ghosts.sprites.copy():
                        ghost.kill()
                    self.ghosts = init_ghosts(
                        self.screen_grid, self.sprite_scale,
                        self.ghost_speed)
                    self.all_sprites.extend(self.ghosts)
                    self.all_sprites.update_grid_screen(
                        self.grid, self.screen_grid)
                    self.pacman.revive(*self.pac_house)
                    if self.pacman not in self.all_sprites.sprites:
                        self.all_sprites.add(self.pacman)

                pacx, pacy = self.pacman.current_cell
                self.ghosts.update_pacman_coords((pacx, pacy))
                self.ghosts.move(dt)
                self.all_sprites.update(dt)
                self.all_sprites.draw(self.screen)
                self.draw_hud()
                self.draw_cheat_legend()
            elif self.state == GameState.PAUSED:
                self.pause_menu.draw(self.screen)
            elif self.state in (GameState.GAME_OVER, GameState.VICTORY):
                assert self.active_input_screen is not None
                self.active_input_screen.draw(self.screen)
            elif self.state == GameState.HIGHSCORES:
                self.highscores.draw(self.screen)
            elif self.state == GameState.INSTRUCTIONS:
                self.instructions.draw(self.screen)

            pygame.display.flip()
            self.clock.tick(60)
