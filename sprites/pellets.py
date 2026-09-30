import pygame
from pygame.surface import Surface
from .general_sprite_classes import CustomSprite


class Pellet(CustomSprite):
    """
    Sprite class for the small pellets (pacgums) PacMan eats to
    earn points.
    """
    def __init__(self, x: float, y: float,
                 scale: float = 4, cooldown: float = 0) -> None:
        super().__init__(x, y, scale, cooldown)
        self.image: Surface = self.image_load()
        self.get_image_rect()

    def image_load(self) -> Surface:
        """
        Loads the pellet image from the sprite sheet.
        """
        sheet_path = 'src_images/pacman_and_ghosts_v2.png'
        sheet = pygame.image.load(sheet_path).convert_alpha()
        return CustomSprite.get_img(sheet, (1, 167), 0, 4, 4, self.scale)

    def update(self, dt: float = 0) -> None:
        """
        Does nothing: pellets are static. Required by CustomSprite.
        """
        pass


class MegaPellet(CustomSprite):
    """
    Sprite class for the big pellets (superpacgums) PacMan eats to
    earn points. Blinks on and off like the original arcade's
    power pellets.
    """

    BLINK_PERIOD = 0.25

    def __init__(self, x: float, y: float, scale: float = 4,
                 cooldown: float = 0) -> None:
        super().__init__(x, y, scale, cooldown)
        self.image: Surface = self.image_load()
        self.get_image_rect()
        self.blink_timer: float = 0.0
        self.visible: bool = True

    def image_load(self) -> Surface:
        """
        Loads the pellet image from the sprite sheet.
        """
        sheet_path = 'src_images/pacman_and_ghosts_v2.png'
        sheet = pygame.image.load(sheet_path).convert_alpha()
        return CustomSprite.get_img(sheet, (1, 175), 0, 8, 8, self.scale)

    def update(self, dt: float = 0) -> None:
        """
        Toggles visibility on a timer to produce the blinking effect.
        """
        self.blink_timer += dt
        if self.blink_timer >= self.BLINK_PERIOD:
            self.blink_timer -= self.BLINK_PERIOD
            self.visible = not self.visible

    def draw(self, screen: Surface) -> None:
        """
        Draws the sprite only while it is in its "on" blink phase.
        """
        if self.visible:
            super().draw(screen)
