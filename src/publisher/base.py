import abc
from dataclasses import dataclass


@dataclass
class PublisherResult:
    platform: str
    success: bool
    url: str | None = None
    error: str | None = None


class BasePublisher(abc.ABC):

    @abc.abstractmethod
    async def publish(self, content: str) -> PublisherResult:
        ...

    @abc.abstractmethod
    async def close(self) -> None:
        ...
