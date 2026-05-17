import asyncio
import logging
from typing import Literal

logger = logging.getLogger(__name__)

SystemMode = Literal["AUTO", "MANUAL"]


class SystemState:
    _instance: "SystemState | None" = None

    def __new__(cls) -> "SystemState":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._mode: SystemMode = "MANUAL"
        self._lock = asyncio.Lock()
        self._drafts_processed_today: int = 0
        self._initialized = True

    async def set_mode(self, mode: SystemMode) -> None:
        async with self._lock:
            self._mode = mode
            logger.info("SYSTEM_MODE set to %s", mode)

    async def get_mode(self) -> SystemMode:
        async with self._lock:
            return self._mode

    async def increment_processed(self) -> None:
        async with self._lock:
            self._drafts_processed_today += 1

    async def get_processed_count(self) -> int:
        async with self._lock:
            return self._drafts_processed_today
