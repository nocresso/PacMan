from mazegenerator import MazeGenerator
from src.parser import GameConfiguration


class MazeLoadError(Exception):
    """
    Custom exception he maze generator failed or
    returned an invalid maze.
    """


class LevelMaze:
    """
    Information that game needs from a generated maze.
    """
    def __init__(self, grid: list[list[int]], seed: int) -> None:
        self.grid = grid
        self.seed = seed


def build_level_maze(config: GameConfiguration, level_index: int) -> LevelMaze:
    """
    Generate the maze for a given level using the assigned mazegenerator
    package and the given game configuration.
    """
    level = config.levels[level_index]
    seed = config.seed if level_index == 0 else 0
    try:
        generator = MazeGenerator(size=(level.width, level.height),
                                  perfect=False, seed=seed)
        grid = generator.maze
    except Exception as e:
        raise MazeLoadError(f"Maze generation failed: {e}") from e

    return LevelMaze(grid=grid, seed=seed)
