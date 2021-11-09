import time
from typing import ClassVar


class ImageGeneratorGAN:
    START_DELAY: ClassVar[int] = 1
    GENERATION_DELAY: ClassVar[int] = 15
    DEFAULT_RESULT: str = "image.png"

    def __init__(self):
        time.sleep(self.START_DELAY)

    def generate_image(self, text: str) -> str:
        time.sleep(self.GENERATION_DELAY)
        return self.DEFAULT_RESULT
