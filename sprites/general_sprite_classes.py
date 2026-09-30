import pygame
from pygame.surface import Surface

from abc import ABC, abstractmethod


class Rect:
    """
    Custom Rect class since pygame's Rects are forbidden as they
    have no equivalent in MLX

    Parameters
    ----------
    x: float
        Position in x axis
    y: float
        Position in y axis
    w: int
        Width, this must correspond an image width
    h: int
        Height, this must correspond an image height

    Atttributes
    -----------
    Same as the parameters
    """
    def __init__(self,
                 x: float = 0,
                 y: float = 0,
                 w: float = 0,
                 h: float = 0) -> None:
        self.x: float = x
        self.y: float = y
        self.w: float = w
        self.h: float = h


class CustomSprite(ABC):
    """
    Custom Sprite class for image loading.
    Has basic custom implementation of some pygame's methods

    Parameters
    ----------
    x: float
        Sprite's position in the screen's x axis.
    y: float
        Sprite's position in the screen's y axis.
    scale: float
        Value used to scale the sprite's size.
    cooldown: float
        Animation cooldown value.

    Attributes
    ----------
    scale
        Sprite's size modification value.
    cooldown
        Determines how fast the animation frames of a sprite
        are going to be changed.
    image
        Surface object with the sprite that's displayed on the screen.
        Gets updated with the animation.
    pos
        List of two values (x and y) that indicates the sprite's position
        on the screen.
    rect
        Rect with the information of the sprite's image size.
    collision_rect
        Rect object used for sprite collision mechanics.
    screen_width
        Screen width value
    screen_height
        Screen height value
    __sprite_groups__
        List of SpriteGroup objects where the sprite has been registered.

    """

    def __init__(self, x: float, y: float,
                 scale: float = 1.0,
                 cooldown: float = 0.06) -> None:
        self.scale: float = scale
        self.cooldown: float = cooldown
        self.image: Surface = pygame.Surface((42, 42))
        self.pos: list[float] = [x, y]
        self.rect: Rect = Rect()
        self.get_image_rect()
        self.collision_rect = self.rect
        self.animation_timer: float = 0
        self.screen_width: int = 0
        self.screen_height: int = 0
        self.__sprite_groups__: list[SpriteGroup] = []

    @staticmethod
    def scale_image(src_image: Surface,
                    new_width: int, new_height: int) -> Surface:
        """
        Custom implementation of pygame's scale function.

        Parameters
        ----------
        src_image: Surface
            Surface type object to be scaled.
        new_width: int
            Width to scale the object.
        new_height: int
            Height to scale the object.
        """
        dst_surface = Surface((new_width, new_height),
                              pygame.SRCALPHA).convert_alpha()
        src_width, src_height = src_image.get_size()

        ratio_x = src_width / new_width
        ratio_y = src_height / new_height

        src_pix = pygame.PixelArray(src_image)
        dst_pix = pygame.PixelArray(dst_surface)

        for y in range(new_height):
            for x in range(new_width):
                src_x = int(x * ratio_x)
                src_y = int(y * ratio_y)

                dst_pix[x, y] = src_pix[src_x, src_y]  # type: ignore[index]

        del src_pix
        del dst_pix

        return dst_surface

    @staticmethod
    def get_img(sheet: Surface, ori: tuple[int, int],
                frame: int, width: int, height: int,
                scale: float) -> Surface:
        """
        Helper function to upload an image from an sprite sheet.
        """
        x, y = ori
        img = pygame.Surface((width, height),
                             pygame.SRCALPHA).convert_alpha()
        img.blit(sheet, (0, 0), (x + (frame * width), y, width, height))
        return CustomSprite.scale_image(img, int(width * scale),
                                        int(height * scale))

    @staticmethod
    def get_top_left(x: float, y: float, w: float, h: float
                     ) -> tuple[float, float]:
        """
        Calculates where the top left coordinates of a Rect would be based
        on a central coordinates and the Rect dimensions.

        Parameters
        ----------
        x: float
            Central x coordinate.
        y: float
            Central y coordinate.
        h: float
            Height of the Rect object.
        w: float
            Width of the Rect object.

        Returns
        -------
        tuple[float, float]
            Top left coordinates.
        """
        top_left_x = x - w / 2
        top_left_y = y - h / 2
        return top_left_x, top_left_y

    @staticmethod
    def get_center(top_x: float, top_y: float, w: float, h: float
                   ) -> tuple[float, float]:
        """
        Calculates where the center coordinates of a Rect would be based
        on the top left coordinates and the Rect dimensions.

        Parameters
        ----------
        top_x: float
            Top left x coordinate.
        top_y: float
            Top left y coordinate.
        h: float
            Height of the Rect object.
        w: float
            Width of the Rect object.

        Returns
        -------
        tuple[float, float]
            Central coordinates.
        """
        x = top_x + w / 2
        y = top_y + h / 2
        return x, y

    def get_image_rect(self) -> None:
        """
        Extracts the images width and height, as well as the sprite's position
        and stores them in the Rect object in rect attribute.
        """
        w = float(self.image.get_width())
        h = float(self.image.get_height())
        self.rect.w = w
        self.rect.h = h
        x = self.pos[0]
        y = self.pos[1]
        t_x, t_y = self.get_top_left(x, y, w, h)
        self.rect.x = t_x
        self.rect.y = t_y

    @abstractmethod
    def update(self, dt: float = 0) -> None:
        """
        Updates the sprite frame to produce the animation in the
        game's loop
        """
        pass

    def draw(self, screen: Surface) -> None:
        """
        Draws the sprite on to a screen Surface.

        Parameters
        ----------
        screen: Surface
            Surface where the image is displayed.
        """
        x = self.rect.x
        y = self.rect.y
        screen.blit(self.image, (int(x), int(y)))

    def collision(self, b: 'CustomSprite') -> bool:
        """
        Determines if a collision with another CustomSprite object
        has occurred based on the intersection of their respective
        collision Rect objects.

        Parameters
        ----------
        b: CustomSprite
            Another CustomSprite object

        Returns
        -------
        bool
            True if two object collide, False if not.
        """

        # Objects current coordinates
        a_x = self.collision_rect.x
        a_y = self.collision_rect.y
        b_x = b.collision_rect.x
        b_y = b.collision_rect.y

        # Objects dimensions
        a_w = self.collision_rect.w
        a_h = self.collision_rect.h
        b_w = b.collision_rect.w
        b_h = b.collision_rect.h
        return (
                a_x < b_x + b_w and
                a_x + a_w > b_x and
                a_y < b_y + b_h and
                a_y + a_h > b_y
            )

    def kill(self) -> None:
        """
        Removes affiliation all SpriteGroup objects registered.
        """
        for group in self.__sprite_groups__:
            if self in group.sprites:
                group.sprites.remove(self)
        self.__sprite_groups__ = []


class MovingSprite(CustomSprite):
    """
    Sprite class in charge of the display and movement of the sprites with
    movement capacities.

    Parameters
    ----------
    x: float
        Sprite's position in the screen's x axis.
    y: float
        Sprite's position in the screen's y axis.
    gh_type: int
        Type of ghost sprite to be displayed. Ranges from 0 to 3.
    cooldown: float
        Animation cooldown value. Determines how fast the animation frames
        of a sprite are going to be changed.
    speed: float
        Determines the speed of the in-screen movement of the sprite.

    Attributes
    ----------
    grid: list[list[int]]
        Maze grid data.
    screen_grid: list[list[tuple[float, float]]]
        Coordinates of all grid cell centers in the screen.
    current_cell: list[int]
        Current cell occupied inside the maze grid.
    moving_up: bool
        Indicates if the sprite is moving up.
    moving_down: bool
        Indicates if the sprite is moving down.
    moving_left: bool
        Indicates if the sprite is moving left.
    moving_right: bool
        Indicates if the sprite is moving right.
    """
    def __init__(self,
                 x: float,
                 y: float,
                 scale: float = 1,
                 cooldown: float = 0.06,
                 speed: float = 330) -> None:
        super().__init__(x, y, scale, cooldown)
        self.speed: float = speed
        self.grid: list[list[int]]
        self.screen_grid: list[list[tuple[float, float]]]
        self.current_cell: list[int] = [0, 0]
        self.moving_up: bool = False
        self.moving_down: bool = False
        self.moving_left: bool = False
        self.moving_right: bool = False

    def update_grid_screen(self, grid: list[list[int]],
                           screen_grid: list[list[tuple[float,
                                                        float]]]) -> None:
        """
        Stores the information about the maze grid as object's attributes.
        """
        self.grid = grid
        self.screen_grid = screen_grid
        self.cell_size = self.screen_grid[0][1][0] - self.screen_grid[0][0][0]

    def its_moving(self) -> bool:
        """
        Indicates if one the moving attrites is set to True

        Returns
        -------
        True if one the moving attrites is set to True, False in not.
        """
        return (self.moving_up or self.moving_down or
                self.moving_left or self.moving_right)

    def change_direction(self, key: str) -> None:
        """
        Changes the attributes that indicate the movement direction
        for the update method.

        Paremeters
        ----------
        key: str
            The direction ('up', 'down', 'left' or 'right') that will be set
            to True.
        """
        dirs = ['right', 'left', 'up', 'down']
        for dir in dirs:
            val = (key == dir)
            setattr(self, f'moving_{dir}', val)

    def stop_movement(self) -> None:
        """
        Sets the movement attributes to False
        """
        dirs = ['right', 'left', 'up', 'down']
        for dir in dirs:
            setattr(self, f'moving_{dir}', False)

    def update_current_cell(self) -> None:
        """
        Updates the sprite's position in the grid
        based on its on-screen position.
        """
        origin_x, origin_y = self.screen_grid[0][0]
        col = round((self.pos[0] - origin_x) / self.cell_size)
        row = round((self.pos[1] - origin_y) / self.cell_size)
        col = max(0, min(col, len(self.grid[0]) - 1))
        row = max(0, min(row, len(self.grid) - 1))
        self.current_cell = [col, row]

    def get_current_center(self) -> tuple[float, float]:
        """
        Gets the current cell's central on-screen position.

        Returns
        -------
        Cells center x and y screen coordinates.
        """
        x, y = self.current_cell
        return self.screen_grid[y][x]

    def snap_to_cell(self) -> None:
        """
        Snaps the sprite's position on-screen to the center of
        its current cell.
        """
        self.update_current_cell()
        x, y = self.current_cell
        cx, cy = self.screen_grid[y][x]
        self.pos[0] = cx
        self.pos[1] = cy
        self.get_image_rect()

    def can_it_move(self, key: str) -> bool:
        """
        Determines if the sprite can move in the 'key' direction based on
        its current cell (position inside the grid).

        Parameters
        ----------
        key: str
            The direction ('up', 'down', 'left' or 'right')
            that will be evaluated.

        Returns
        -------
        True if movement towards the 'key' direction is possible, False if not.
        """
        x, y = self.current_cell
        directions = {'up': 1, 'right': 2, 'down': 4, 'left': 8}
        return directions[key] & self.grid[y][x] == 0

    def rect_update_not_free(self, dx: float, dy: float) -> None:
        """
        Updates the sprite's Rect position when there are movement
        restriction based on a maze grid and the sprite's position
        inside it. Restricts or prevents position modification by
        dx and dy parameters if necessary.

        Parameters
        ----------
        dx: float
            Potential modification of the Rect's x position on-screen.
        dy: float
            Potential modification of the Rect's y position on-screen.
        """

        self.update_current_cell()
        if self.moving_left and self.can_it_move('left'):
            self.pos[0] += dx
        if self.moving_right and self.can_it_move('right'):
            self.pos[0] += dx
        if self.moving_up and self.can_it_move('up'):
            self.pos[1] += dy
        if self.moving_down and self.can_it_move('down'):
            self.pos[1] += dy
        self.get_image_rect()

    def move_rect(self, dt: float) -> None:
        """
        Determines the magnitud of the Rect's position change in the
        x and y axis. Meant to be used inside update method to update
        the sprite's position.

        Parameters
        ----------
        dt: float
            Delta time, time that has passes since the last
            measurement.
        """
        dx, dy = 0.0, 0.0
        if self.moving_left:
            dx -= self.speed * dt
        if self.moving_right:
            dx += self.speed * dt
        if self.moving_up:
            dy -= self.speed * dt
        if self.moving_down:
            dy += self.speed * dt
        self.rect_update_not_free(dx, dy)


class SpriteGroup:
    """
    Own implementation of pygame.sprite.Group because it doesn't have a
    MLX equivalent and the built-in function is not allowed.

    It stores a list of sprites and allows to use common functions in the
    sprites in one call.

    Attributes
    ----------
    sprites
        List of CustomSprite objects that belong to the group.
    """
    def __init__(self) -> None:
        self.sprites: list[CustomSprite] = []

    def add(self, sprite: CustomSprite) -> None:
        """
        Adds the sprite to the sprites attribute list.
        Adds the SpriteGroup to the sprite's list of
        affiliated groups.

        Parameters
        ----------
        sprite: CustomSprite
            sprite to be added to the list.
        """
        self.sprites.append(sprite)
        sprite.__sprite_groups__.append(self)

    def draw(self, screen: Surface) -> None:
        """
        Calls the draw method of all the sprites stored
        in the sprite list.

        Parameters
        ----------
        screen: Surface
            Screen surface where the sprite will be displayed.
        """
        for spr in self.sprites.copy():
            if hasattr(spr, 'draw'):
                spr.draw(screen)

    def update(self, dt: float) -> None:
        """
        Calls the update method of all the sprites stored
        in the sprite list.

        Parameters
        ----------
        dt: float
            Delta time, time that has passes since the last
            measurement.
        """
        for spr in self.sprites.copy():
            if hasattr(spr, 'update'):
                spr.update(dt)

    def update_grid_screen(self, grid: list[list[int]],
                           screen_grid: list[list[tuple[float,
                                                        float]]]) -> None:
        """
        Calls the update_grid_screen method of all the sprites stored
        in the sprite list.

        Parameters
        ----------
        grid: list[list[int]]
            Maze grid data.
        screen_grid: list[list[tuple[float, float]]]
            Coordinates of all grid cell centers in the screen.
        """
        for spr in self.sprites:
            if isinstance(spr, MovingSprite):
                spr.update_grid_screen(grid, screen_grid)

    def extend(self, sprite_group: 'SpriteGroup') -> None:
        """
        Add the affiliated sprite list of another group to the
        own.

        Parameters
        ----------
        sprite_group: SpriteGroup
            Another SpriteGroup object to extract a list of sprites.
        """
        for spr in sprite_group.sprites:
            self.add(spr)

    def clear(self) -> None:
        """
        Calls the clear method of all the sprites stored
        in the sprite list.
        """
        self.sprites.clear()
