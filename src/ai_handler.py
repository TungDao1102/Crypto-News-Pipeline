import asyncio
import json
import logging
import re
import time
from typing import Any

import httpx
from pydantic import BaseModel

from src.models import DraftContent, RawMessage

logger = logging.getLogger(__name__)

EMOJI_PATTERN = re.compile(
    "[\U0001F000-\U0010FFFF]"
)
CONTRACT_ADDRESS_PATTERN = re.compile(r"0x[a-fA-F0-9]{40}")
CODE_BLOCK_PATTERN = re.compile(r"```[\s\S]*?```")

PLACEHOLDER_TEMPLATE = "\x00PROTECTED_{}\x00"
_placeholder_counter = 0


def _next_placeholder() -> str:
    global _placeholder_counter
    _placeholder_counter += 1
    return PLACEHOLDER_TEMPLATE.format(_placeholder_counter)


BASE_TRANSLATE_SYSTEM = (
    "You are a professional crypto news Vietnamese translator.\n"
    "Your task is to translate the following English crypto news to Vietnamese.\n"
    "PRESERVE these English terms: Testnet, Mainnet, Mint, NFT, Faucet, Gas fee, "
    "Airdrop, Staking, Claim, Token, TGE, IDO, ICO, whitelist, KYC\n"
    "Output must be valid JSON ONLY with exactly 1 field: translated_text\n"
    "Vietnamese style guidelines:\n"
    "- Use short, punchy sentences\n"
    "- Include emojis where appropriate\n"
    "- Start with a hook that creates urgency or excitement\n"
    "- Use community terms: 'san airdrop', 'farm testnet', 'claim token'\n"
    "- Natural and conversational, NOT overly polite\n"
    "- Each paragraph max 3 lines (mobile-friendly)\n"
    "- NEVER include price predictions or financial advice\n"
    "- NEVER promote scams or suspicious links"
)

BASE_REWRITE_SYSTEM = (
    "You are a professional Vietnamese crypto content creator.\n"
    "Your task is to rewrite the following translated Vietnamese crypto content "
    "into engaging posts for Telegram and Binance Square.\n"
    "Output must be valid JSON ONLY with exactly 3 fields: "
    "title_vn, telegram_markdown, binance_square_markdown\n"
    "Rules:\n"
    "- Create a catchy, urgent title for title_vn\n"
    "- Telegram post: shorter, more casual, use emojis and line breaks\n"
    "- Binance Square post: slightly more formal but still engaging, include hashtags\n"
    "- End both posts with a clear call-to-action\n"
    "- NEVER include price predictions or financial advice\n"
    "- NEVER promote scams or suspicious links"
)


def _make_airdrop_translate() -> str:
    return BASE_TRANSLATE_SYSTEM + (
        "\n\nTone: URGENT and FOMO. Emphasize deadlines, "
        "limited time opportunities, and 'Co hoi cuoi cung' (last chance). "
        "Use phrases like 'Nhanh tay keo het', 'Dung bo lo', 'Co hoi sieu hiem'."
    )


def _make_airdrop_rewrite() -> str:
    return BASE_REWRITE_SYSTEM + (
        "\n\nTone: Create urgency and excitement. "
        "Mention how much potential value, deadline countdown, "
        "and step-by-step claim instructions. "
        "Use 'Co hoi cuoi cung', 'Nhanh tay keo het', 'Dung bo lo'."
    )


def _make_testnet_translate() -> str:
    return BASE_TRANSLATE_SYSTEM + (
        "\n\nTone: INSTRUCTIONAL and DETAILED. Emphasize step-by-step guide. "
        "Keep technical accuracy. Clearly separate each step. "
        "Include important warnings like 'Can MetaMask', 'Can du ETH lam gas'."
    )


def _make_testnet_rewrite() -> str:
    return BASE_REWRITE_SYSTEM + (
        "\n\nTone: Clear, instructional, step-by-step guide. "
        "Break down into numbered steps for Telegram. "
        "Include requirements section (what user needs). "
        "Add warnings where necessary."
    )


def _make_macro_translate() -> str:
    return BASE_TRANSLATE_SYSTEM + (
        "\n\nTone: ANALYTICAL and PROFESSIONAL. Focus on market context, "
        "project fundamentals, and strategic significance. "
        "Use terms like 'phan tich', 'nhan dinh thi truong', 'trien vong'."
    )


def _make_macro_rewrite() -> str:
    return BASE_REWRITE_SYSTEM + (
        "\n\nTone: Analytical but accessible. "
        "Provide market context and strategic insights. "
        "Use 'Theo phan tich', 'Nhin chung', 'Trien vong dai han'."
        "Keep engaging but more measured than airdrop posts."
    )


def _make_defi_translate() -> str:
    return BASE_TRANSLATE_SYSTEM + (
        "\n\nTone: TECHNICAL and PRECISE. Focus on protocol mechanics, "
        "TVL, tokenomics, and technical details. "
        "Preserve DeFi terminology: TVL, APY, LP, DEX, bridge, liquid staking, "
        "yield farming, impermanent loss."
    )


def _make_defi_rewrite() -> str:
    return BASE_REWRITE_SYSTEM + (
        "\n\nTone: Protocol-focused and technically accurate. "
        "Explain DeFi mechanics in an accessible way for Vietnamese community. "
        "Use terms like 'thanh khoan', 'sine loi', 'stake token'. "
        "Include relevant metrics (TVL, APY, etc.) if available."
    )


PROMPT_REGISTRY: dict[str, dict[str, str]] = {
    "default": {
        "translate_system": BASE_TRANSLATE_SYSTEM,
        "rewrite_system": BASE_REWRITE_SYSTEM,
        "user_template": "Translate this crypto news to Vietnamese:\n\n{raw_text}\n\n"
        'Output ONLY valid JSON: {{"translated_text": "..."}}',
    },
    "airdrop": {
        "translate_system": _make_airdrop_translate(),
        "rewrite_system": _make_airdrop_rewrite(),
        "user_template": "Translate this airdrop news to Vietnamese urgently:\n\n{raw_text}\n\n"
        'Output ONLY valid JSON: {{"translated_text": "..."}}',
    },
    "testnet": {
        "translate_system": _make_testnet_translate(),
        "rewrite_system": _make_testnet_rewrite(),
        "user_template": "Translate this testnet guide to Vietnamese, step by step:\n\n{raw_text}\n\n"
        'Output ONLY valid JSON: {{"translated_text": "..."}}',
    },
    "macro": {
        "translate_system": _make_macro_translate(),
        "rewrite_system": _make_macro_rewrite(),
        "user_template": "Translate this crypto market analysis to Vietnamese:\n\n{raw_text}\n\n"
        'Output ONLY valid JSON: {{"translated_text": "..."}}',
    },
    "defi": {
        "translate_system": _make_defi_translate(),
        "rewrite_system": _make_defi_rewrite(),
        "user_template": "Translate this DeFi protocol news to Vietnamese:\n\n{raw_text}\n\n"
        'Output ONLY valid JSON: {{"translated_text": "..."}}',
    },
}


def prompt_for_tags(tags: list[str]) -> dict[str, str]:
    priority = ["airdrop", "testnet", "macro", "defi", "default"]
    for tag in priority:
        if tag in tags:
            return PROMPT_REGISTRY[tag]
    return PROMPT_REGISTRY["default"]


class AllModelsExhausted(Exception):
    pass


FALLBACK_MODELS = [
    "deepseek-chat:free",
    "meta-llama/llama-3-70b-instruct:free",
    "qwen/qwen-2.5-72b-instruct:free",
]

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterClient:
    def __init__(self, api_key: str, http_client: httpx.AsyncClient) -> None:
        self.api_key = api_key
        self.http_client = http_client

    async def call(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.6,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        response = await self.http_client.post(
            OPENROUTER_URL,
            headers=headers,
            json=body,
        )
        response.raise_for_status()
        return response.json()

    async def call_with_fallback(
        self,
        system_prompt: str,
        user_content: str,
        temperature: float = 0.6,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        last_exception: Exception | None = None
        for model in FALLBACK_MODELS:
            try:
                logger.info("Calling OpenRouter model: %s", model)
                result = await self.call(model, messages, temperature, max_tokens)
                logger.info("OpenRouter model %s succeeded", model)
                return result
            except httpx.TimeoutException:
                logger.warning("Timeout on model %s, trying next", model)
                last_exception = httpx.TimeoutException("Timeout")
            except httpx.HTTPStatusError as e:
                logger.warning("HTTP error %s on model %s, trying next", e.response.status_code, model)
                last_exception = e
            except json.JSONDecodeError as e:
                logger.warning("JSON decode error on model %s, trying next", model)
                last_exception = e
        raise AllModelsExhausted(
            f"All models exhausted for this request. Last error: {last_exception}"
        ) from last_exception

    async def call_structured(
        self,
        system_prompt: str,
        user_content: str,
        response_model: type[BaseModel],
        temperature: float = 0.6,
    ) -> tuple[BaseModel | None, bool]:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        last_exception: Exception | None = None
        for idx, model in enumerate(FALLBACK_MODELS):
            try:
                logger.info("Calling OpenRouter (structured) model: %s", model)
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
                body: dict[str, Any] = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": 2048,
                    "response_format": {"type": "json_object"},
                }
                response = await self.http_client.post(
                    OPENROUTER_URL,
                    headers=headers,
                    json=body,
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                parsed = response_model.model_validate_json(content)
                logger.info("OpenRouter model %s structured result validated", model)
                return parsed, idx > 0
            except httpx.TimeoutException:
                logger.warning("Timeout on model %s, trying next", model)
                last_exception = httpx.TimeoutException("Timeout")
            except httpx.HTTPStatusError as e:
                logger.warning("HTTP error %s on model %s, trying next", e.response.status_code, model)
                last_exception = e
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                logger.warning("Invalid response on model %s: %s, trying next", model, e)
                last_exception = e
            except Exception as e:
                logger.warning("Unexpected error on model %s: %s, trying next", model, e)
                last_exception = e
        raise AllModelsExhausted(
            f"All models exhausted for structured request. Last error: {last_exception}"
        ) from last_exception


class TextPreprocessor:
    def preprocess(self, raw_text: str) -> str:
        placeholders: dict[str, str] = {}

        def protect(pattern: re.Pattern, text: str) -> str:
            def _replacer(m: re.Match) -> str:
                placeholder = _next_placeholder()
                placeholders[placeholder] = m.group(0)
                return placeholder
            return pattern.sub(_replacer, text)

        text = protect(CODE_BLOCK_PATTERN, raw_text)
        text = protect(CONTRACT_ADDRESS_PATTERN, text)

        text = EMOJI_PATTERN.sub("", text)

        text = re.sub(r"\s+", " ", text).strip()

        for placeholder, original in placeholders.items():
            text = text.replace(placeholder, original)

        return text


class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float) -> None:
        self.capacity = capacity
        self.tokens = float(capacity)
        self.refill_rate = refill_rate
        self._last_refill = time.monotonic()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self._last_refill = now

    async def acquire(self, tokens: int = 1) -> None:
        while True:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return
            await asyncio.sleep((tokens - self.tokens) / self.refill_rate)


class TranslatedText(BaseModel):
    translated_text: str


class AIConsumer:
    def __init__(
        self,
        raw_queue: asyncio.Queue[RawMessage],
        result_queue: asyncio.Queue[DraftContent],
        channel_tags: dict[str, list[str]],
        rate_limiter: TokenBucket,
        http_client: httpx.AsyncClient,
        api_key: str,
        worker_count: int = 3,
    ) -> None:
        self.raw_queue = raw_queue
        self.result_queue = result_queue
        self.channel_tags = channel_tags
        self.rate_limiter = rate_limiter
        self.http_client = http_client
        self.api_key = api_key
        self.worker_count = worker_count
        self._workers: list[asyncio.Task[None]] = []
        self._shutdown = asyncio.Event()
        self._preprocessor = TextPreprocessor()
        self._openrouter = OpenRouterClient(api_key, http_client)

    async def start(self) -> None:
        self._workers = [
            asyncio.create_task(self._worker(i))
            for i in range(self.worker_count)
        ]
        logger.info("AI consumer started with %d worker(s)", self.worker_count)
        await asyncio.gather(*self._workers)

    async def shutdown(self) -> None:
        self._shutdown.set()
        for w in self._workers:
            w.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        logger.info("AI consumer shut down")

    async def _worker(self, worker_id: int) -> None:
        while not self._shutdown.is_set():
            qsize = self.raw_queue.qsize()
            if qsize > 10:
                logger.warning(
                    "Backpressure: raw_queue size=%d, processing rate may be insufficient",
                    qsize,
                )
            msg = await self.raw_queue.get()
            try:
                await self.rate_limiter.acquire()
                draft = await self._process_message(msg)
                if draft:
                    await self.result_queue.put(draft)
            except Exception:
                logger.exception(
                    "Worker %d: unexpected error processing msg %s",
                    worker_id,
                    msg.message_id,
                )
            finally:
                self.raw_queue.task_done()

    async def _process_message(self, msg: RawMessage) -> DraftContent | None:
        tags = self.channel_tags.get(msg.source_channel, [])
        prompts = prompt_for_tags(tags)

        preprocessed = self._preprocessor.preprocess(msg.raw_text)
        if not preprocessed.strip():
            logger.info("Message %d from %s: empty after preprocessing, skipping", msg.message_id, msg.source_channel)
            return None

        try:
            await self.rate_limiter.acquire()
            translate_result, used_fallback = await self._openrouter.call_structured(
                system_prompt=prompts["translate_system"],
                user_content=prompts["user_template"].format(raw_text=preprocessed),
                response_model=TranslatedText,
                temperature=0.6,
            )
            if translate_result is None:
                logger.error("Message %d: all models exhausted for translation, skipping", msg.message_id)
                return None
        except AllModelsExhausted:
            logger.error("Message %d from %s: all models exhausted for translation", msg.message_id, msg.source_channel)
            return None

        try:
            await self.rate_limiter.acquire()
            rewrite_prompt = (
                f"Rewrite this Vietnamese crypto content for Telegram and Binance Square:\n\n"
                f"{translate_result.translated_text}\n\n"
                f"Output ONLY valid JSON with fields: title_vn, telegram_markdown, binance_square_markdown"
            )
            rewrite_result, rewrite_used_fallback = await self._openrouter.call_structured(
                system_prompt=prompts["rewrite_system"],
                user_content=rewrite_prompt,
                response_model=DraftContent,
                temperature=0.7,
            )
            if rewrite_result is None:
                logger.warning("Message %d: rewrite failed, using translated text as draft", msg.message_id)
                return DraftContent(
                    title_vn=translate_result.translated_text[:100],
                    telegram_markdown=translate_result.translated_text,
                    binance_square_markdown=translate_result.translated_text,
                    status="pending",
                    tags=tags,
                    used_fallback=used_fallback,
                )
        except AllModelsExhausted:
            logger.warning(
                "Message %d from %s: all models exhausted for rewrite, using translated text",
                msg.message_id,
                msg.source_channel,
            )
            return DraftContent(
                title_vn=translate_result.translated_text[:100],
                telegram_markdown=translate_result.translated_text,
                binance_square_markdown=translate_result.translated_text,
                status="pending",
                tags=tags,
                used_fallback=True,
            )

        rewrite_result.tags = tags
        rewrite_result.status = "pending"
        rewrite_result.used_fallback = used_fallback or rewrite_used_fallback
        logger.info("Message %d from %s: successfully processed", msg.message_id, msg.source_channel)
        return rewrite_result
