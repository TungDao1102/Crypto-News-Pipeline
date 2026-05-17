import asyncio
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from src.models import DraftContent
from src.scam_patterns import is_low_confidence, is_suspicious
from src.system_state import SystemState

logger = logging.getLogger(__name__)

_pending_drafts: dict[int, DraftContent] = {}
_next_index: int = 0

WAITING_EDIT_TEXT = 1
EDIT_TIMEOUT_SECONDS = 300


async def startup_notification(
    application: Application,
    system_state: SystemState,
    result_queue: asyncio.Queue[DraftContent],
) -> None:
    admin_chat_id = application.bot_data.get("admin_chat_id")
    if not admin_chat_id:
        logger.warning("ADMIN_CHAT_ID not set — skipping startup notification")
        return
    mode = await system_state.get_mode()
    queue_size = result_queue.qsize()
    text = (
        f"✅ Bot started\n"
        f"SYSTEM_MODE: {mode}\n"
        f"Drafts in queue: {queue_size}"
    )
    await application.bot.send_message(
        chat_id=admin_chat_id,
        text=text,
    )
    logger.info("Startup notification sent to admin")


async def post_init(application: Application) -> None:
    system_state: SystemState = application.bot_data.get("system_state")
    result_queue: asyncio.Queue[DraftContent] = application.bot_data.get(
        "result_queue"
    )
    if system_state and result_queue:
        await startup_notification(application, system_state, result_queue)


async def mode_auto(update: Update, context: CallbackContext) -> None:
    system_state: SystemState = context.application.bot_data["system_state"]
    await system_state.set_mode("AUTO")
    await update.message.reply_text(
        "✅ Chế độ AUTO — Bài viết sẽ được đăng tự động."
    )


async def mode_manual(update: Update, context: CallbackContext) -> None:
    system_state: SystemState = context.application.bot_data["system_state"]
    await system_state.set_mode("MANUAL")
    await update.message.reply_text(
        "👤 Chế độ MANUAL — Bài viết chờ Admin duyệt."
    )


async def status(update: Update, context: CallbackContext) -> None:
    system_state: SystemState = context.application.bot_data["system_state"]
    result_queue: asyncio.Queue[DraftContent] = context.application.bot_data[
        "result_queue"
    ]
    mode = await system_state.get_mode()
    processed = await system_state.get_processed_count()
    queue_depth = result_queue.qsize()
    text = (
        f"📊 **System Status**\n"
        f"Mode: {mode}\n"
        f"Queue: {queue_depth} drafts pending\n"
        f"Processed today: {processed}"
    )
    await update.message.reply_text(text)


def _build_draft_text(draft: DraftContent) -> str:
    return (
        f"📝 **{draft.title_vn}**\n\n"
        f"```\n{draft.telegram_markdown}\n```\n\n"
        f"```\n{draft.binance_square_markdown}\n```"
    )


def _build_keyboard(draft_index: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve:{draft_index}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject:{draft_index}"),
            InlineKeyboardButton("✏️ Edit", callback_data=f"edit:{draft_index}"),
        ]
    ])


async def handle_approve(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    draft_index = int(query.data.split(":")[1])
    draft = _pending_drafts.pop(draft_index, None)
    if draft is None:
        await query.edit_message_text("⚠️ Draft no longer available.")
        return
    draft.status = "approved"
    publish_queue: asyncio.Queue[DraftContent] = context.application.bot_data[
        "publish_queue"
    ]
    await publish_queue.put(draft)
    system_state: SystemState = context.application.bot_data["system_state"]
    await system_state.increment_processed()
    await query.edit_message_text(f"✅ **Approved** — {draft.title_vn}")
    logger.info("Draft %d approved by admin — %s", draft_index, draft.title_vn)


async def handle_reject(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    draft_index = int(query.data.split(":")[1])
    draft = _pending_drafts.pop(draft_index, None)
    if draft is None:
        await query.edit_message_text("⚠️ Draft no longer available.")
        return
    draft.status = "rejected"
    await query.edit_message_text(f"❌ **Rejected** — {draft.title_vn}")
    logger.info("Draft %d rejected by admin — %s", draft_index, draft.title_vn)


async def review_consumer(
    result_queue: asyncio.Queue[DraftContent],
    application: Application,
    admin_chat_id: str,
) -> None:
    global _next_index
    system_state: SystemState = application.bot_data["system_state"]
    publish_queue: asyncio.Queue[DraftContent] = application.bot_data["publish_queue"]
    while True:
        draft = await result_queue.get()
        mode = await system_state.get_mode()

        if mode == "AUTO":
            combined = f"{draft.title_vn} {draft.telegram_markdown} {draft.binance_square_markdown}"
            suspicious = is_suspicious(combined)
            low_conf = is_low_confidence(draft, draft.used_fallback)

            if not suspicious and not low_conf:
                draft.status = "approved"
                await publish_queue.put(draft)
                await system_state.increment_processed()
                logger.info(
                    "AUTO approved draft — %s",
                    draft.title_vn,
                )
                continue
            logger.info(
                "Forcing manual review (suspicious=%s, low_confidence=%s) — %s",
                suspicious,
                low_conf,
                draft.title_vn,
            )

        idx = _next_index
        _next_index += 1
        _pending_drafts[idx] = draft
        text = _build_draft_text(draft)
        keyboard = _build_keyboard(idx)
        try:
            await application.bot.send_message(
                chat_id=admin_chat_id,
                text=text,
                reply_markup=keyboard,
            )
        except Exception:
            logger.exception("Failed to send draft %d for review", idx)

        pending_count = len(_pending_drafts)
        if pending_count > 50:
            logger.warning(
                "Review queue at %d pending — backpressure warning",
                pending_count,
            )


async def handle_edit(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    draft_index = int(query.data.split(":")[1])
    draft = _pending_drafts.get(draft_index)
    if draft is None:
        await query.edit_message_text("⚠️ Draft no longer available.")
        return ConversationHandler.END
    context.user_data["edit_draft_index"] = draft_index
    await query.edit_message_text(
        f"✏️ **Editing draft {draft_index}**\n\n"
        f"Title: {draft.title_vn}\n\n"
        f"Send the replacement text for the full draft body "
        f"(Telegram + Binance Square format).\n"
        f"The title will be preserved.\n\n"
        f"Reply with your new content, or /cancel to abort."
    )
    return WAITING_EDIT_TEXT


async def receive_edit(update: Update, context: CallbackContext) -> int:
    draft_index = context.user_data.get("edit_draft_index")
    if draft_index is None:
        await update.message.reply_text("⚠️ No active edit session.")
        return ConversationHandler.END
    draft = _pending_drafts.get(draft_index)
    if draft is None:
        await update.message.reply_text("⚠️ Draft no longer available.")
        return ConversationHandler.END
    new_text = update.message.text
    draft.telegram_markdown = new_text
    draft.binance_square_markdown = new_text
    draft.status = "pending"
    text = _build_draft_text(draft)
    keyboard = _build_keyboard(draft_index)
    admin_chat_id = context.application.bot_data["admin_chat_id"]
    await context.application.bot.send_message(
        chat_id=admin_chat_id,
        text=text,
        reply_markup=keyboard,
    )
    await update.message.reply_text(
        f"✅ Draft {draft_index} updated — re-sent for approval."
    )
    logger.info("Draft %d edited by admin", draft_index)
    return ConversationHandler.END


async def cancel_edit(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("✖️ Edit cancelled. Draft preserved as-is.")
    return ConversationHandler.END


async def edit_timeout(update: Update, context: CallbackContext) -> int:
    if update.callback_query:
        await update.callback_query.answer()
    chat_id = update.effective_chat.id
    await context.application.bot.send_message(
        chat_id=chat_id,
        text="⏰ Edit timed out. Draft preserved as-is.",
    )
    return ConversationHandler.END


def register_handlers(application: Application) -> None:
    application.add_handler(CommandHandler("mode_auto", mode_auto))
    application.add_handler(CommandHandler("mode_manual", mode_manual))
    application.add_handler(CommandHandler("status", status))

    edit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_edit, pattern="^edit:")],
        states={
            WAITING_EDIT_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edit),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_edit),
            CallbackQueryHandler(edit_timeout, pattern="^edit:"),
        ],
        conversation_timeout=EDIT_TIMEOUT_SECONDS,
    )
    application.add_handler(edit_conv)

    application.add_handler(CallbackQueryHandler(handle_approve, pattern="^approve:"))
    application.add_handler(CallbackQueryHandler(handle_reject, pattern="^reject:"))


async def run_bot(
    token: str,
    system_state: SystemState,
    admin_chat_id: str,
    result_queue: asyncio.Queue[DraftContent],
    publish_queue: asyncio.Queue[DraftContent],
) -> None:
    application = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .build()
    )
    application.bot_data["system_state"] = system_state
    application.bot_data["admin_chat_id"] = admin_chat_id
    application.bot_data["result_queue"] = result_queue
    application.bot_data["publish_queue"] = publish_queue

    register_handlers(application)

    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    asyncio.create_task(review_consumer(result_queue, application, admin_chat_id))

    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        logger.info("Bot polling cancelled — shutting down")
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
