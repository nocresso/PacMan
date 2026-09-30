import pygame
import random
from collections import deque
from pygame.surface import Surface
from .general_sprite_classes import CustomSprite, MovingSprite


class Ghost(MovingSprite):
    """
    Sprite class in charge of the display and movement of the ghosts' sprites

    Parameters
    ----------
    x: float
        Sprite's position in the screen's x axis. Stored in a Rect object.
    y: float
        Sprite's position in the screen's x axis. Stored in a Rect object.
    scale: float
        Value used to scale the sprite's size.
    gh_type: int
        Type of ghost sprite to be displayed. Ranges from 0 to 3.
    cooldown: float
        Animation cooldown value.
    speed: float
        Determines the speed of the in-screen movement of the sprite.

    Attributes
    ----------
    To see general attributes check the parent class MovingSprite

    gh_type
        Type of ghost sprite, ranges from 0 to 3.
    sprites
        Dictionary of all available list of frames for different
        animations a ghost can display.
    row
        Dictionary key of the current list of frames being used
        for the animation.
    current_frame
        Current number of animation frame being displayed.
    dirchange_time
        Counter of direction change time for random movement
    frightened
        Indicates if the ghost is in frightened mode.
    fright_time
        Counts the time that has passed since the frightened mode started.
    eaten
        Indicates if the ghost is in eaten mode.
    home_cell
        Coordinates of the home cell. The ghost is first displayed in this
        cell and returns to it when eaten mode is triggered.
    forbidden_cells
        Cells inside the grid that can't be considered as possible targets
    moves_to_target
        List of moves (i.e. 'up', 'down', 'left' or 'right) needed to
        reach a target.
    coords_to_target
        List of screen coordinates of the centers of each cell in the path
        to the target.
    target
        X and Y indexes of the target's position inside the grid.
    pacman_cell
        X and Y position of the PacMan sprite inside the grid.
    chasing_random
        Indicates if a random position inside the grid is being used as a
        target.
    chasing_pacman
        Indicates if the PacMan sprite is being targeted.
    behavior_timer
        Counts the time passed to control the change of the ghost sprite
        behavior.
    """

    def __init__(self, x: float, y: float,
                 scale: float = 1.0,
                 gh_type: int = 0,
                 cooldown: float = 0.09,
                 speed: float = 150) -> None:
        super().__init__(x, y, scale, cooldown, speed)
        self.gh_type: int = gh_type
        self.sprites: dict[str, list[Surface]] = self.image_load()
        self.row: str = 'up'
        self.current_frame: int = 0
        self.dirchange_time: float = 0
        self.image: Surface = self.sprites[self.row][self.current_frame]
        self.get_image_rect()
        self.frightened: bool = False
        self.fright_time: float = 0
        self.eaten: bool = False
        self.home: CustomSprite
        self.home_cell: tuple[int, int]
        self.forbidden_cells: list[tuple[int, int]] = []
        self.moves_to_target: list[str]
        self.coords_to_target: list[tuple[int, int]]
        self.target: tuple[float, float] | None = None
        self.pacman_cell: tuple[int, int] | None = None
        self.chasing_random: bool = False
        self.chasing_pacman: bool = False
        self.behavior_timer: float = 0
        self.fright_reassess_timer: float = 0

    def image_load(self) -> dict[str, list[Surface]]:
        """
        Loads the images used for the display inside Pygame's
        Surface type object.

        Returns
        -------
        dict[str, list[Surface]]
            Dictionary of all available list of frames for different
            animations a ghost can display.
        """

        def move_ori(gh_type: int, ori: tuple[int, int]) -> tuple[int, int]:
            x, y = ori
            ny = y + (gh_type * 16)
            return x, ny

        sheet_path = 'src_images/pacman_and_ghosts_v2.png'
        sprites: dict[str, list[Surface]] = {}
        sheet = pygame.image.load(sheet_path).convert_alpha()
        keys = ['right', 'left', 'up', 'down',
                'eyes_right', 'eyes_left', 'eyes_up', 'eyes_down',
                'frightened']
        origin = [(0, 76), (32, 76), (64, 76), (96, 76),
                  (128, 92), (144, 92), (160, 92), (176, 92), (128, 76)]
        for k, ori in zip(keys, origin):
            sp_list: list[Surface] = []
            if 'eyes' in k:
                frames = 1
            else:
                frames = 2 if k != 'frightened' else 4
            if k in keys[:4]:
                n_ori = move_ori(self.gh_type, ori)
            else:
                n_ori = ori
            for i in range(frames):
                img = CustomSprite.get_img(sheet, n_ori, i, 16, 16, self.scale)
                sp_list.append(img)
            sprites[k] = sp_list
        return sprites

    def _row_from_movement(self,
                           movements: tuple[tuple[str, str], ...]) -> None:
        """
        Sets 'row' to the value paired with the first movement
        attribute that is True.
        """
        for attr, value in movements:
            if getattr(self, attr):
                self.row = value
                break

    def _change_direction_row(self) -> None:
        """
        Sets the normal animation row matching the current movement.
        """
        movements = (('moving_up', 'up'),
                     ('moving_down', 'down'),
                     ('moving_left', 'left'),
                     ('moving_right', 'right'))

        self._row_from_movement(movements)

    def _change_eyes_row(self) -> None:
        """
        Sets the 'eyes' animation row matching the current movement.
        """
        movements = (('moving_up', 'eyes_up'),
                     ('moving_down', 'eyes_down'),
                     ('moving_left', 'eyes_left'),
                     ('moving_right', 'eyes_right'))

        self._row_from_movement(movements)

    def change_direction(self, key: str) -> None:
        """
        Changes the attributes that indicate the movement direction
        for the update method, as well as the set of sprites used
        for the animation.

        Paremeters
        ----------
        key: str
            The direction ('up', 'down', 'left' or 'right') that will be set
            to True.
        """
        if getattr(self, f'moving_{key}'):
            return
        super().change_direction(key)
        if not self.frightened and not self.eaten:
            self.row = key
        elif self.eaten:
            self._change_eyes_row()

    def get_forbidden(self, cells: list[tuple[int, int]]) -> None:
        """
        Stores a list of forbidden cells to be ignored by the BFS algorithm
        and other path-seeking related methods.

        Parameters
        ----------
        cells: list[tuple[int, int]]
            List of forbidden cells.
        """
        self.forbidden_cells.extend(cells)

    def update_pacman_coords(self, pacman_cell: tuple[int, int]) -> None:
        """
        Updates the PacMan sprites coordinates information used
        in the chasing mode.

        Parameters
        ----------
        pacman_cell: tuple[int, int]
            Pair of x and y indexes indicating the position
            of PacMan in the maze grid.
        """
        self.pacman_cell = pacman_cell

    def get_target_coord(self, target: tuple[float,
                                             float]) -> tuple[float, float]:
        """
        Retrieves the screen coordinates of the center of a given cell.

        Parameters
        ----------
        target: tuple[float, float]
            Pair of x and y indexes of any cell of the maze grid.
        """
        grid_x, grid_y = target
        return self.screen_grid[int(grid_y)][int(grid_x)]

    def rect_update_not_free(self, dx: float, dy: float) -> None:
        """
        Updates the stored Rect attributes based on its position modifications.
        Sets movement limitations based on the sprite's current position
        inside the maze.

        Parameters
        ----------
        dx: float
            Potential modification of the Rect's x position on-screen.
        dy: float
            Potential modification of the Rect's y position on-screen.
        """

        new_pos0 = self.pos[0] + dx
        new_pos1 = self.pos[1] + dy
        tolerance = self.cell_size // 5

        center = self.get_current_center()
        pointing = False

        if self.target:
            pointing = True
            tx, ty = self.get_target_coord(self.target)

        if self.moving_left:
            if not self.can_it_move('left'):
                if new_pos0 < center[0]:
                    self.pos[0] = center[0]
                    dx = 0
            elif self.pos[1] != center[1]:
                if abs(self.pos[1] - center[1]) <= tolerance:
                    self.pos[1] = center[1]
                else:
                    dx = 0
            elif pointing and new_pos0 <= tx:
                self.pos[0] = center[0]
                dx = 0

        elif self.moving_right:
            if not self.can_it_move('right'):
                if new_pos0 > center[0]:
                    self.pos[0] = center[0]
                    dx = 0
            elif self.pos[1] != center[1]:
                if abs(self.pos[1] - center[1]) <= tolerance:
                    self.pos[1] = center[1]
                else:
                    dx = 0
            elif pointing and new_pos0 >= tx:
                self.pos[0] = center[0]
                dx = 0

        elif self.moving_up:
            if not self.can_it_move('up'):
                if new_pos1 < center[1]:
                    self.pos[1] = center[1]
                    dy = 0
            elif self.pos[0] != center[0]:
                if abs(self.pos[0] - center[0]) <= tolerance:
                    self.pos[0] = center[0]
                else:
                    dy = 0
            elif pointing and new_pos1 <= ty:
                self.pos[1] = center[1]
                dy = 0

        elif self.moving_down:
            if not self.can_it_move('down'):
                if new_pos1 > center[1]:
                    self.pos[1] = center[1]
                    dy = 0
            elif self.pos[0] != center[0]:
                if abs(self.pos[0] - center[0]) <= tolerance:
                    self.pos[0] = center[0]
                else:
                    dy = 0
            elif pointing and new_pos1 >= ty:
                self.pos[1] = center[1]
                dy = 0

        # Update rect attributes
        self.pos[0] += dx
        self.pos[1] += dy
        self.get_image_rect()

    def stop_and_center(self) -> None:
        """
        Stops movement if the sprite is outside the center of
        its current cell. Then it centers it.
        """
        self.stop_movement()
        center = self.get_current_center()
        self.pos = list(center)

    def path_to_cell(self, cell: tuple[int, int]) -> None:
        """
        Takes the coordinates of a cell inside the grid and
        finds the moves needed to reach another cell.
        Adjust the position of the sprites if it is not in the
        correct coordinates to begin the path following

        Parameters
        ----------
        cell: tuple[int, int]
            tuple with the x and y indexes to locate the cell in the grid

        """
        (x, y) = self.current_cell

        if (x, y) == cell:
            self.moves_to_target = []
            self.coords_to_target = []
            self.target = None
            self.stop_and_center()
            self.move_random(1.5)
            return

        bfs_results = self.bfs((x, y), cell)
        if not bfs_results[1]:
            self.moves_to_target = []
            self.coords_to_target = []
            self.target = None
            self.stop_and_center()
            return
        self.moves_to_target = bfs_results[0]
        self.coords_to_target = bfs_results[1]
        self.first_move_to_target()

    def bfs(self, p_a: tuple[int, int],
            p_b: tuple[int, int]) -> tuple[list[str], list[tuple[int, int]]]:
        """
        Finds the path that connects two positions in the maze.
        It uses the BFS (Breadth First Search) algorithm to look for a path
        from the entry to the exit. Must be used only when the grid data
        are stored in this class' attributes.

        Returns
        -------
        List of moves ('up', 'down', 'left', 'right') and list of the
        cells visited from p_a to p_b. Both are empty if no path exists.
        """
        if p_a == p_b:
            return [], [p_a]

        grid = self.grid
        width = len(grid[0])
        height = len(grid)

        N, E, S, W = 1, 2, 4, 8
        DX = {E: 1, W: -1, N:  0, S: 0}
        DY = {E: 0, W:  0, N: -1, S: 1}
        dirs = {N: 'up', E: 'right', S: 'down', W: 'left'}

        visited = [[False for _ in range(width)] for _ in range(height)]
        queue: deque[tuple[int, int]] = deque([p_a])
        visited[p_a[1]][p_a[0]] = True

        def inbounds(x: int, y: int) -> bool:
            return 0 <= x < width and 0 <= y < height

        parent_map: dict[tuple[int, int], tuple[tuple[int, int], str]] = {}
        found = False

        while queue:
            x, y = queue.popleft()

            if (x, y) == p_b:
                found = True
                break

            for dir_bit, dir_name in dirs.items():
                nx, ny = x + DX[dir_bit], y + DY[dir_bit]

                if (
                    inbounds(nx, ny) and
                    not visited[ny][nx] and
                    grid[y][x] ^ dir_bit > grid[y][x]
                ):
                    visited[ny][nx] = True
                    parent_map[(nx, ny)] = ((x, y), dir_name)
                    queue.append((nx, ny))

        if not found:
            return [], []

        moves: list[str] = []
        coords: list[tuple[int, int]] = [p_b]
        curr = p_b

        while curr != p_a:
            parent_coord, dir_name = parent_map[curr]
            moves.append(dir_name)
            coords.append(parent_coord)
            curr = parent_coord

        moves.reverse()
        coords.reverse()

        return moves, coords

    def first_move_to_target(self) -> None:
        """
        Adjust the sprite's position towards its current cell center
        if needed, before it starts moving towards a target as path
        following relays on reaching the central coordinates of the cells
        in the path.
        """
        def check_firstmove(me: Ghost) -> bool:
            if not self.moves_to_target:
                return False
            first_move = self.moves_to_target[0]
            return getattr(me, f'moving_{first_move}', False)

        def next_target_or_center(me: Ghost, key: str) -> None:
            if check_firstmove(me):
                me.get_target()
            else:
                me.change_direction(key)

        if len(self.coords_to_target) < 1:
            self.moves_to_target = []
            self.coords_to_target = []
            self.target = None
            self.stop_and_center()
            return

        self.target = self.coords_to_target.pop(0)
        target_coord = self.get_target_coord(self.target)
        if self.pos[0] > target_coord[0]:
            next_target_or_center(self, 'left')
        elif self.pos[0] < target_coord[0]:
            next_target_or_center(self, 'right')
        elif self.pos[1] > target_coord[1]:
            next_target_or_center(self, 'up')
        elif self.pos[1] < target_coord[1]:
            next_target_or_center(self, 'down')
        else:
            self.get_target()

    def get_target(self) -> None:
        """
        Retrieves the next target in the list of path coordinates and
        changes the direction according to the path's list of moves.
        """
        if len(self.moves_to_target) > 0 and len(self.coords_to_target) > 0:
            key = self.moves_to_target.pop(0)
            self.change_direction(key)
            self.target = self.coords_to_target.pop(0)
        else:
            self.target = None

    def move_random(self, dt: float) -> None:
        """
        Change the sprite's movement randomly every 1.5 seconds.

        dt: float
            Delta time, time that has passes since the last
            measurement.
        """
        if self.chasing_pacman or self.chasing_random or self.target:
            return
        self.target = None
        self.dirchange_time += dt
        if self.dirchange_time >= 1.5:
            self.dirchange_time -= 1.5
            dirs = ['right', 'left', 'up', 'down']
            valid_dirs = [d for d in dirs if self.can_it_move(d)]
            if valid_dirs:
                self.snap_to_cell()
                k = random.choice(valid_dirs)
                self.change_direction(k)

    def chase_pacman(self) -> None:
        """
        Triggers the path seeking algorithm towards PacMan's position.
        """
        if self.pacman_cell:
            self.path_to_cell(self.pacman_cell)

    def away_from_cell(self, cell: tuple[int, int]) -> None:
        """
        Triggers the path seeking algorithm towards a cell far away from
        any given position in the maze grid.

        Parameters
        ----------
        cell: tuple[int, int]
            Position in the maze grid to get away from.
        """
        width = len(self.grid[0])
        height = len(self.grid)

        radius = max(2, min(width, height) // 4)
        sx, sy = cell

        candidates = [
            (x, y)
            for y in range(height)
            for x in range(width)
            if (x, y) not in self.forbidden_cells
            and (x, y) != tuple(self.current_cell)
            and (abs(x - sx) > radius or abs(y - sy) > radius)
        ]

        if candidates:
            candidates.sort(key=lambda c: (c[0] - sx) ** 2 + (c[1] - sy) ** 2,
                            reverse=True)
            top = candidates[: max(1, len(candidates) // 2)]
            self.path_to_cell(random.choice(top))

    def flee_from_pacman(self) -> None:
        """
        Triggers the path seeking algorithm towards a cell far away from
        PacMan.
        """
        if self.pacman_cell is None:
            sx, sy = self.current_cell
            self.away_from_cell((sx, sy))
            return

        width = len(self.grid[0])
        height = len(self.grid)

        px, py = self.pacman_cell
        target_x = 0 if px > width // 2 else width - 1
        target_y = 0 if py > height // 2 else height - 1

        candidates = [
            (x, y)
            for y in range(height)
            for x in range(width)
            if (x, y) not in self.forbidden_cells
            and (x, y) != tuple(self.current_cell)
        ]

        if candidates:
            candidates.sort(key=lambda c: (c[0] - target_x) ** 2 +
                            (c[1] - target_y) ** 2)
            top_slice = max(1, len(candidates) // 10)
            top = candidates[: top_slice]
            self.path_to_cell(random.choice(top))
        else:
            sx, sy = self.current_cell
            self.away_from_cell((sx, sy))

    def assess_distance_then_move(self) -> None:
        """
        Assess if the current position is close to PacMan to either flee
        from pacman (when close) or to a random cell (when far).
        """
        x, y = self.current_cell

        if self.pacman_cell is None:
            self.away_from_cell((x, y))
            return

        px, py = self.pacman_cell
        dist_to_pacman = ((x - px) ** 2 + (y - py) ** 2) ** 0.5

        width = len(self.grid[0])
        height = len(self.grid)
        safe_dist = min(width, height) / 2
        if dist_to_pacman >= safe_dist:
            self.away_from_cell((x, y))
        else:
            self.flee_from_pacman()

    def frightened_mode(self) -> None:
        """
        Set the frightened mode and changes the appropiate attributes.
        """
        if not self.eaten and not self.frightened:
            self.frightened = True
            self.chasing_random = False
            self.chasing_pacman = False
            self.fright_time = 0
            self.row = 'frightened'
            self.assess_distance_then_move()

    def get_eaten(self) -> None:
        """
        Set the eaten mode and changes the appropiate attributes.
        """
        self.frightened = False
        self.eaten = True
        self.current_frame = 0
        self.path_to_cell(self.home_cell)
        self._change_eyes_row()

    def revive(self) -> None:
        """
        Returns the sprite to the normal mode.
        Clears path and target information.
        """
        self.eaten = False
        self.moves_to_target = []
        self.coords_to_target = []
        self.target = None
        self._change_direction_row()

    def change_behavior(self, dt: float = 0) -> None:
        """
        Changes the sprite's behavior based on the time measured and
        the sprite's current mode.

        Parameters
        ----------
        dt: float
            Delta time, time that has passes since the last
            measurement.
        """
        self.behavior_timer += dt

        if self.frightened:
            self.fright_reassess_timer += dt
            if self.fright_reassess_timer >= 2:
                self.fright_reassess_timer = 0
                self.assess_distance_then_move()
            elif (
                  not self.moves_to_target
                  and not self.coords_to_target
                  and self.target is None
            ):
                self.assess_distance_then_move()
            return

        self.fright_reassess_timer = 0

        inverse = {0: 3, 1: 2, 2: 1, 3: 0}
        chasing_time = 10 - self.gh_type * 3
        random_time = 10 - inverse[self.gh_type] * 2

        if self.chasing_pacman:
            if self.behavior_timer >= chasing_time:
                self.chasing_pacman = False
                self.target = None
                if self.gh_type in [0, 1, 2]:
                    self.chasing_random = True
                    (x, y) = self.current_cell
                    self.away_from_cell((x, y))
                self.behavior_timer -= chasing_time
            elif self.behavior_timer >= 3:
                self.chase_pacman()
        elif (
              not self.eaten and
              self.behavior_timer >= random_time
        ):
            if self.gh_type in [0, 1, 2]:
                self.chasing_random = False
            self.chasing_pacman = True
            self.chase_pacman()
            self.behavior_timer -= random_time

    def update(self, dt: float = 0) -> None:
        """
        Updates the ghost's behavior, animation frame and position, and
        advances along its path when it reaches a target cell.
        """
        self.animation_timer += dt
        self.change_behavior(dt)
        if not self.frightened or self.eaten:
            if (
                self.its_moving() and
                self.animation_timer >= self.cooldown
            ):
                self.animation_timer -= self.cooldown
                self.current_frame = ((self.current_frame + 1)
                                      % len(self.sprites[self.row]))
        else:
            frames = 2
            self.fright_time += dt
            if self.fright_time >= 8:
                self.frightened = False
                self.current_frame = 0 if self.current_frame % 2 == 0 else 1
                self._change_direction_row()

            elif self.fright_time >= 5:
                frames = 4
            if self.animation_timer >= self.cooldown:
                self.animation_timer -= self.cooldown
                self.current_frame = (self.current_frame + 1) % frames

        self.image = self.sprites[self.row][self.current_frame]

        self.move_rect(dt)
        self.update_current_cell()

        # Check if ghost arrived to position and update target
        if self.target:
            target_coord = self.get_target_coord(self.target)
            if tuple(self.pos) == target_coord:
                self.get_target()
