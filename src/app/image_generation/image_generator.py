import time
from typing import ClassVar


class ImageGeneratorGAN:
    START_DELAY: ClassVar[int] = 60
    GENERATION_DELAY: ClassVar[int] = 30
    DEFAULT_RESULT: str = "image.png"

    def __init__(self):
        self.is_ready = False
        self.start()

    def generate_image(self, text: str) -> str:
        time.sleep(self.GENERATION_DELAY)
        return self.DEFAULT_RESULT

    def start(self):
        time.sleep(self.START_DELAY)
        self.is_ready = True
