import logging
from googletrans import Translator

logger = logging.getLogger()

class TextTranslator:
    def __init__(self):
        self.translator = Translator()

    def translate_to_en(self, text: str) -> str:
        try:
            lang = self.translator.detect(text).lang
            if lang == "ru":
                text = self.translator.translate(text, origin="ru", dest="en").text
        except Exception as e:
            logger.info(e)
        logger.info(f"Translated text: {text}")
        return text
