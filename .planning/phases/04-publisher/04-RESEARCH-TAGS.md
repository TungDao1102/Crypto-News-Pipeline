# Phase 4: Publisher & Platform Integration — Cashtag & Hashtag Research

**Researched:** 2026-05-17
**Domain:** Crypto content formatting conventions for Telegram + Binance Square
**Confidence:** HIGH

---

## User Constraints (from CONTEXT.md)

### Locked Decisions (D-03)
- **Last-minute injector pattern** — strip existing tags from AI output, inject deterministically based on `DraftContent.tags` field + coin-to-cashtag mapping list. Clean separation: AI writes content, injector handles platform formatting compliance.
- Cashtag priority list per AI-SPEC §7.4: `$BTC`, `$ETH`, `$SOL`, `$ARB`, `$OP`, `$MATIC`, `$AVAX`, `$ATOM`

### the agent's Discretion (relevant to tags)
- Cashtag priority list — hardcoded in code vs config file
- Hashtag-to-tag mapping (e.g., `tags=["airdrop"]` → `#Airdrop`)

---

## 1. Cashtag Format on Binance Square

### Format: `$TICKER` (standard dollar-prefix)

**CONFIRMED** — Binance Square uses the standard industry cashtag convention `$TICKER` (e.g., `$BTC`, `$ETH`, `$SOL`, `$BNB`). This is documented consistently across multiple official Binance sources:

- Binance Write-to-Earn FAQ: *"Add a coin cashtag (e.g., $BTC) to improve navigation and clarity"* — [Source](https://www.binance.info/en/support/faq/detail/3f4940d27ff04748a13e0fc1d3f1598d)
- Binance Write-to-Earn announcement: *"When readers click any of coin cashtags (e.g., $BTC)"* — [Source](https://www.binance.info/en/support/announcement/detail/4b3e53810ef04d43b9d3b2216e18fb4b)
- Binance Square OpenAPI (bodyTextOnly supports hashtags, and cashtags work as plaintext in the same body) — [Source](https://github.com/binance/binance-skills-hub/blob/main/skills/binance/square-post/SKILL.md)

### Critical Finding: Maximum 3 Cashtags Per Post

**NEWLY DISCOVERED (CONFIRMED)** — The official Binance FAQ states:

> *"Please note: You can add a maximum of 3 coin cashtags in each post."*

[Source](https://www.binance.info/en/support/faq/detail/3f4940d27ff04748a13e0fc1d3f1598d)

This overrides the AI-SPEC §7.4 priority list behavior. The injector **MUST** enforce this limit.

### Cashtags Are Clickable → Power Write-to-Earn

When a reader clicks a cashtag on Binance Square:
1. Opens a price/asset detail page
2. If they trade within 1 minute, the post creator earns up to 50% trading fee commission
3. This is the core monetization mechanism — cashtags are not decorative, they're revenue drivers

**Implication:** Cashtag injection is not just formatting compliance — it directly enables Write-to-Earn monetization. The injector must get it right.

### Cashtag Case Sensitivity

Cashtags are NOT case-sensitive across the industry (per X/Twitter conventions): `$btc`, `$BTC`, `$Btc` all resolve. However, Binance Square convention observed is uppercase (`$BTC`, `$ETH`, `$SOL`). **Recommendation:** Use uppercase for consistency and to match the priority list format in AI-SPEC.

---

## 2. Hashtag Rendering on Telegram Channels

### Automatic Detection — No Parse Mode Required

**CONFIRMED** — Telegram Bot API automatically detects hashtags server-side as `MessageEntity` of type `"hashtag"`. This happens WITHOUT needing `parse_mode`.

From the official Bot API docs:
> *Type of the entity. Currently, can be "mention" (@username), "hashtag" (#hashtag), "cashtag" ($USD)*
> — [core.telegram.org/bots/api#messageentity](https://core.telegram.org/bots/api#messageentity)

**Key behavior:**
- Hashtags become clickable automatically — tapping searches the chat/channel for the tag
- No `parse_mode` required — works with plain text `send_message()`
- Format: `#hashtag` or `#hashtag@chatusername`
- Works identically in both channels and groups

### Telegram vs Binance Square Hashtag Behavior

| Platform | Detection | Clickable? | Search Scope |
|----------|-----------|------------|--------------|
| Telegram | Server-side auto-detect | ✅ Yes | Within the chat/channel |
| Binance Square | Server-side rendering engine | ✅ Yes | Across Binance Square |

### Telegram Cashtag Support

**CONFIRMED** — Telegram also recognizes `$USD` as a cashtag entity type:
> *"cashtag" ($USD or $USD@chatusername)* — [core.telegram.org/bots/api#messageentity](https://core.telegram.org/bots/api#messageentity)

However, clicking a Telegram cashtag does NOT link to trading/price data (unlike Binance Square or X/Twitter). On Telegram, it simply triggers a search for that ticker within the chat.

**Implication for this pipeline:** Cashtags on Telegram are visually highlighted but don't enable monetization. The primary value of cashtags is on Binance Square for Write-to-Earn.

---

## 3. Cashtag Rendering on Binance Square — Supported Format Details

### The `bodyTextOnly` Field Accepts Tags as Plain Text

**CONFIRMED** — The Binance Square OpenAPI's `bodyTextOnly` field accepts plain text that includes hashtags and cashtags. The platform's rendering engine auto-detects and converts them to interactive elements.

From the OpenAPI spec:
> *`bodyTextOnly` | string | Yes | Post content text (supports #hashtags)*

[Source](https://github.com/binance/binance-skills-hub/blob/main/skills/binance/square-post/SKILL.md)

**This means:** The injector simply appends the raw text `$BTC $ETH $SOL` to the content body, and Binance Square handles the rendering. No special encoding, API fields, or metadata needed.

### Important Constraint: "Do NOT auto-add hashtags during optimization"

The Binance Square skill documentation explicitly instructs:
> *"Do NOT auto-add hashtags (#xxx) during optimization — keep any hashtags the user wrote, but never add new ones."*

This applies to content *optimization* (reformatting user input), not to programmatic injection. Our pipeline's last-minute injector pattern (D-03) is the correct approach: AI writes content without tags, injector adds them deterministically.

### Cashtag Format Confirmed for Priority List

Per AI-SPEC §7.4 and confirmed by research:
```
$BTC  $ETH  $SOL  $ARB  $OP  $MATIC  $AVAX  $ATOM
```

All follow the standard `$TICKER` format with uppercase ticker.

---

## 4. Best Practices for Injecting Tags Into News Content

### Position: End of Content

Both Telegram and Binance Square conventions place tags at the **end** of the message, after a separator line. This is consistent with:
- AI-SPEC §7.3 (Telegram): `#Airdrop #Testnet #Retroactive #[TênDựÁn]` at bottom
- AI-SPEC §7.4 (Binance Square): Cashtags and hashtags after `---` separator and disclaimer

**Recommendation:** Append a blank line + tags at the end of the existing content body. Do not inject into the middle of the article.

### Format: Hashtags Then Cashtags

Observed pattern across Binance Square and Telegram:

```
#Airdrop #Testnet #Arbitrum

$BTC $ETH $ARB
```

Hashtags first, cashtags second. Each group on its own line.

### Count Limits (Critical)

| Tag Type | Platform | Max Allowed | Source |
|----------|----------|-------------|--------|
| Cashtags | Binance Square | **3** | [Binance FAQ](https://www.binance.info/en/support/faq/detail/3f4940d27ff04748a13e0fc1d3f1598d) |
| Cashtags | Telegram | No limit (but 3 is reasonable) | Bot API docs |
| Hashtags | Binance Square | **5** (per AI-SPEC §7.4) | AI-SPEC §7.4 |
| Hashtags | Telegram | No limit (keep reasonable) | Bot API docs |

**The AI-SPEC §7.4 priority list has 8 coins.** The injector MUST cap at 3 and either:
1. Use the first 3 that match `DraftContent.tags` from the priority list, or
2. Pick the top 3 by priority regardless of content match.

**Recommendation:** Use option 1 (match against tags found in content). Fall back to option 2 (top 3 by priority) if no tag match.

### Natural Integration

Binance Square guidance emphasizes natural use:
> *"Using cashtags naturally within the analysis and avoiding spammy overuse could be a critical factor in building trust among readers."*

However, since we use the **last-minute injector pattern** (tags appended at end, not woven into text), this is less of a concern. The tags serve their functional purpose (enabling Write-to-Earn) without disrupting readability.

### Tag Deduplication

The injector MUST:
1. Strip any existing tags from AI-generated content (per D-03)
2. De-duplicate: ensure no coin appears twice in cashtags
3. De-duplicate: ensure no hashtag appears twice

---

## 5. Character Limits for Tags

### Telegram: 1–4096 Characters (Total Message)

**CONFIRMED** — From Telegram Bot API `sendMessage` documentation:
> *`text` | string | Text of the message to be sent, 1-4096 characters after entities parsing.*

[Source](https://core.telegram.org/bots/api#sendmessage)

Tags are part of the message body, not extra. The injector must ensure the total content length (including appended tags) stays under 4096.

**Current AI-SPEC constraint:** `telegram_markdown` max 4000 chars (Pydantic model). This leaves 96 chars of headroom for tags — sufficient for the recommended tag block.

### Binance Square: "Content Length is Limited" (Error 20013)

**PARTIALLY CONFIRMED** — The exact max character count is NOT documented in the OpenAPI specification. The error code reference lists:

| Code | Description |
|------|-------------|
| 20013 | Content length is limited |

[Source](https://github.com/binance/binance-skills-hub/blob/main/skills/binance/square-post/SKILL.md)

**Practical constraints:**
- AI-SPEC §7.4 sets `binance_square_markdown` max at 4000 chars (Pydantic field validation)
- Binance Square recommends >500 characters for Write-to-Earn eligibility
- The 4000-char limit in AI-SPEC is a safe working bound (typical Binance Square articles run 800–2000 words ≈ 4000–10000 chars, but the API limit may be higher)

**Recommendation:** Keep content ≤4000 characters (AI-SPEC bound). If the API returns 20013, the error handling (D-04/D-06) will catch it.

### Tag Block Size Estimation

Estimated character cost of a tag block:
```
\n\n#Airdrop #Testnet #Arbitrum\n\n$BTC $ETH $ARB
```
≈ 45 characters. Negligible headroom impact on either platform.

---

## 6. Implementation Guidance

### Injector Algorithm (Pseudocode)

```text
FUNCTION inject_tags(content: str, tags: list[str], coin_tickers: list[str]) -> str:
    # Strip any pre-existing #hashtags or $cashtags from content (per D-03)
    content = strip_hashtags(content)
    content = strip_cashtags(content)
    
    # Generate hashtags from tags list
    # Use tag-to-hashtag mapping (e.g., "airdrop" -> "#Airdrop")
    hashtags = []
    FOR tag IN tags:
        mapped = hashtag_map.get(tag, f"#{tag.capitalize()}")
        IF mapped NOT IN hashtags:
            hashtags.append(mapped)
    # Cap at 5 hashtags
    hashtags = hashtags[:5]
    
    # Generate cashtags from priority list + content match
    cashtags = []
    FOR ticker IN PRIORITY_LIST:  # ["BTC", "ETH", "SOL", ...]
        IF ticker matches content OR ticker in tags:
            cashtags.append(f"${ticker}")
        IF len(cashtags) >= 3:  # Binance Square max
            BREAK
    
    # Append to content
    tag_block = ""
    IF hashtags:
        tag_block += "\n\n" + " ".join(hashtags)
    IF cashtags:
        tag_block += "\n\n" + " ".join(cashtags)
    
    RETURN content + tag_block
```

### Priority List with Top-3 Enforcement

```python
CASHTAG_PRIORITY = ["BTC", "ETH", "SOL", "ARB", "OP", "MATIC", "AVAX", "ATOM"]
MAX_CASHTAGS = 3
```

### Hashtag Mapping (the agent's Discretion)

```python
# Simple capitalization mapping
HASHTAG_MAP = {
    "airdrop": "#Airdrop",
    "testnet": "#Testnet", 
    "retroactive": "#Retroactive",
    "defi": "#DeFi",
    "nft": "#NFT",
    "gamefi": "#GameFi",
    "layer2": "#Layer2",
    "staking": "#Staking",
}
```

### Formatted Output Examples

**Telegram (with injected tags):**
```markdown
🚀 **Cơ hội Airdrop Arbitrum — Claim ngay!**

[Content body...]

⚠️ *Lưu ý: Hạn chót 30/05*

#Airdrop #Arbitrum #Layer2
```

**Binance Square (with injected tags):**
```markdown
## 🚀 Cơ hội Airdrop Arbitrum — Claim ngay!

[Content body...]

---

*Bài viết được tổng hợp và biên tập bởi [Channel Name]*

#Airdrop #Arbitrum #Layer2

$ARB $ETH $BTC
```

---

## Summary of Key Findings

| Finding | Confidence | Source | New vs. Known |
|---------|-----------|--------|---------------|
| Cashtag format = `$TICKER` (e.g. `$BTC`) | **CONFIRMED** | Binance FAQ, Write-to-Earn docs | Confirms AI-SPEC |
| **Max 3 cashtags per Binance Square post** | **CONFIRMED** | [Binance FAQ](https://www.binance.info/en/support/faq/detail/3f4940d27ff04748a13e0fc1d3f1598d) | **NEW — overrides AI-SPEC §7.4** |
| Telegram auto-detects hashtags (no parse_mode needed) | **CONFIRMED** | [core.telegram.org/bots/api](https://core.telegram.org/bots/api#messageentity) | Confirms known |
| Telegram also supports cashtag entity auto-detection | **CONFIRMED** | [core.telegram.org/bots/api](https://core.telegram.org/bots/api#messageentity) | **NEW — adds context** |
| Binance Square `bodyTextOnly` accepts tags as plain text | **CONFIRMED** | [Binance Skills Hub](https://github.com/binance/binance-skills-hub/blob/main/skills/binance/square-post/SKILL.md) | Confirms D-02 |
| Cashtags power Write-to-Earn monetization (click → trade → commission) | **CONFIRMED** | Binance FAQ | **NEW — strategic context** |
| Telegram message limit: 1-4096 chars | **CONFIRMED** | Telegram Bot API docs | Confirms AI-SPEC |
| Binance Square content length limit (error 20013) — exact max not documented | **INFERRED** | Binance Skills Hub error codes | Partially known |
| Hashtags on Binance Square: max 5 per post | **INFERRED** | AI-SPEC §7.4 | Known from spec |
| Position convention: tags at end of content, hashtags then cashtags | **CONFIRMED** | Observed across multiple Binance Square posts | Confirms AI-SPEC |

### What Changed vs. AI-SPEC

1. **AI-SPEC §7.4 lists 8 coins in priority list** — but Binance Square allows max **3** cashtags per post. The injector must cap at 3.

2. **AI-SPEC mentions separate `telegram_markdown` and `binance_square_markdown`** — but Telegram auto-detects both hashtags and cashtags without parse_mode, so tag injection is identical for both platforms. The injector can use a shared function.

3. **Cashtag priority list should be capped at 3** — if `DraftContent.tags` matches more than 3 from the priority list, only the top 3 matching should be used.

### Sources

**Primary (HIGH confidence):**
- [Binance FAQ: Write to Earn](https://www.binance.info/en/support/faq/detail/3f4940d27ff04748a13e0fc1d3f1598d) — cashtag format, 3-max rule
- [Binance Skills Hub: square-post](https://github.com/binance/binance-skills-hub/blob/main/skills/binance/square-post/SKILL.md) — OpenAPI bodyTextOnly details, error codes
- [Telegram Bot API: sendMessage](https://core.telegram.org/bots/api#sendmessage) — character limits, parse modes
- [Telegram Bot API: MessageEntity](https://core.telegram.org/bots/api#messageentity) — hashtag/cashtag entity types
- [Binance Write-to-Earn Announcement](https://www.binance.info/en/support/announcement/detail/4b3e53810ef04d43b9d3b2216e18fb4b) — monetization mechanics

**Secondary (MEDIUM confidence):**
- [Binance Square Community Guidelines](https://www.binance.info/en/support/faq/detail/ecb50ef2012f40b2a2c4f72eaa5b569f) — content standards
- MEXC News: Write-to-Earn Guide — cashtag usage best practices (confirmed via Binance FAQ cross-reference)
