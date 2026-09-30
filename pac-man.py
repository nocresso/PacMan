from src.parser import (ConfigurationError, load_config)
import os
import sys
import pygame
from src.game import Game
from src.maze_loader import MazeLoadError


def main() -> None:
    """
    Loads the configuration and runs the game.
    """
    def get_base_dir() -> str:
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))

    BASE_DIR = get_base_dir()

    try:
        if len(sys.argv) > 1:
            config_file = sys.argv[1]
        else:
            config_file = os.path.join(BASE_DIR, 'config.json')

        if not os.path.exists(config_file):
            raise FileNotFoundError("Configuration file not found"
                                    f"at {config_file}\n")

        game_config = load_config(config_file)
        game = Game(game_config)
        try:
            game.run()
        finally:
            pygame.quit()

    except (FileNotFoundError, MazeLoadError, ConfigurationError) as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)
    except (pygame.error, OSError) as e:
        sys.stderr.write(f"Error: cannot load a resource: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except KeyboardInterrupt:
        sys.stderr.write("\nProgram was manually stopped: Ctrl+C detected\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Unexpected error: {type(e).__name__}: {e}\n")
        sys.exit(1)
