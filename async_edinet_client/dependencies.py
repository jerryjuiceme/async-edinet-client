from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging

from googletrans import Translator


logger = logging.getLogger(__name__)


class BaseTranslator(ABC):
    @abstractmethod
    async def translate(self, input_text: str) -> str:
        pass


class GoogleTranslator(BaseTranslator):

    async def translate(self, input_text: str) -> str:
        try:
            async with self._get_translator() as translator:
                result = await translator.translate(input_text, dest="en")
                logger.debug("Abstract translated successfully")
                return result.text
        except Exception:
            logger.warning("Description translation failed, returning the same text")
            return "Not translated: " + input_text

    @asynccontextmanager
    async def _get_translator(self) -> AsyncGenerator[Translator, None]:
        async with Translator() as translator:
            yield translator


class BypassTranslator(BaseTranslator):
    async def translate(self, input_text: str) -> str:
        return "translation disabled: " + input_text


def get_translator(condition: bool) -> BaseTranslator:
    """
    A function to get the translator controller

    Args:
        condition (bool): if true, uses google translator

    Returns:
        BaseTranslator: the translator controller
    """
    if condition:
        return GoogleTranslator()
    else:
        return BypassTranslator()
