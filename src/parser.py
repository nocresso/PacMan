from pydantic import (BaseModel, Field, model_validator,
                      field_validator, ValidationInfo,
                      ValidationError)
from typing import List, Tuple, Dict, Any
from pathlib import Path
import json
import logging


logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

LIMITS: Dict[str, Tuple[int, int]] = {
    "seed": (1, 1000),
    "lives": (1, 100),
    "pacgums": (1, 500),
    "points_per_pacgum": (1, 500),
    "points_per_super_pacgum": (1, 500),
    "points_per_ghost": (1, 500),
    "level_max_time": (1, 10000),
}


class ConfigurationError(Exception):
    """
    Custom exception for invalid game configuration errors.
    """
    def __init__(self, extra_info: str = ""):
        self.base_msg = "Invalid configuration"
        if extra_info:
            self.full_msg = f"{self.base_msg}, {extra_info}"
        else:
            self.full_msg = self.base_msg
        super().__init__(self.full_msg)


class LevelConfig(BaseModel):
    """
    Pydantic model for a single maze level's dimensions.
    """
    width: int = Field(ge=15, le=25, default=15)
    height: int = Field(ge=15, le=20, default=15)


class GameConfiguration(BaseModel):
    """
    Pydantic model that validates all the game configuration parameters.
    """
    highscore_filename: str = Field(default="scores.json")
    seed: int = Field(gt=0, le=1000, default=42)
    lives: int = Field(gt=0, le=100, default=3)
    pacgums: int = Field(gt=0, le=500, default=100)
    points_per_pacgum: int = Field(gt=0, le=500, default=10)
    points_per_super_pacgum: int = Field(gt=0, le=500, default=50)
    points_per_ghost: int = Field(gt=0, le=500, default=200)
    level_max_time: int = Field(gt=0, le=10000, default=90)
    level_nb: int = Field(ge=10, le=20, default=10)
    levels: List[LevelConfig] = Field(default_factory=list)

    @staticmethod
    def _clamp_dimension(value: Any, name: str, low: int, high: int) -> int:
        """
        Return a valid maze dimension: the default (the lower limit) when
        the value is not an integer, or the value clamped into [low, high].
        """
        if not isinstance(value, int) or isinstance(value, bool):
            logger.warning(
                f"level '{name}' invalid ({value!r}), using {low} instead")
            return low
        clamped = max(low, min(value, high))
        if clamped != value:
            logger.warning(
                f"level '{name}' out of range ({value!r}), "
                f"using {clamped} instead")
        return clamped

    @field_validator('levels', mode="before")
    @classmethod
    def clamp_levels(cls, value: Any, info: ValidationInfo) -> Any:
        """
        Validate the raw 'levels' value before Pydantic builds the list
        of LevelConfig objects, discarding anything that is not a
        well-formed level.

        If the value is not a list, it is replaced with an empty list
        (which `expand_levels` will later auto-fill). If it is a list,
        each item is checked against `LevelConfig`; items that fail
        validation are discarded and only the valid ones are kept, so a
        single malformed level does not invalidate the whole file.
        """
        if info.field_name is None:
            return value
        if not isinstance(value, list):
            logger.warning(
                f"'{info.field_name}' invalid ({value!r}), "
                "using an empty list (will be auto-filled)"
            )
            return []

        clean_levels = []
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                logger.warning(
                    f"discarding invalid level at index {index} "
                    f"({item!r}): it is not an object"
                )
                continue
            clean_levels.append({
                "width": cls._clamp_dimension(item.get("width"),
                                              "width", 15, 25),
                "height": cls._clamp_dimension(item.get("height"),
                                               "height", 15, 20),
            })
        return clean_levels

    @model_validator(mode="after")
    def expand_levels(self) -> "GameConfiguration":
        """
        Ensure there are exactly `level_nb` levels once the whole
        configuration has been validated, generating any missing ones.
        """
        if not self.levels:
            self.levels = [LevelConfig()]

        while len(self.levels) < self.level_nb:
            last = self.levels[-1]
            new_width = last.width + 1
            new_height = last.height + 1

            new_level = LevelConfig(width=min(25, new_width),
                                    height=min(20, new_height))
            self.levels.append(new_level)
        return self

    @field_validator('highscore_filename', mode="before")
    @classmethod
    def clamp_highscore_name(cls, value: Any, info: ValidationInfo) -> Any:
        """
        Validate the raw 'highscore_filename' value before Pydantic's
        own type checking, falling back to the field's default when it
        is not a non-empty string.
        """
        if info.field_name is None:
            return value
        default = cls.model_fields[info.field_name].default
        if not isinstance(value, str) or value == "":
            logger.warning(
                f"'{info.field_name}' invalid ({value!r}),"
                f" using default value {default} instead"
            )
            return default
        return value

    @field_validator('seed', 'lives', 'pacgums', 'points_per_pacgum',
                     'points_per_super_pacgum', 'points_per_ghost',
                     'level_max_time', mode="before")
    @classmethod
    def clamp_positive_int(cls, value: Any, info: ValidationInfo) -> Any:
        """
        Validate the raw value of an integer configuration field before
        Pydantic's own type checking, falling back to that field's
        default when it is not an integer inside its allowed range.
        """
        if info.field_name is None:
            return value
        default = cls.model_fields[info.field_name].default
        low, high = LIMITS[info.field_name]
        if (not isinstance(value, int) or isinstance(value, bool)
                or not low <= value <= high):
            logger.warning(
                f"'{info.field_name}' invalid ({value!r}), "
                f"must be an integer between {low} and {high}, "
                f"using default value {default} instead"
            )
            return default
        return value

    @field_validator('level_nb', mode="before")
    @classmethod
    def clamp_level_nb(cls, value: Any, info: ValidationInfo) -> Any:
        """
        Validate the raw 'level_nb' value before Pydantic's own type
        checking, falling back to the field's default when it is not an
        integer of at least 10.
        """
        if info.field_name is None:
            return value
        default = cls.model_fields[info.field_name].default
        if (not isinstance(value, int) or isinstance(value, bool) or
                value < 10 or value > 20):
            logger.warning(
                f"'{info.field_name}' invalid ({value!r}),"
                f" using default value {default} instead"
            )
            return default
        return value


def _reject_duplicate_keys(data: List[Tuple[str, Any]]) -> Dict[str, Any]:
    """
    Function to check duplicates.
    """
    clean_data: Dict[str, Any] = {}
    for key, value in data:
        if key in clean_data:
            raise ConfigurationError(f"duplicate key '{key}'")
        clean_data[key] = value
    return clean_data


def check_config_file(file_path: str) -> Dict[str, Any]:
    """
    Validates the existence and format of the configuration
    file and returns clean data.
    """
    path = Path(file_path)

    if not path.exists():
        raise ConfigurationError(f"{file_path} does not exist")

    if not path.is_file():
        raise ConfigurationError(f"{file_path} is not a valid file")

    if path.suffix != ".json":
        raise ConfigurationError("configuration file needs to be .json")
    try:
        with open(path, "r", encoding="utf-8") as file:
            clean_lines = []
            lines = file.readlines()
            for line in lines:
                line = line.strip()
                if line.startswith("#") or not line:
                    continue
                clean_lines.append(line)
    except (OSError, UnicodeDecodeError) as e:
        raise ConfigurationError(f"cannot read {file_path}: {e}") from e
    clean_file = "\n".join(clean_lines)
    try:
        data = json.loads(clean_file,
                          object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as e:
        raise ConfigurationError(f"invalid JSON: {e}") from e
    except ValueError as e:
        raise ConfigurationError(f"invalid JSON value: {e}") from e
    if not isinstance(data, dict):
        raise ConfigurationError(
            f"expected a JSON object at the root, got '{type(data).__name__}'")
    return data


def load_config(file_path: str) -> GameConfiguration:
    """
    Reads and validates the config file and constructs the
    validated GameConfiguration.
    """
    data = check_config_file(file_path)
    try:
        return GameConfiguration(**data)
    except ValidationError as e:
        raise ConfigurationError("could not build "
                                 f"configuration: '{e}'") from e


def is_valid_entry(entry: Any) -> bool:
    """
    A valid entry is a dict with a name (1-10 letters, digits or spaces,
    not only spaces) and a score (integer >= 0).
    """
    if not isinstance(entry, dict):
        return False
    name = entry.get("name")
    score = entry.get("score")
    return (
        isinstance(name, str)
        and 0 < len(name.strip()) and len(name) <= 10
        and all(c.isascii() and (c.isalnum() or c == " ") for c in name)
        and isinstance(score, int) and not isinstance(score, bool)
        and score >= 0
    )
