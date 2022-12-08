import pathlib
from typing import Union

PathLike = Union[pathlib.Path, str]

BASE_PATH = pathlib.Path(__file__).resolve().parents[3] # Race prediction
DAT_PATH = BASE_PATH / "Data"
LINKEDIN_PATH = DAT_PATH / "LinkedIn"
OUTPUT_DAT_PATH = LINKEDIN_PATH / "Data"
IMAGE_PATH = BASE_PATH / "Images"
