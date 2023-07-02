from .cli.main import app
from .config import (
    DEFAULT_SAVE_PATH,
    DEFAULT_GENERATED_FONT_PATH,
    DEFAULT_ASSETS_PATH,
    BASE_EMOJI_FONT_PATH,
)

# Create default file saving directories if they doesn't already exist
DEFAULT_SAVE_PATH.mkdir(parents=True, exist_ok=True)
DEFAULT_ASSETS_PATH.mkdir(parents=True, exist_ok=True)
DEFAULT_GENERATED_FONT_PATH.parent.mkdir(parents=True, exist_ok=True)
BASE_EMOJI_FONT_PATH.mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    app()
