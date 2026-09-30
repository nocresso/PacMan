import pygame
from pygame.surface import Surface
from .general_sprite_classes import CustomSprite, MovingSprite, Rect


class PacMan(MovingSprite):
    """
    Sprite class in charge of the display of the player's
    character.
    """

    def __init__(self, x: float, y: float,
                 scale: float = 1.0,
                 speed: float = 250,
                 cooldown: float = 0.08) -> None:
        super().__init__(x, y, scale, cooldown, speed)
        self.sprites: dict[str, list[Surface]] = self.image_load()
        self.row: str = 'right'
        self.current_frame: int = 1
        self.frame_dir: int = 1
        self.image: Surface = self.sprites[self.row][self.current_frame]
        self.collision_rect = Rect()
        self.get_image_rect()
        self.change_collision_rect()
        self.alive: bool = True
        self.moving_dir: str = ''
        self.wanted_dir: str = ''

    def image_load(self) -> dict[str, list[Surface]]:
        """
        Loads the images used for the display inside Pygame's
        Surface type object.

        Returns
        -------
        dict[str, list[Surface]]
            Dictionary of all available list of frames for different
            animations Pacman can display.
        """

        sheet_path = 'src_images/pacman_and_ghosts_v2.png'
        sprites: dict[str, list[Surface]] = {}
        sheet = pygame.image.load(sheet_path).convert_alpha()
        keys = ['right', 'left', 'up', 'down', 'death']
        origin = [(0, 15), (0, 30), (0, 45), (0, 60), (0, 140)]
        for k, ori in zip(keys, origin):
            sp_list: list[Surface] = []
            d_x = 15 if k != 'death' else 17
            d_y = 15 if k != 'death' else 16
            frames = 3 if k != 'death' else 11
            for i in range(frames):
                img = CustomSprite.get_img(sheet, ori, i, d_x, d_y, self.scale)
                sp_list.append(img)
            sprites[k] = sp_list
        return sprites

    def init_cell_position(self, x: int, y: int) -> None:
        """
        Sets the value of all the attributes related to the sprite's posiiton
        inside the maze grid.
        """
        self.current_cell = [x, y]
        center = self.screen_grid[y][x]
        self.pos = list(center)

    def calculate_cell(self, center: tuple[float, float]
                       ) -> list[float]:
        """
        Calculates the size of the cells of the grid, given the cells' central
        coordinates.
        """
        reach = self.cell_size // 2
        lower_x = center[0] - reach
        upper_x = center[0] + reach
        lower_y = center[1] - reach
        upper_y = center[1] + reach
        return [lower_x, upper_x, lower_y, upper_y]

    def center_in_boundaries(self, center: tuple[float, float],
                             pos: list[float]) -> bool:
        """
        Determines if the sprite's central coordinates are inside a
        given cell.
        """
        l_x, u_x, l_y, u_y = self.calculate_cell(center)
        return l_x <= pos[0] <= u_x and l_y <= pos[1] <= u_y

    def update_current_cell(self) -> None:
        """
        Determines the sprites position inside the maze grid based on its
        position inside the screen.
        """
        x, y = self.current_cell
        dirs = {'up': (0, -1),
                'right': (1, 0),
                'down': (0, 1),
                'left': (-1, 0)}

        for dx, dy in dirs.values():
            if x + dx < 0 or x + dx >= len(self.screen_grid[0]):
                continue
            if y + dy < 0 or y + dy >= len(self.screen_grid):
                continue
            center = self.screen_grid[y + dy][x + dx]
            if self.center_in_boundaries(center, self.pos):
                self.current_cell[0] += dx
                self.current_cell[1] += dy
                break

    def change_collision_rect(self) -> None:
        """
        Modifies the dimensions of the collision Rect making it
        smaller than the image's Rect.
        """
        self.collision_rect.x = self.pos[0] - self.rect.w / 4
        self.collision_rect.y = self.pos[1] - self.rect.h / 4
        self.collision_rect.w = self.rect.w / 2
        self.collision_rect.h = self.rect.h / 2

    def request_direction(self, direction: str) -> None:
        """
        Stores the direction the player wants to go next. It will be
        applied as soon as Pacman reaches a point where it is possible.
        """
        if not self.alive:
            return
        self.wanted_dir = direction

    def release_all(self) -> None:
        """
        Forgets the wanted direction (pause, death...). The direction
        Pacman is actually moving in is untouched (arcade style).
        """
        self.wanted_dir = ''

    def choose_move(self) -> tuple[str, float, bool] | None:
        """
        Decides what Pacman should do next: which direction to move,
        how many pixels it can travel before it needs to check again,
        and whether that movement takes it exactly to the center of
        the cell. Returns None if Pacman should not move.
        """
        center_x, center_y = self.get_current_center()
        offset_x = self.pos[0] - center_x
        offset_y = self.pos[1] - center_y

        if offset_x == 0 and offset_y == 0:
            self.pos = [center_x, center_y]
            if self.wanted_dir and self.can_it_move(self.wanted_dir):
                return self.wanted_dir, float(self.cell_size), False
            if self.moving_dir and self.can_it_move(self.moving_dir):
                return self.moving_dir, float(self.cell_size), False
            return None

        tolerance = self.cell_size // 5

        if offset_y == 0:
            if (self.wanted_dir == 'up' and self.can_it_move('up')
                    and abs(offset_x) <= tolerance):
                self.pos = [center_x, center_y]
                return '', 0.0, False
            if (self.wanted_dir == 'down' and self.can_it_move('down')
                    and abs(offset_x) <= tolerance):
                self.pos = [center_x, center_y]
                return '', 0.0, False

            if self.moving_dir == 'right' or self.moving_dir == 'left':
                key = self.moving_dir
            elif self.wanted_dir and self.can_it_move(self.wanted_dir):
                key = 'left' if offset_x > 0 else 'right'
            else:
                return None

            if key == 'right':
                if offset_x < 0:
                    return 'right', -offset_x, True
                if not self.can_it_move('right'):
                    return None
                return 'right', self.cell_size - offset_x, False
            else:
                if offset_x > 0:
                    return 'left', offset_x, True
                if not self.can_it_move('left'):
                    return None
                return 'left', self.cell_size + offset_x, False

        else:
            if (self.wanted_dir == 'left' and self.can_it_move('left')
                    and abs(offset_y) <= tolerance):
                self.pos = [center_x, center_y]
                return '', 0.0, False
            if (self.wanted_dir == 'right' and self.can_it_move('right')
                    and abs(offset_y) <= tolerance):
                self.pos = [center_x, center_y]
                return '', 0.0, False

            if self.moving_dir == 'up' or self.moving_dir == 'down':
                key = self.moving_dir
            elif self.wanted_dir and self.can_it_move(self.wanted_dir):
                key = 'up' if offset_y > 0 else 'down'
            else:
                return None

            if key == 'down':
                if offset_y < 0:
                    return 'down', -offset_y, True
                if not self.can_it_move('down'):
                    return None
                return 'down', self.cell_size - offset_y, False
            else:
                if offset_y > 0:
                    return 'up', offset_y, True
                if not self.can_it_move('up'):
                    return None
                return 'up', self.cell_size + offset_y, False

    def advance(self, key: str, step: float, arrive: bool) -> None:
        """
        Moves Pacman 'step' pixels in 'key' direction (or exactly to
        the center of the cell if 'arrive').
        """
        center_x, center_y = self.get_current_center()
        if key == 'right':
            self.pos[0] = center_x if arrive else self.pos[0] + step
        elif key == 'left':
            self.pos[0] = center_x if arrive else self.pos[0] - step
        elif key == 'down':
            self.pos[1] = center_y if arrive else self.pos[1] + step
        elif key == 'up':
            self.pos[1] = center_y if arrive else self.pos[1] - step

    def move_rect(self, dt: float) -> None:
        """
        Pacman keeps moving on its own and only
        stops when it meets a wall.
        """
        distance = self.speed * dt
        moved = ''
        for _ in range(6):
            self.update_current_cell()
            action = self.choose_move()
            if action is None:
                break
            key, limit, to_center = action
            if not key:
                continue
            if distance <= 0:
                break
            step = min(distance, limit)
            self.advance(key, step, to_center and step >= limit)
            distance -= step
            moved = key
        self.moving_dir = moved
        if moved:
            self.change_direction(moved)
        elif self.its_moving():
            self.stop_movement()
        self.get_image_rect()
        self.change_collision_rect()

    def change_direction(self, key: str) -> None:
        """
        Sets the movement flags and the animation row to the given
        direction. Ignored if PacMan is dead.
        """
        if not self.alive:
            return
        super().change_direction(key)
        self.row = key

    def stop_movement(self) -> None:
        """
        Stops movements in all directions.
        """
        if not self.alive:
            return
        super().stop_movement()
        self.current_frame = 1
        self.image = self.sprites[self.row][self.current_frame]

    def die(self) -> None:
        """
        Triggers the death animation.
        """
        dirs = ['right', 'left', 'up', 'down']
        for dir in dirs:
            setattr(self, f'moving_{dir}', False)
        self.row = 'death'
        self.current_frame = 0
        self.image = self.sprites[self.row][self.current_frame]
        self.get_image_rect()
        self.alive = False
        self.moving_dir = ''
        self.release_all()

    def revive(self, cell_x: int, cell_y: int) -> None:
        """
        Restores Pacman to a normal, movable state after losing a life
        and respawns him to the center.
        """
        dirs = ['right', 'left', 'up', 'down']
        for dir in dirs:
            setattr(self, f'moving_{dir}', False)
        self.row = 'right'
        self.current_frame = 1
        self.frame_dir = 1
        self.image = self.sprites[self.row][self.current_frame]
        self.alive = True
        self.moving_dir = ''
        self.release_all()
        self.init_cell_position(cell_x, cell_y)

    def update(self, dt: float = 0) -> None:
        self.animation_timer += dt
        if self.its_moving() and self.alive:
            if self.animation_timer >= self.cooldown:
                self.animation_timer -= self.cooldown
                self.current_frame += self.frame_dir
                self.image = self.sprites[self.row][self.current_frame]
                if (
                    self.current_frame == len(self.sprites[self.row]) - 1 or
                    self.current_frame == 0
                ):
                    self.frame_dir *= -1
        elif (
            not self.alive and
            self.animation_timer >= self.cooldown
        ):
            self.animation_timer -= self.cooldown
            self.current_frame = self.current_frame + 1
            if self.current_frame >= len(self.sprites[self.row]):
                self.kill()
                return
            self.image = self.sprites[self.row][self.current_frame]

        if self.alive:
            self.move_rect(dt)
            self.update_current_cell()
