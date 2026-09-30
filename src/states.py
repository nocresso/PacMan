from enum import Enum, auto


class GameState(Enum):
    """
    Enumeration of the distinct states the game can be in, used by
    `Game` to decide what to update and draw on each frame, and by
    each screen to know which action was chosen.

    Attributes
    ----------
    MENU
        The main menu is being shown.
    PLAYING
        A level is currently being played.
    PAUSED
        Gameplay is paused and the pause menu is being shown.
    GAME_OVER
        The player has lost all lives and the game over screen is
        being shown.
    VICTORY
        The player has completed all levels and the victory screen
        is being shown.
    HIGHSCORES
        The highscores screen is being shown.
    INSTRUCTIONS
        The instructions screen is being shown.
    """
    MENU = auto()
    PLAYING = auto()
    PAUSED = auto()
    GAME_OVER = auto()
    VICTORY = auto()
    HIGHSCORES = auto()
    INSTRUCTIONS = auto()
