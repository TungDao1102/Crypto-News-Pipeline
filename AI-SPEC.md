# AI-SPEC — Crypto News & Airdrop Automation Pipeline

> System Architecture Design Contract — consumed by all downstream planning and execution phases.
> Locks data flow, module structure, review mechanism, resilience strategy, and content standards before implementation begins.

---

## 1. System Classification

**System Type:** Content Generation + Data Pipeline (Hybrid: Crawl → AI Process → Multi-Platform Publish)

**Description:**
Hệ thống pipeline tự động theo dõi các kênh Telegram quốc tế về crypto airdrop/testnet/retroactive, thu thập bài viết gốc tiếng Anh, gọi API OpenRouter để dịch thuật và xào nấu lại thành nội dung tiếng Việt hấp dẫn theo chuẩn [Oh My Agent], sau đó xuất bản đồng thời lên Telegram Channel công khai (phễu hút user) và Binance Square (kiếm tiền Write-to-Earn).

**Critical Failure Modes:**
1. **Spam/Flood phá kênh** — Crawler đăng nội dung rác hoặc duplicate từ Telegram nguồn mà không qua kiểm soát chất lượng
2. **Lộ thông tin User Telegram** — Session User Telegram bị泄露, dẫn đến khóa tài khoản hoặc lộ API credentials
3. **Sập nguồn cấp dữ liệu** — Mất kết nối Telethon hoặc OpenRouter dài hạn mà không phát hiện, dẫn đến chết pipeline âm thầm
4. **Nội dung kém chất lượng** — AI dịch sai thuật ngữ, giữ nguyên văn phong AI hoặc mất context chuyên ngành crypto
5. **Vỡ cấu trúc JSON** — OpenRouter trả về JSON malformed, gây crash toàn bộ pipeline xử lý

---

## 1b. Domain Context

**Industry Vertical:** Web3 / Crypto — Content Automation & Marketing

**User Population:**
- **Admin (Vận hành):** Người vận hành hệ thống, duyệt bài qua Telegram Bot, quản lý chế độ AUTO/MANUAL
- **End Users (Telegram):** Cộng đồng farming airdrop, săn testnet, quan tâm retroactive — cần tin tức nhanh, chính xác bằng tiếng Việt
- **End Users (Binance Square):** Nhà đầu tư crypto tìm kiếm cơ hội airdrop — nội dung kích thích tương tác để kiếm phí Write-to-Earn

**Stakes Level:** Medium

**Output Consequence:** Nội dung sai lệch về airdrop/testnet có thể khiến người đọc mất phí gas hoặc bỏ lỡ cơ hội thực. Hệ thống bị khóa nếu vi phạm ToS Telegram hoặc Binance.

### What Domain Experts Evaluate Against

| Dimension | Good (expert accepts) | Bad (expert flags) | Stakes | Source |
|-----------|----------------------|---------------------|--------|--------|
| **Thuật ngữ chính xác** | "Mint NFT trên Testnet", "Claim Airdrop sau TGE" | "Đúc token thử", "Nhận quà miễn phí" | High | Crypto farming communities |
| **Tính kịp thời** | Bài đăng trong vòng 15-30 phút từ khi nguồn ra | Bài đăng sau 4+ giờ, cơ hội đã hết | High | Airdrop时效性 |
| **Kích thích tương tác** | "Cơ hội cuối cùng — chỉ còn 48h", "Faucet miễn phí ai chưa xin" | Nội dung khô khan, không có call-to-action | Medium | Binance Square algorithm |
| **Định dạng chuẩn** | Markdown rõ ràng, hashtag đầy đủ, Cashtag coin | Sai định dạng, thiếu hashtag, nội dung một khối | Medium | Binance Square guidelines |

### Known Failure Modes in This Domain

1. **FUD/FOMO amplification** — Dịch tin đồn chưa kiểm chứng từ nguồn quốc tế, gây hoang mang cho cộng đồng Việt
2. **Gas fee misdirection** — Hướng dẫn sai cách mint/testnet khiến user mất tiền phí gas thật
3. **Source overload** — Một kênh nguồn quá nhiều bài trong thời gian ngắn, queue bị nghẽn
4. **Scam link propagation** — Vô tình đăng link lừa đảo từ kênh nguồn không được kiểm duyệt

### Regulatory / Compliance Context

- **Telegram ToS:** Không được spam, không được dùng User Bot để crawl dữ liệu quá mức (rate limit)
- **Binance Square ToS:** Nội dung phải原创, không vi phạm bản quyền, không pump/dump coin
- **OpenRouter ToS:** Tuân thủ rate limit và không abuse API miễn phí

### Domain Expert Roles for Evaluation

| Role | Responsibility |
|------|---------------|
| Crypto content moderator | Kiểm tra chất lượng đầu ra, xác thực thuật ngữ, đánh giá tính kịp thời |
| Senior airdrop farmer | Label dataset đầu ra (rubric calibration), đánh giá độ hấp dẫn nội dung |

---

## 2. FrameWork Decision

**Selected Framework:** Không sử dụng AI framework chuyên dụng (LangChain/LlamaIndex). Hệ thống là pipeline thuần Python với asyncio, gọi OpenRouter API trực tiếp qua HTTP.

**Rationale:**
- Hệ thống không cần RAG, agent loop, hay tool-use phức tạp — chỉ cần call API đơn giản với structured output
- OpenRouter cung cấp OpenAI-compatible API, có thể dùng `httpx` + Pydantic để quản lý response
- Giảm dependency, giảm chi phí bảo trì, tăng tốc độ xử lý
- Dễ dàng fallback giữa các model mà không cần qua framework abstraction layer

**Alternatives Considered:**

| FrameWork | Ruled Out Because |
|-----------|------------------|
| LangChain | Overkill — thêm dependency không cần thiết cho pipeline đơn giản, tăng độ phức tạp debug |
| LlamaIndex | Designed cho RAG — không phù hợp với use case translate + rewrite thuần túy |
| OpenAI SDK | Chỉ support OpenAI models — không linh hoạt cho fallback ma trận đa model của OpenRouter |

**Vendor Lock-In Accepted:** Partial — OpenRouter API format, nhưng có thể swap sang bất kỳ OpenAI-compatible endpoint nào với thay đổi tối thiểu.

---

## 3. Data Flow Architecture

> Dòng chảy dữ liệu xuyên suốt hệ thống từ đầu vào đến đầu ra.

### High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA INGESTION LAYER                                │
│                                                                             │
│  Telegram Sources ──► Telethon User Client ──► Event Handler ──► Raw Queue  │
│  (Configurable)          (Async Listener)         (New Message)   (Memory) │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │ Raw Message
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA PROCESSING LAYER                               │
│                                                                             │
│  Raw Queue ──► Preprocessor ──► OpenRouter AI ──► JSON Validator ──► Draft │
│              (Clean HTML)     (Translate+Rewrite)  (Pydantic Schema)  Queue │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │ Draft Content
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA DISTRIBUTION LAYER                             │
│                                                                             │
│  Draft Queue ──► Mode Gate ──► Publisher ──► Telegram Channel              │
│              (AUTO/MANUAL)        │                                          │
│                                   ├──► Binance Square (OpenAPI)             │
│                                   │                                          │
│  MANUAL: ──► Bot Reviewer ──► Admin ──► Approve/Reject                     │
│              (Inline Keyboard)    (Decision)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Chi tiết Data Flow

#### Stage 1: Ingestion (Crawl)
1. **Telethon User Client** đăng nhập bằng `TELEGRAM_API_ID` + `TELEGRAM_API_HASH`
2. Client lắng nghe sự kiện `NewMessage` từ danh sách kênh nguồn (cấu hình trong `.env` hoặc file JSON)
3. Mỗi message mới → đóng gói thành `RawMessage` object (gồm: `source_channel`, `raw_text`, `media`, `timestamp`)
4. Push `RawMessage` vào **asyncio.Queue** (bộ nhớ đệm)

#### Stage 2: Processing (AI Transform)
1. Consumer lấy `RawMessage` từ Queue
2. **Preprocessor** làm sạch: loại bỏ emoji thừa, URL rác, định dạng lại plain text
3. Gọi **OpenRouter API** với prompt engineered để:
   - Dịch thuật ngữ crypto sang tiếng Việt
   - Viết lại thành văn phong tự nhiên, lôi cuốn
   - Trả về JSON cấu trúc: `{title_vn, telegram_markdown, binance_square_markdown}`
4. **JSON Validator** dùng Pydantic kiểm tra response:
   - Nếu valid → push vào `Draft Queue`
   - Nếu invalid → retry với model fallback hoặc ghi log lỗi

#### Stage 3: Distribution (Publish)
1. **Mode Gate** kiểm tra `SYSTEM_MODE`:
   - `AUTO`: gửi thẳng tới Publisher
   - `MANUAL`: gửi bản nháp cho Admin duyệt qua Bot Reviewer
2. **Publisher** đăng bài đồng thời lên:
   - Telegram Channel (qua Bot Token)
   - Binance Square (qua OpenAPI + Cashtag/Hashtag)

---

## 4. Clean Source Module Structure (src/)

Kiến trúc thư mục mã nguồn — mỗi file một responsibility rõ ràng.

```
crypto-news-pipeline/
│
├── src/
│   ├── __init__.py
│   │
│   ├── main.py                          # Entry point, khởi tạo và điều phối toàn bộ hệ thống
│   │                                     # - Đọc config → khởi tạo các service
│   │                                     # - Khởi chạy crawler, processor, publisher đồng thời (asyncio.gather)
│   │                                     # - Quản lý vòng đời: start → running → shutdown (graceful)
│   │                                     # - Bắt tín hiệu SIGINT/SIGTERM để cleanup
│   │
│   ├── config.py                        # Quản lý cấu hình và bảo mật
│   │                                     # - Đọc .env bằng python-dotenv
│   │                                     # - Kiểm tra toàn vẹn: validate tất cả required keys tồn tại
│   │                                     # - Kiểm tra bảo mật: cảnh báo nếu dùng giá trị mặc định
│   │                                     # - Expose dataclass chứa toàn bộ config
│   │
│   ├── crawler.py                       # Telegram Crawler (Telethon User Client)
│   │                                     # - async def listen(): lắng nghe NewMessage từ kênh nguồn
│   │                                     # - async def fetch_history(channel, limit): fetch lịch sử khi khởi động
│   │                                     # - Quản lý danh sách kênh nguồn (có thể thêm/xóa động)
│   │                                     # - Exponential Backoff khi mất kết nối hoặc rate limited
│   │
│   ├── models.py                        # Pydantic models cho toàn bộ hệ thống
│   │                                     # - RawMessage: source_channel, raw_text, media, timestamp
│   │                                     # - DraftContent: title_vn, telegram_markdown, binance_square_markdown
│   │                                     # - PublishResult: platform, status, url, error
│   │
│   ├── ai_handler.py                    # OpenRouter AI handler (Structured Outputs)
│   │                                     # - async def translate_and_rewrite(raw_text) → DraftContent
│   │                                     # - Sử dụng OpenRouter chat completions endpoint
│   │                                     # - Cấu hình response_format = {"type": "json_object"}
│   │                                     # - Fallback chain: deepseek-chat:free → llama-3-70b-instruct:free
│   │                                     # - retry 3 lần với exponential backoff khi API lỗi
│   │
│   ├── bot_reviewer.py                  # Telegram Bot Reviewer (Human-in-the-Loop)
│   │                                     # - async def send_for_review(draft) → gửi bản nháp + inline keyboard
│   │                                     # - Inline Keyboard: [✅ Approve] [❌ Reject] [✏️ Edit]
│   │                                     # - Lắng nghe callback_query để bắt sự kiện bấm nút
│   │                                     # - Lắng nghe lệnh: /mode_auto, /mode_manual, /status
│   │                                     # - async def set_mode(mode): thay đổi SYSTEM_MODE runtime
│   │
│   ├── publisher.py                     # Multi-Platform Publisher
│   │                                     # - async def publish(draft_content) → list[PublishResult]
│   │                                     # - TelegramPublisher: gửi qua Bot API → channel
│   │                                     # - BinanceSquarePublisher: gửi qua OpenAPI → Binance Square
│   │                                     # - CashtagInjector: tự động thêm $BTC, $ETH, $SOL, v.v.
│   │                                     # - HashtagInjector: thêm #Airdrop #Testnet #Retroactive
│   │
│   └── logging_setup.py                 # Logging & Monitoring
│                                         # - Cấu hình logging: console + file (logs/app.log)
│                                         # - Rotating file handler (10MB, 5 backups)
│                                         # - Log format: timestamp | level | module | message
│                                         # - Exception hook để bắt unhandled exception
│
├── logs/
│   └── app.log                          # Log file tự động tạo
│
├── .env                                 # Credentials (gitignored)
├── .env.example                         # Template cho env (committed)
├── requirements.txt                     # Python dependencies
│
├── AI-SPEC.md                           # THIS FILE — Architecture Design Specification
│
└── README.md                            # Project overview & setup guide
```

### Module Responsibility Matrix

| File | Input | Output | Key Libraries | Error Mode |
|------|-------|--------|---------------|------------|
| `config.py` | `.env` file | `Config` dataclass | `python-dotenv`, `dataclasses` | Thiếu key → raise `ConfigError` |
| `crawler.py` | Telegram channels | `RawMessage` objects | `Telethon`, `asyncio` | Mất kết nối → reconnect với backoff |
| `ai_handler.py` | `RawMessage.raw_text` | `DraftContent` (JSON validated) | `httpx`, `pydantic` | API lỗi → fallback model |
| `bot_reviewer.py` | `DraftContent` | Approve/Reject signal | `python-telegram-bot` | Timeout → retry gửi |
| `publisher.py` | `DraftContent` | `PublishResult` | `httpx`, Telegram Bot API | API lỗi → retry 3 lần |
| `main.py` | All modules | Running system | `asyncio`, `signal` | Lỗi component → restart component |
| `logging_setup.py` | Log records | `logs/app.log` | `logging`, `RotatingFileHandler` | Disk full → fallback to stderr |

---

## 5. Human-in-the-Loop Review Mechanism & Mode Management

### 5.1. SYSTEM_MODE Global Variable

```python
# Biến toàn cục kiểm soát trạng thái hệ thống
SYSTEM_MODE: Literal["AUTO", "MANUAL"] = "MANUAL"  # Mặc định MANUAL an toàn
```

- **AUTO**: Bài viết qua AI xử lý → tự động đăng lên Telegram + Binance Square
- **MANUAL**: Bài viết qua AI xử lý → lưu queue → gửi Admin duyệt → chỉ đăng khi Approve

### 5.2. Mode Switching (Runtime — No Restart)

**Cơ chế:** Bot Reviewer lắng nghe lệnh chat từ Admin:

| Command | Hành động |
|---------|-----------|
| `/mode_auto` | Set `SYSTEM_MODE = "AUTO"`. Bot reply: ✅ **Chế độ AUTO** — Bài viết sẽ được đăng tự động. |
| `/mode_manual` | Set `SYSTEM_MODE = "MANUAL"`. Bot reply: 👤 **Chế độ MANUAL** — Bài viết chờ Admin duyệt. |
| `/status` | Bot reply: 📊 **Status** — Mode hiện tại, queue depth, số bài đã đăng hôm nay. |

**Implementation:**
```python
# Trong bot_reviewer.py
async def handle_mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command = update.message.text.strip().lower()
    if command == "/mode_auto":
        system_state.set_mode("AUTO")
        await update.message.reply_text("✅ Chế độ AUTO — Bài viết sẽ được đăng tự động.")
    elif command == "/mode_manual":
        system_state.set_mode("MANUAL")
        await update.message.reply_text("👤 Chế độ MANUAL — Bài viết chờ Admin duyệt.")
```

`system_state` là singleton object dùng chung giữa các module, thread-safe với `asyncio.Lock`.

### 5.3. Approval Flow (MANUAL Mode)

```
Draft Ready
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  Bot Reviewer gửi bản nháp tới ADMIN_CHAT_ID:        │
│                                                      │
│   📝 Tiêu đề bài viết                                │
│   ─────────────────────────────────────────────      │
│   [Nội dung markdown tiếng Việt...]                  │
│   ─────────────────────────────────────────────      │
│                                                      │
│   [✅ Approve]  [❌ Reject]  [✏️ Edit]              │
└─────────────────────────────────────────────────────┘
    │           │           │
    ▼           ▼           ▼
Approve     Reject      Edit
    │           │           │
    ▼           ▼           ▼
Publish     Bỏ qua     Admin sửa
    │        + Log     bằng tay
    ▼                   │
Publish Result          ▼
                    Publish
```

**Chi tiết nút bấm:**

| Nút | Callback | Hành động |
|-----|----------|-----------|
| `✅ Approve` | `callback_data="approve:{draft_id}"` | Gọi Publisher, xóa khỏi queue, log "Đã duyệt" |
| `❌ Reject` | `callback_data="reject:{draft_id}"` | Xóa khỏi queue, log "Từ chối — lý do: (optional)" |
| `✏️ Edit` | `callback_data="edit:{draft_id}"` | Admin gửi text chỉnh sửa → AI re-process với context gốc |

### 5.4. Queue Management

- **Draft Queue:** `asyncio.Queue` lưu các `DraftContent` object chờ duyệt
- Khi queue đầy (>100 items): tự động chuyển sang chế độ backpressure, tạm dừng ingestion
- Bot có thể trả lời `/queue` command để xem trạng thái queue:
  ```
  📊 Queue Status: 12 bài chờ duyệt
  - Bài cũ nhất: 3 phút trước (ID: draft_042)
  - Bài mới nhất: 30 giây trước (ID: draft_054)
  - Mode hiện tại: MANUAL
  ```

---

## 6. Resilience & Self-Recovery (Phòng thủ hệ thống)

### 6.1. Telethon Connection — Exponential Backoff

```python
BACKOFF_CONFIG = {
    "initial_delay": 1,       # giây
    "max_delay": 300,         # 5 phút
    "multiplier": 2,          # double mỗi lần retry
    "jitter": 0.1,            # ±10% random jitter
    "max_retries": 10         # sau 10 lần → log critical và chờ manual
}

# Khi mất kết nối (FloodWaitError, ConnectionError):
# Lần 1: chờ 1s + jitter
# Lần 2: chờ 2s + jitter
# Lần 3: chờ 4s + jitter
# ...
# Nếu vượt max_retries → gửi alert tới Admin Telegram
```

**Cơ chế:** Telethon đã có built-in reconnection handling. Ta override `on_error` callback để thêm logging và exponential backoff logic.

### 6.2. OpenRouter Fallback — Model Ma Trận

**Primary → Fallback Chain:**

```
deepseek-chat:free
    ↓ (nếu 429 Too Many Requests hoặc 5xx Server Error)
meta-llama/llama-3-70b-instruct:free
    ↓ (nếu cũng lỗi)
qwen/qwen-2.5-72b-instruct:free
    ↓ (tất cả đều lỗi)
Log critical error + Alert Admin + Pause AI processing 5 phút
```

**Implementation pattern trong `ai_handler.py`:**

```python
FALLBACK_CHAIN = [
    "deepseek-chat:free",
    "meta-llama/llama-3-70b-instruct:free",
    "qwen/qwen-2.5-72b-instruct:free"
]

async def translate_and_rewrite(raw_text: str) -> DraftContent:
    last_error = None
    for model in FALLBACK_CHAIN:
        try:
            response = await call_openrouter(model, raw_text)
            validated = DraftContent.model_validate_json(response)
            logger.info(f"✅ AI success — model: {model}")
            return validated
        except (RateLimitError, ServerError, ValidationError) as e:
            last_error = e
            logger.warning(f"⚠️ Model {model} failed: {e}. Falling back...")
            await asyncio.sleep(2)  # cool-off trước khi fallback
    # Tất cả models đều fail
    logger.critical(f"❌ All AI models failed. Last error: {last_error}")
    raise AIPipelineError("All models exhausted")
```

### 6.3. Structured Outputs Validation (JSON Mode)

**Cấu hình OpenRouter request:**

```python
request_body = {
    "model": model_name,
    "messages": [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": raw_text}
    ],
    "response_format": {"type": "json_object"},
    "temperature": 0.7,
    "max_tokens": 2048
}
```

**Pydantic validation:**

```python
class DraftContent(BaseModel):
    title_vn: str = Field(..., min_length=5, max_length=200)
    telegram_markdown: str = Field(..., min_length=20, max_length=4000)
    binance_square_markdown: str = Field(..., min_length=20, max_length=4000)

def validate_response(raw_json: str) -> DraftContent:
    try:
        return DraftContent.model_validate_json(raw_json)
    except ValidationError as e:
        logger.error(f"❌ JSON validation failed: {e}")
        # Thử fix: nếu thiếu field → raise → fallback chain sẽ xử lý
        raise
```

### 6.4. Logging & Monitoring

```python
# logging_setup.py
LOG_CONFIG = {
    "version": 1,
    "formatters": {
        "standard": {
            "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/app.log",
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 5,
            "level": "DEBUG",
            "formatter": "standard"
        }
    },
    "root": {
        "level": "DEBUG",
        "handlers": ["console", "file"]
    }
}
```

**Log levels mapping:**

| Event | Level | Example |
|-------|-------|---------|
| Bài viết mới từ nguồn | DEBUG | `[crawler] New message from @airdrop_source` |
| AI xử lý thành công | INFO | `[ai_handler] ✅ deepseek-chat:free — 412 tokens, 1.8s` |
| Fallback model | WARNING | `[ai_handler] ⚠️ deepseek failed (429) → falling to llama-3` |
| Mất kết nối Telegram | WARNING | `[crawler] ⚠️ Connection lost — retry in 4s (attempt 2/10)` |
| JSON validation fail | ERROR | `[ai_handler] ❌ JSON missing field: title_vn` |
| Tất cả models fail | CRITICAL | `[ai_handler] 🔴 All models exhausted — pausing 5 minutes` |
| Admin approve/reject | INFO | `[reviewer] ✅ draft_042 approved by admin` |
| Publish thành công | INFO | `[publisher] ✅ Published to Telegram + Binance Square` |
| Publish thất bại | ERROR | `[publisher] ❌ Binance Square API error: 403 Forbidden` |

---

## 7. Content Standards for Crypto Content

### 7.1. Core Terminology — Giữ nguyên (không dịch)

| Thuật ngữ gốc | Giữ nguyên | Lý do |
|---------------|-------------|-------|
| Testnet | ✅ Testnet | Không có từ thay thế chính xác trong tiếng Việt |
| Mainnet | ✅ Mainnet | Tương tự — thuật ngữ quốc tế hóa |
| Mint NFT | ✅ Mint NFT | "Đúc NFT" nghe không tự nhiên |
| Faucet | ✅ Faucet | "Vòi nước" là sai hoàn toàn |
| Gas fee | ✅ Gas fee | "Phí gas" chấp nhận được nhưng giữ gốc an toàn hơn |
| Airdrop | ✅ Airdrop | "Thả token" không chuẩn |
| Staking | ✅ Staking | "Cọc" hoàn toàn sai nghĩa |

### 7.2. Văn phong — Tiếng Việt lôi cuốn, tự nhiên

**Nguyên tắc viết:**
- ✅ Câu ngắn, rõ ràng, có cảm xúc: "Cơ hội cuối cùng để claim Airdrop LayerZero"
- ✅ Sử dụng từ ngữ thông dụng trong cộng đồng crypto Việt: "săn airdrop", "farm testnet", "claim token"
- ✅ Có call-to-action rõ ràng: "Tham gia ngay", "Đừng bỏ lỡ", "Nhanh tay kẻo hết"
- ✅ Dùng emoji hợp lý (🚀, 💰, 🔥, ✅, ⚠️) để tăng visual appeal
- ✅ Ngắt đoạn ngắn, dễ đọc trên mobile
- ❌ Không quá lịch sự: tránh "xin mời", "kính mời", "xin phép"
- ❌ Không văn phong AI: tránh "trong thế giới crypto ngày nay", "hãy cùng tìm hiểu"
- ❌ Không quá kỹ thuật với người mới: giải thích ngắn nếu cần

### 7.3. Output Format — Telegram Markdown

```markdown
🚀 **[Tiêu đề hấp dẫn — tối đa 120 ký tự]**

[Giới thiệu ngắn — 1-2 câu về cơ hội]

📌 **Thông tin chi tiết:**
• [Điểm 1: Mô tả ngắn gọn]
• [Điểm 2: Thời gian, số lượng, yêu cầu]
• [Điểm 3: Cách tham gia]

⚡ **Hướng dẫn:**
1. Bước 1: [Mô tả]
2. Bước 2: [Mô tả]
3. Bước 3: [Mô tả]

⚠️ *Lưu ý: [Cảnh báo nếu có — phí gas, thời hạn, rủi ro]*

#Airdrop #Testnet #Retroactive #[TênDựÁn]
```

### 7.4. Output Format — Binance Square Markdown

```markdown
## 🚀 [Tiêu đề — SEO-friendly, tối đa 150 ký tự]

[Body content giống Telegram nhưng dài hơn (800-2000 từ), thêm phân tích và nhận định]

**🔑 Key Takeaways:**
• [Takeaway 1]
• [Takeaway 2]
• [Takeaway 3]

---

*Bài viết được tổng hợp và biên tập bởi [Channel Name]*

[Auto-injected]
#Airdrop #Crypto #[TênCoin]

$BTC $ETH $SOL $ARB $OP
```

**Cashtag rules:**
- Tự động phát hiện tên coin trong nội dung
- Chèn Cashtag duy nhất một lần cho mỗi coin ở cuối bài
- Priority Cashtag list: `$BTC`, `$ETH`, `$SOL`, `$ARB`, `$OP`, `$MATIC`, `$AVAX`, `$ATOM`
- Nếu coin không có trong danh sách ưu tiên, dùng format `$TICKER`

**Hashtag rules:**
- Luôn thêm `#Airdrop` ở cuối
- Thêm `#Testnet` hoặc `#Retroactive` tùy nội dung
- Thêm `#[TênDựÁn]` nếu là dự án cụ thể
- Tối đa 5 hashtag mỗi bài

### 7.5. Prompt Engineering cho AI

**System Prompt (tiếng Anh để AI hiểu rõ instruction):**

```
You are a professional crypto news Vietnamese translator and content creator.
Your task is to:
1. Translate the following English crypto news about airdrop/testnet/retroactive to Vietnamese
2. Rewrite it in an engaging, natural Vietnamese style suitable for Vietnamese crypto community
3. PRESERVE these English terms: Testnet, Mainnet, Mint, NFT, Faucet, Gas fee, Airdrop, Staking, Claim, Token, TGE, IDO, ICO, whitelist, KYC
4. Output must be valid JSON ONLY with exactly 3 fields (no markdown wrapping the JSON)

Vietnamese style guidelines:
- Use short, punchy sentences
- Include emojis where appropriate (🚀💰🔥⚡✅⚠️)
- Start with a hook that creates urgency or excitement
- Use community terms: "săn airdrop", "farm testnet", "claim token"
- Natural and conversational, NOT overly polite
- Each paragraph max 3 lines (mobile-friendly)
- End with clear call-to-action

Content rules:
- NEVER include price predictions or financial advice
- NEVER promote scams or suspicious links
- Flag any content that sounds like a potential scam
```

**User Prompt (raw English article):**
```
{{raw_text}}

Write in Vietnamese. Output ONLY a JSON object with this exact structure (no markdown code fences):
{
  "title_vn": "...",
  "telegram_markdown": "...",
  "binance_square_markdown": "..."
}
```

---

## 8. Evaluation Strategy

### 8.1. Dimensions

| Dimension | Rubric (Pass/Fail) | Measurement Approach | Priority |
|-----------|-------------------|---------------------|----------|
| **Thuật ngữ chính xác** | Pass: Giữ nguyên Testnet/Mainnet/Mint/Faucet/Gas fee/Airdrop/Staking — Fail: Dịch sai hoặc bỏ qua | LLM Judge (sample 10 bài) | Critical |
| **Văn phong tự nhiên** | Pass: Câu ngắn, có cảm xúc, dùng từ cộng đồng — Fail: Văn phong AI, quá lịch sự | Human review | Critical |
| **Cấu trúc JSON** | Pass: Valid JSON, đúng schema DraftContent — Fail: Malformed, thiếu field | Code automated (Pydantic) | Critical |
| **Định dạng Markdown** | Pass: Đúng Telegram/Binance format — Fail: Sai cú pháp, thiếu hashtag/cashtag | Code automated (regex) | High |
| **Tính kịp thời** | Pass: Bài đăng trong 30 phút từ nguồn — Fail: Trễ >60 phút | Log monitoring | High |
| **No hallucination** | Pass: Không thêm thông tin không có trong nguồn — Fail: Thêm nhận định sai | LLM Judge (sample) | Critical |

### 8.2. Test Scenarios for Development

| Scenario | Input | Expect Output | Type |
|----------|-------|---------------|------|
| Normal airdrop news | Bài viết về airdrop LayerZero | Title VN hấp dẫn, đủ 3 fields JSON, có $ZRO #Airdrop | Unit |
| Testnet announcement | Thông báo testnet mới | Giữ nguyên "Testnet", hướng dẫn các bước rõ ràng | Unit |
| Chinese/other language | Bài không phải tiếng Anh | Log warning + skip (hoặc xử lý nếu có thể) | Edge |
| Empty content | Message chỉ có emoji/URL | Skip + log info | Edge |
| Very long article | Bài >4000 ký tự | Truncate + process, log warning | Edge |
| API timeout | OpenRouter timeout | Fallback to next model, không crash | Resilience |
| Network disconnect | Mất internet | Exponential backoff, reconnect khi có mạng | Resilience |
| Rate limited | Telegram FloodWait | Chờ + retry, không mất message | Resilience |

---

## 9. Guardrails

### 9.1. Online (Real-Time)

| Guardrail | Trigger | Intervention |
|-----------|---------|--------------|
| Content length check | Bài viết >4000 ký tự hoặc <20 ký tự | Truncate hoặc reject + log warning |
| Duplicate detection | Nội dung trùng >80% với bài đã đăng trong 24h | Skip + log "duplicate" |
| Scam keyword detection | Nội dung chứa từ khóa pump/dump, get-rich-quick | Flag "suspicious" + luôn gửi Admin review (kể cả AUTO mode) |
| Rate limit per source | Một nguồn gửi >20 bài trong 1 giờ | Tạm dừng nguồn đó 30 phút + alert Admin |
| API credit check | OpenRouter balance thấp | Warning log + alert Admin |

### 9.2. Offline (Flywheel)

| Metric | Sampling Strategy | Action on Degradation |
|--------|------------------|----------------------|
| Tỉ lệ Approve/Reject | Daily aggregate | Nếu reject >30% → kiểm tra prompt quality |
| Lỗi JSON validation | Per-day count | Nếu >5% → kiểm tra model quality/thay đổi prompt |
| API latency | P95 hàng giờ | Nếu >10s → alert + check OpenRouter status |
| Queue depth | Every 5 phút | Nếu >50 → auto switch to MANUAL mode |

---

## 10. Environment Configuration (.env)

```ini
# Telegram Personal API credentials for data scraping/crawling
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_api_hash_32_characters

# Telegram Reviewer Bot token obtained from @BotFather
TELEGRAM_BOT_TOKEN=123456:ABCdefGhIJKlmNoPQRsTUVwxyZ

# Personal Telegram Chat ID of the Admin for receiving post approvals
ADMIN_CHAT_ID=987654321

# OpenRouter API Key for free AI model orchestration
OPENROUTER_API_KEY=your_openrouter_api_key

# Binance Square OpenAPI Key for Creator monetization
BINANCE_SQUARE_API_KEY=your_binance_square_api_key

# Target Telegram Public Channel for publishing approved posts
TELEGRAM_CHANNEL_ID=@your_telegram_channel

# Telegram source channels to monitor (comma-separated)
SOURCE_CHANNELS=@airdrop_news,@testnet_alerts,@defi_updates

# System mode at startup (AUTO or MANUAL)
SYSTEM_MODE=MANUAL
```

`config.py` sẽ validate:
1. Tất cả keys required phải tồn tại
2. `TELEGRAM_API_HASH` phải đúng 32 ký tự
3. `TELEGRAM_API_ID` phải là số
4. `TELEGRAM_BOT_TOKEN` phải match pattern regex `\d+:[\w-]+`
5. Cảnh báo nếu giá trị là default sample (chứa "your_")
6. `SOURCE_CHANNELS` parse thành list, trim whitespace

---

## Checklist

- [x] **1. Data Flow Architecture** — Ingestion → Processing → Distribution (3 stages, Pydantic-validated)
- [x] **2. Clean Module Structure (src/)** — 7 files, mỗi file một responsibility rõ ràng
- [x] **3. Human-in-the-Loop** — SYSTEM_MODE (AUTO/MANUAL), Bot Reviewer Inline Keyboard, Runtime mode switching
- [x] **4. Resilience** — Exponential Backoff (Telethon), Model Fallback Chain (OpenRouter), Structured Outputs, Rotating Logs
- [x] **5. Content Standards** — Thuật ngữ crypto giữ nguyên, văn phong lôi cuốn, Telegram/Binance format, Cashtag + Hashtag auto-inject
- [x] **6. Guardrails** — Online (length, duplicate, scam, rate limit) + Offline (metrics, sampling)
- [x] **7. Evaluation Strategy** — 6 Dimensions with rubrics, Test Scenarios (Unit/Edge/Resilience)
- [x] **8. Environment Config** — Full .env spec with validation rules
- [ ] Implement Phase 1: Configuration & Crawler
- [ ] Implement Phase 2: AI Handler & Processing
- [ ] Implement Phase 3: Bot Reviewer & Mode Management
- [ ] Implement Phase 4: Publisher & Platform Integration
- [ ] Implement Phase 5: Resilience, Logging & Monitoring

---

*Last updated: 2026-05-after system architecture design*
