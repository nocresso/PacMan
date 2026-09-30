from abc import ABC, abstractmethod
import pygame
import json
import sys
from typing import Optional, List, Any, Tuple, Dict
from src.parser import is_valid_entry

PIXEL_FONT_PATH = "fonts/PressStart2P-Regular.ttf"
NEON_YELLOW = (255, 221, 0)
NEON_YELLOW_GLOW = (255, 140, 0)
NEON_CYAN = (80, 220, 255)
_pixel_font_cache: Dict[int, pygame.font.Font] = {}


def scaled_size(reference: int, fraction: float,
                min_size: int, max_size: int) -> int:
    """
    Scales a font/spacing size as a fraction of a reference length
    (typically the surface height), clamped to a sane range so text
    stays legible on both tiny and huge windows.
    """
    return max(min_size, min(max_size, round(reference * fraction)))


def load_pixel_font(size: int) -> pygame.font.Font:
    """
    Loads (and caches) the arcade-style pixel font at a given size,
    falling back to a bold monospace system font if it's unavailable.
    """
    if size not in _pixel_font_cache:
        try:
            _pixel_font_cache[size] = pygame.font.Font(
                PIXEL_FONT_PATH, size)
        except (FileNotFoundError, OSError):
            _pixel_font_cache[size] = pygame.font.SysFont(
                "couriernew", size, bold=True)
    return _pixel_font_cache[size]


def fit_pixel_font(text: str, max_width: int,
                   ideal_size: int, min_size: int) -> pygame.font.Font:
    """
    Picks the largest pixel font size (down to min_size) that renders
    the given text within max_width.
    """
    size = ideal_size
    while size > min_size:
        if load_pixel_font(size).size(text)[0] <= max_width:
            break
        size -= 2
    return load_pixel_font(max(size, min_size))


def render_glow_text(font: pygame.font.Font, text: str,
                     color: Tuple[int, int, int],
                     glow_color: Tuple[int, int, int]) -> pygame.Surface:
    """
    Renders text with a soft neon halo behind it, built from a few
    offset, translucent copies of the same text.
    """
    base = font.render(text, True, color)
    pad = max(4, font.get_height() // 6)
    width, height = base.get_size()
    surface = pygame.Surface((width + pad * 2, height + pad * 2),
                             pygame.SRCALPHA)
    glow = font.render(text, True, glow_color)
    glow.set_alpha(90)
    offsets = [(-2, 0), (2, 0), (0, -2), (0, 2),
               (-2, -2), (2, 2), (-2, 2), (2, -2)]
    for ox, oy in offsets:
        surface.blit(glow, (pad + ox, pad + oy))
    surface.blit(base, (pad, pad))
    return surface


def centered_topleft(width: int, height: int, center_x: int,
                     center_y: int) -> Tuple[int, int]:
    """
    Compute the top-left coordinates a rectangle must have so that
    it is centered on a given point.
    """
    x = center_x - width // 2
    y = center_y - height // 2
    return (x, y)


def read_scores(filename: str) -> list[dict[str, Any]]:
    """
    Reads the highscores file and on any problem it
    prints a message and returns only the valid entries (or none).
    """
    try:
        with open(filename, "r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        return []
    except (OSError, ValueError) as error:
        sys.stderr.write(f"Highscores: cannot read '{filename}': {error}\n")
        return []
    if not isinstance(data, list):
        sys.stderr.write(f"Highscores: '{filename}' must contain a list\n")
        return []
    scores = [entry for entry in data if is_valid_entry(entry)]
    scores.sort(key=lambda e: e["score"], reverse=True)
    return scores[:10]


class UserInterface(ABC):
    """
    Common interface for any full-screen view the game can show
    (main menu, pause menu, highscores, game over, etc.).
    """

    @abstractmethod
    def draw(self, surface: pygame.Surface) -> None:
        """
        Render this screen onto the given surface.
        """
        pass

    @abstractmethod
    def handle_events(self, event: pygame.event.Event) -> Optional[str]:
        """
        Process one pygame event and return an action label when
        the player confirms a choice, otherwise return None.
        """
        pass


class OptionsMenu(UserInterface):
    """
    Base for any screen showing a title and a vertical list of
    selectable options, with keyboard navigation
    (UP/DOWN to move the selection, ENTER to confirm).
    """

    def __init__(self, title: str, options: List[str]) -> None:
        """
        Store this screen's title and its list of selectable
        options.
        """
        self.title = title
        self.options = options
        self.selected_index = 0
        self._font_size_key: Optional[Tuple[int, int]] = None

    def _ensure_fonts(self, surface: pygame.Surface) -> None:
        """
        (Re)builds the fonts sized relative to the surface only when
        the surface's size actually changed.
        """
        size_key = surface.get_size()
        if self._font_size_key == size_key:
            return
        self._font_size_key = size_key
        width, height = size_key
        max_width = round(width * 0.88)
        title_ideal = scaled_size(height, 0.09, 20, 90)
        self.title_font = fit_pixel_font(
            self.title, max_width, title_ideal, 12)
        options_ideal = scaled_size(height, 0.045, 12, 34)
        longest = max(self.options, key=len)
        self.options_font = fit_pixel_font(
            "> " + longest, max_width, options_ideal, 8)

    def draw(self, surface: pygame.Surface) -> None:
        """
        Render the title and the list of options onto the given
        surface, highlighting the currently selected option.
        """
        self._ensure_fonts(surface)
        surface.fill((0, 0, 0))
        width = surface.get_width()
        height = surface.get_height()
        title = render_glow_text(self.title_font, self.title,
                                 NEON_YELLOW, NEON_YELLOW_GLOW)
        title_pos = centered_topleft(title.get_width(),
                                     title.get_height(), width // 2,
                                     round(height * 0.12))
        surface.blit(title, title_pos)
        start_y_options = round(height * 0.4)
        gap = scaled_size(height, 0.075, 24, 70)
        for i, option in enumerate(self.options):
            selected = i == self.selected_index
            color = NEON_YELLOW if selected else NEON_CYAN
            prefix = "> " if selected else "  "
            option_text = self.options_font.render(
                prefix + option, True, color)
            option_pos = centered_topleft(option_text.get_width(),
                                          option_text.get_height(),
                                          width // 2, start_y_options + i*gap)
            surface.blit(option_text, option_pos)

    def handle_events(self, event: pygame.event.Event) -> Optional[str]:
        """
        Updates the selected options and returns the
        selected option's label when ENTER is pressed.
        """
        if event.type != pygame.KEYDOWN:
            return None
        if event.key == pygame.K_UP:
            self.selected_index = (self.selected_index - 1) % len(self.options)
        elif event.key == pygame.K_DOWN:
            self.selected_index = (self.selected_index + 1) % len(self.options)
        elif event.key == pygame.K_RETURN:
            return self.options[self.selected_index]
        return None


class MainMenu(OptionsMenu):
    """
    Main menu of the game.
    """
    def __init__(self) -> None:
        super().__init__(
            "PAC-MAN", ["START GAME", "VIEW HIGHSCORES",
                        "INSTRUCTIONS", "EXIT"])


class PauseMenu(OptionsMenu):
    """
    Pause menu shown while a game is in progress, letting the
    player resume or return to the main menu.
    """
    def __init__(self) -> None:
        super().__init__(
            "PAUSE MENU", ["RESUME THE GAME", "RETURN TO THE MAIN MENU"])


class InputScreen(UserInterface):
    """
    Base for any screen showing the final score and asking the
    player to type their name to save it.
    """

    MAX_NAME_LENGTH = 10

    def __init__(self, title: str,
                 score: int, prompt: str,
                 filename: str) -> None:
        """
        Store this screen's title and the prompt for the user.
        """
        self.title = title
        self.score = score
        self.prompt = prompt
        self.filename = filename
        self.player_name = ""
        self._font_size_key: Optional[Tuple[int, int]] = None

    def _ensure_fonts(self, surface: pygame.Surface) -> None:
        """
        (Re)builds the fonts sized relative to the surface only when
        the surface's size actually changed.
        """
        size_key = surface.get_size()
        if self._font_size_key == size_key:
            return
        self._font_size_key = size_key
        width, height = size_key
        max_width = round(width * 0.88)
        title_ideal = scaled_size(height, 0.09, 20, 90)
        self.title_font = fit_pixel_font(
            self.title, max_width, title_ideal, 12)
        std_ideal = scaled_size(height, 0.045, 12, 32)
        longest = max(["Score: 999999", self.prompt,
                      "M" * self.MAX_NAME_LENGTH + "_"], key=len)
        self.std_font = fit_pixel_font(longest, max_width, std_ideal, 8)
        self.input_font = self.std_font

    def draw(self, surface: pygame.Surface) -> None:
        """
        Render the title, the score, the prompt, and the name
        typed so far onto the given surface.
        """
        self._ensure_fonts(surface)
        surface.fill((0, 0, 0))
        width = surface.get_width()
        height = surface.get_height()

        title = render_glow_text(self.title_font, self.title,
                                 NEON_YELLOW, NEON_YELLOW_GLOW)
        title_pos = centered_topleft(title.get_width(),
                                     title.get_height(), width // 2,
                                     round(height * 0.14))
        surface.blit(title, title_pos)

        score_surface = self.std_font.render(
            f"Score: {self.score}", True, NEON_YELLOW)
        score_pos = centered_topleft(
            score_surface.get_width(),
            score_surface.get_height(), width // 2, round(height * 0.245))
        surface.blit(score_surface, score_pos)

        prompt_surface = self.std_font.render(
            self.prompt, True, NEON_CYAN)
        prompt_pos = centered_topleft(prompt_surface.get_width(),
                                      prompt_surface.get_height(),
                                      width // 2, round(height * 0.315))
        surface.blit(prompt_surface, prompt_pos)

        input_surface = self.input_font.render(
            self.player_name + "_", True, NEON_YELLOW)
        input_pos = centered_topleft(
            input_surface.get_width(), input_surface.get_height(),
            width // 2, round(height * 0.42))
        surface.blit(input_surface, input_pos)

    def handle_events(self, event: pygame.event.Event) -> Optional[str]:
        """
        Prompts the player to enter their name to save the score and
        returns it when press ENTER.
        """
        if event.type != pygame.KEYDOWN:
            return None
        if event.key == pygame.K_RETURN:
            name = self.player_name.strip()
            if not name:
                return None
            entry = {"name": name, "score": self.score}
            if not is_valid_entry(entry):
                return None
            scores = read_scores(self.filename)
            scores.append(entry)
            scores.sort(key=lambda e: e["score"], reverse=True)
            try:
                with open(self.filename, "w", encoding="utf-8") as file:
                    json.dump(scores[:10], file, indent=4)
            except OSError as error:
                sys.stderr.write(
                    f"Highscores: cannot save '{self.filename}': {error}\n")
            return name

        if event.key == pygame.K_BACKSPACE:
            self.player_name = self.player_name[:-1]
            return None
        if (event.unicode.isascii() and (
            event.unicode.isalnum() or event.unicode == " ") and (
                len(self.player_name) < self.MAX_NAME_LENGTH)):
            self.player_name += event.unicode
        return None


class GameOverScreen(InputScreen):
    "Game Over Screen shown when player loses."

    def __init__(self, score: int, filename: str) -> None:
        super().__init__("GAME OVER", score, "Enter your name:", filename)


class VictoryScreen(InputScreen):
    "Victory Screen shown when player wins."

    def __init__(self, score: int, filename: str) -> None:
        super().__init__("YOU WIN!", score, "Enter your name:", filename)


class InfoScreen(UserInterface):
    """
    Base for any screen showing information to the user.
    """

    def __init__(self, title: str, text: List[str],
                 align: str = "center") -> None:
        """
        Store this screen's title and the prompt for the user.
        """
        self.title = title
        self.text = text
        self.align = align
        self._font_size_key: Optional[
            Tuple[Tuple[int, int], Tuple[str, ...]]] = None

    def _ensure_fonts(self, surface: pygame.Surface) -> None:
        """
        (Re)builds the fonts sized relative to the surface only when
        the surface's size or text content actually changed.
        """
        size_key = (surface.get_size(), tuple(self.text))
        if self._font_size_key == size_key:
            return
        self._font_size_key = size_key
        width, height = surface.get_size()
        title_ideal = scaled_size(height, 0.075, 16, 70)
        self.title_font = fit_pixel_font(
            self.title, round(width * 0.88), title_ideal, 10)
        std_ideal = scaled_size(height, 0.04, 10, 26)
        left_margin = width // 10
        indent = round(width * 0.03125)
        body_max_width = (round(width * 0.88) if self.align != "left"
                          else width - left_margin - indent - 10)
        longest_line = max((line.strip() for line in self.text),
                           key=len, default="PLACEHOLDER")
        self.std_font = fit_pixel_font(
            longest_line, max(body_max_width, 50), std_ideal, 8)

    def draw(self, surface: pygame.Surface) -> None:
        """
        Render the title and the information onto the given surface.
        """
        self._ensure_fonts(surface)
        surface.fill((0, 0, 0))
        width = surface.get_width()
        height = surface.get_height()

        title = render_glow_text(self.title_font, self.title,
                                 NEON_YELLOW, NEON_YELLOW_GLOW)
        title_pos = centered_topleft(title.get_width(),
                                     title.get_height(), width // 2,
                                     round(height * 0.14))
        surface.blit(title, title_pos)

        left_margin = width // 10
        indent = round(width * 0.03125)
        y = round(height * 0.32)
        line_gap = scaled_size(height, 0.056, 14, 70)
        continuation_gap = scaled_size(height, 0.0455, 11, 58)
        for line in self.text:
            is_continuation = line.startswith(" ")
            content = line.strip()
            text_surface = self.std_font.render(
                content, True, NEON_CYAN)

            if self.align == "left":
                x = left_margin + (indent if is_continuation else 0)
                text_pos = (x, y)
            else:
                text_pos = centered_topleft(
                    text_surface.get_width(),
                    text_surface.get_height(), width // 2, y)
            surface.blit(text_surface, text_pos)
            y += continuation_gap if is_continuation else line_gap

    def handle_events(self, event: pygame.event.Event) -> Optional[str]:
        """
        Process one pygame event and return to the main menu when the
        player presses ENTER or ESCAPE.
        """
        if event.type != pygame.KEYDOWN:
            return None
        if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
            return "MAIN MENU"
        return None


class HighscoreScreen(InfoScreen):
    "Highscore Screen that shows the 10 top highscores."

    def __init__(self, filename: str) -> None:
        super().__init__("PAC-MAN", [])
        self.filename = filename
        self.load_scores()

    def load_scores(self) -> None:
        scores = read_scores(self.filename)
        self.text = [f"{entry['name']}: {entry['score']}"
                     for entry in scores]


class InstructionsScreen(InfoScreen):
    "Screen to show the game instructions."

    def __init__(self) -> None:
        self.text = [
            "How to Play:",
            "- Move: Use the arrow keys or WASD to guide",
            "  Pac-Man through the maze.",
            "- Eat the pacgums: Clear every pacgum to win",
            "  the level.",
            "- Avoid ghosts: Blinky, Pinky, Inky and Clyde",
            "  will end your run if they catch you.",
            "- Superpacgums: Eat the four big pacgums to",
            "  turn ghosts blue and vulnerable.",
            "- Eat ghosts: Touch blue ghosts for bonus",
            "  points before they turn back."]
        super().__init__("INSTRUCTIONS", self.text, "left")
