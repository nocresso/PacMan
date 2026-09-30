import random
from .ghosts import Ghost
from .general_sprite_classes import SpriteGroup
from .pacman_sprite import PacMan
from .pellets import Pellet, MegaPellet


class GhostGroup(SpriteGroup):
    """
    SpriteGroup class tailored to call methods especific of Ghost type
    sprites.
    """
    def __init__(self) -> None:
        super().__init__()

    def move(self, dt: float) -> None:
        """
        Calls the move_random method of all the sprites stored
        in the sprite list.

        Parameters
        ----------
        dt: float
            Delta time, time that has passes since the last
            measurement.
        """
        for spr in self.sprites:
            if isinstance(spr, Ghost) and not spr.eaten:
                spr.move_random(dt)

    def update_pacman_coords(self, pacman_cell: tuple[int, int]) -> None:
        """
        Calls the update_pacaman_coords method of all the sprites stored
        in the sprite list.

        Parameters
        ----------
        pacman_cell: tuple[int, int]
            PacMan sprite current position in the maze grid.
        """
        for spr in self.sprites:
            if isinstance(spr, Ghost):
                spr.update_pacman_coords(pacman_cell)

    def get_forbidden(self, cells: list[tuple[int, int]]) -> None:
        """
        Calls the get_forbidden method of all the sprites stored
        in the sprite list.

        Parameters
        ----------
        cells: list[tuple[int, int]]
            List of forbidden cells inside the maze grid.
        """
        for spr in self.sprites:
            if isinstance(spr, Ghost):
                spr.get_forbidden(cells)

    def frightened_mode(self) -> None:
        """
        Calls the frightened_mode method of all the sprites stored
        in the sprite list.
        """
        for spr in self.sprites:
            if isinstance(spr, Ghost):
                spr.frightened_mode()

    def check_collision(self, player: PacMan,
                        points: int, cheat: bool) -> int:
        """
        Checks collision events of all the sprites stored in the sprite list
        under different circumstances.

        Triggers frightened mode, eaten mode and revival of Ghost type objects
        or the death of the player.

        Increases the game score when eaten mode is triggered.

        Parameters
        ----------
        player: PacMan
            PacMan sprite object.
        points: int
            Points to be awarded when eaten.
        cheat: bool
            Indicates if a game cheat mode is active.

        Returns
        -------
        earned: int
            Total of earned points resulting from collisions.
        """
        earned = 0
        for spr in self.sprites:
            if isinstance(spr, Ghost):
                if spr.frightened and spr.collision(player):
                    spr.get_eaten()
                    earned += points
                elif spr.eaten:
                    if tuple(spr.current_cell) == spr.home_cell:
                        spr.revive()
                elif not spr.eaten and spr.collision(player) and not cheat:
                    player.die()
        return earned


class PelletGroup(SpriteGroup):
    """
    SpriteGroup class tailored to call methods especific of Pellet type
    sprites.
    """
    def __init__(self) -> None:
        super().__init__()

    def death_on_collision(self, player: PacMan,
                           points: int = 0) -> int:
        """
        Checks collision events of all the sprites stored in the sprite list.
        Triggers erase of Pellet object when a collision is detected.

        Parameters
        ----------
        player: PacMan
            PacMan sprite object.
        points: int
            Points to be awarded when eaten.

        Returns
        -------
        earned: int
            Total of earned points resulting from collisions.
        """
        sprites_copy = self.sprites.copy()
        earned = 0
        for spr in sprites_copy:
            if spr.collision(player):
                earned += points
                spr.kill()
        return earned


class MegaPelletGroup(PelletGroup):
    """
    SpriteGroup class tailored to call methods especific of MegaPellet type
    sprites.
    """
    def __init__(self) -> None:
        super().__init__()

    def trigger_fright(self, player: PacMan, ghosts: GhostGroup,
                       points: int) -> int:
        """
        Checks collision events of all the sprites stored in the sprite list.
        Triggers erase of MegaPellet object when a collision is detected and
        frightened mode of Ghost sprites.

        Parameters
        ----------
        player: PacMan
            PacMan sprite object.
        ghosts: GhostGroup
            Ghost type objects group.
        points: int
            Points to be awarded when eaten.

        Returns
        -------
        earned: int
            Total of earned points resulting from collisions.
        """
        sprites_copy = self.sprites.copy()
        earned = 0
        for spr in sprites_copy:
            if spr.collision(player):
                earned += points
                spr.kill()
                ghosts.frightened_mode()
        return earned


def spawn_pellets(grid: list[list[int]],
                  screen_grid: list[list[tuple[float, float]]],
                  pellet_nb: int, scale: float = 3) -> PelletGroup:
    """
    Instatiate several Pellet objects in random cells inside the maze
    and stores them in PelletGroup.

    Parameters
    ----------
    grid: list[list[int]]
        Maze grid data.
    screen_grid: list[list[tuple[float, float]]]
        Coordinates of all grid cell centers in the screen.
    pellet_nb: int
        Number of Pellet type objects to be instantiated.

    Returns
    -------
    pellets: PelletGroup
    """
    pellets = PelletGroup()
    available_cells = [
        (x, y) for x in range(len(grid[0]))
        for y in range(len(grid)) if grid[y][x] != 15]
    pellet_nb = min(pellet_nb, len(available_cells))
    chosen_cells = random.sample(available_cells, pellet_nb)
    for x, y in chosen_cells:
        s_x, s_y = screen_grid[y][x]
        pellet = Pellet(s_x, s_y, scale)
        pellets.add(pellet)
    return pellets


def spawn_megapellets(grid: list[list[int]],
                      screen_grid: list[list[tuple[float, float]]],
                      scale: float = 3) -> MegaPelletGroup:
    """
    Instantiates four MegaPellet objects, one in each corner cell of
    the maze, and stores them in a MegaPelletGroup.

    Parameters
    ----------
    grid: list[list[int]]
        Maze grid data.
    screen_grid: list[list[tuple[float, float]]]
        Coordinates of all grid cell centers in the screen.

    Returns
    -------
    megapellets: MegaPelletGroup
    """
    megapellets = MegaPelletGroup()

    coords = [(0, 0),
              (0, len(screen_grid) - 1),
              (len(screen_grid[0]) - 1, 0),
              (len(screen_grid[0]) - 1, len(screen_grid) - 1)]
    for x, y in coords:
        s_x, s_y = screen_grid[y][x]
        pellet = MegaPellet(s_x, s_y, scale)
        megapellets.add(pellet)
    return megapellets


def init_ghosts(screen_grid: list[list[tuple[float, float]]],
                scale: float = 3, speed: float = 150) -> GhostGroup:
    """
    Instatiate four Ghost objects in the four corner cells of the maze
    and stores them in GhostGroup.

    Parameters
    ----------
    screen_grid: list[list[tuple[float, float]]]
        Coordinates of all grid cell centers in the screen.

    Returns
    -------
    ghosts: GhostGroup
    """
    ghosts = GhostGroup()

    coords = [(1, 0),
              (0, len(screen_grid) - 2),
              (len(screen_grid[0]) - 1, 1),
              (len(screen_grid[0]) - 1, len(screen_grid) - 2)]
    for gh_type, (x, y) in enumerate(coords):
        s_x, s_y = screen_grid[y][x]
        ghost = Ghost(s_x, s_y, scale, gh_type, speed=speed)
        ghost.home_cell = (x, y)
        ghosts.add(ghost)
    return ghosts
