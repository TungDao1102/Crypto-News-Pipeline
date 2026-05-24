import logging
import re

logger = logging.getLogger(__name__)

CASHTAG_PRIORITY = ["BTC", "ETH", "SOL", "ARB", "OP", "MATIC", "AVAX", "ATOM"]
MAX_CASHTAGS = 3
MAX_HASHTAGS = 5

HASHTAG_MAP: dict[str, str] = {
    "airdrop": "#Airdrop",
    "testnet": "#Testnet",
    "retroactive": "#Retroactive",
    "defi": "#DeFi",
    "nft": "#NFT",
    "gamefi": "#GameFi",
    "layer2": "#Layer2",
    "staking": "#Staking",
    "macro": "#Macro",
    "news": "#CryptoNews",
    "trading": "#Trading",
    "meme": "#MemeCoin",
    "rwa": "#RWA",
    "infra": "#Infrastructure",
    "security": "#Security",
    "regulation": "#Regulation",
}

TAG_LINE_PATTERN = re.compile(r"^[\s#\$A-Za-z0-9_]+$")


class TagInjector:

    def strip_tags(self, content: str) -> str:
        lines = content.split("\n")
        clean = [
            line for line in lines
            if not TAG_LINE_PATTERN.match(line.strip())
            or not self._looks_like_tag_block(line.strip())
        ]
        return "\n".join(clean).strip()

    def _looks_like_tag_block(self, line: str) -> bool:
        tokens = line.strip().split()
        tag_count = sum(1 for t in tokens if t.startswith("#") or t.startswith("$"))
        return tag_count >= 2 and tag_count == len(tokens)

    def select_cashtags(self, content_tags: list[str]) -> list[str]:
        matched = [t for t in CASHTAG_PRIORITY if t.lower() in [ct.lower() for ct in content_tags]]
        return [f"${t}" for t in matched[:MAX_CASHTAGS]]

    def select_hashtags(self, content_tags: list[str]) -> list[str]:
        matched = []
        content_lower = [t.lower() for t in content_tags]
        for key, value in HASHTAG_MAP.items():
            if key in content_lower:
                matched.append(value)
            if len(matched) >= MAX_HASHTAGS:
                break
        return matched

    def inject(self, content: str, content_tags: list[str], max_length: int = 4096) -> str:
        cleaned = self.strip_tags(content)

        cashtags = self.select_cashtags(content_tags)
        hashtags = self.select_hashtags(content_tags)

        tag_line = " ".join(cashtags + hashtags)
        if not tag_line:
            return cleaned

        result = f"{cleaned}\n\n{tag_line}"

        if len(result) > max_length:
            excess = len(result) - max_length
            if len(tag_line) >= excess + 10:
                result = result[:max_length]
            else:
                trimmed = cleaned[:max_length - len(tag_line) - 2]
                result = f"{trimmed}\n\n{tag_line}"

        logger.debug(
            "Injector: %d cashtags, %d hashtags → %d chars",
            len(cashtags), len(hashtags), len(result),
        )
        return result
