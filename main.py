import html
import io
import logging
import threading
import uuid
from collections import OrderedDict
from queue import Queue

import requests
import telebot
from decouple import config
from PIL import Image, UnidentifiedImageError
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyParameters

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

BOT_TOKEN = config("BOT_TOKEN")
HUGGINGFACE_TOKEN = config("HUGGINGFACE_TOKEN")
API_URL = config("API_URL")

REQUEST_TIMEOUT = 120
MAX_CAPTION_PROMPT_LEN = 800
MAX_PROMPT_CACHE_SIZE = 200

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

http_session = requests.Session()
http_session.headers.update(
    {
        "Authorization": f"Bearer {HUGGINGFACE_TOKEN}",
        "Accept": "image/png",
        "x-wait-for-model": "true",
    }
)

task_queue = Queue()
state_lock = threading.Lock()
active_users = set()
prompt_cache = OrderedDict()


def cache_prompt(user_id: int, prompt: str) -> str:
    token = uuid.uuid4().hex[:8]
    with state_lock:
        prompt_cache[token] = (user_id, prompt)
        if len(prompt_cache) > MAX_PROMPT_CACHE_SIZE:
            prompt_cache.popitem(last=False)
    return token


def get_cached_prompt(token: str):
    with state_lock:
        return prompt_cache.get(token)


def build_welcome_markup() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📖 使用说明", callback_data="help"),
        InlineKeyboardButton("✨ 示例提示词", callback_data="example"),
    )
    return markup


def build_result_markup(token: str, user_id: int) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🔄 重新生成", callback_data=f"regen:{token}"),
        InlineKeyboardButton("🗑 删除图片", callback_data=f"del:{user_id}"),
    )
    return markup


def extract_error_detail(response: requests.Response) -> str:
    try:
        data = response.json()
        if isinstance(data, dict) and isinstance(data.get("error"), str):
            return data["error"][:200]
    except ValueError:
        pass
    return f"HTTP {response.status_code}"


def request_stable_diffusion(prompt: str) -> io.BytesIO:
    try:
        response = http_session.post(
            API_URL,
            json={"inputs": prompt},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.exceptions.Timeout as exc:
        logger.warning("Inference request timed out: %s", exc)
        raise RuntimeError("模型推理超时，请稍后重试。") from exc
    except requests.exceptions.RequestException as exc:
        logger.error("Inference request failed: %s", exc)
        raise RuntimeError("无法连接到推理服务，请稍后重试。") from exc

    if not response.ok:
        detail = extract_error_detail(response)
        logger.warning("Inference API returned %s: %s", response.status_code, detail)
        raise RuntimeError(f"推理接口返回错误（{detail}）")

    try:
        with Image.open(io.BytesIO(response.content)) as img:
            if img.mode not in ("RGB", "RGBA", "L"):
                img = img.convert("RGB")
            output = io.BytesIO()
            img.save(output, format="PNG")
            output.seek(0)
            output.name = "generated.png"
            return output
    except UnidentifiedImageError as exc:
        logger.error("Invalid image payload from inference API")
        raise RuntimeError("推理服务返回的数据不是有效图像。") from exc


def safe_delete_message(chat_id: int, message_id: int) -> None:
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass


def safe_update_status(chat_id: int, message_id: int, text: str) -> None:
    try:
        bot.edit_message_text(text, chat_id=chat_id, message_id=message_id)
    except Exception:
        pass


def format_caption(prompt: str) -> str:
    display_prompt = (
        f"{prompt[:MAX_CAPTION_PROMPT_LEN]}…"
        if len(prompt) > MAX_CAPTION_PROMPT_LEN
        else prompt
    )
    escaped_prompt = html.escape(display_prompt)
    return f"🎨 <b>生成完成</b>\n<blockquote>{escaped_prompt}</blockquote>"


def process_generation(
    chat_id: int,
    reply_to_id: int,
    status_msg_id: int,
    user_id: int,
    prompt: str,
    queued_ahead: bool,
) -> None:
    try:
        if queued_ahead:
            safe_update_status(chat_id, status_msg_id, "🎨 正在生成图像，请稍候…")
        bot.send_chat_action(chat_id, "upload_photo")
        photo = request_stable_diffusion(prompt)
        token = cache_prompt(user_id, prompt)
        bot.send_photo(
            chat_id,
            photo,
            caption=format_caption(prompt),
            reply_parameters=ReplyParameters(
                message_id=reply_to_id,
                allow_sending_without_reply=True,
            ),
            reply_markup=build_result_markup(token, user_id),
        )
        safe_delete_message(chat_id, status_msg_id)
    except Exception as exc:
        error_text = f"⚠️ <b>生成失败</b>\n{html.escape(str(exc))}"
        safe_update_status(chat_id, status_msg_id, error_text)
    finally:
        with state_lock:
            active_users.discard(user_id)


def worker_loop() -> None:
    while True:
        task = task_queue.get()
        try:
            process_generation(*task)
        finally:
            task_queue.task_done()


def enqueue_generation(chat_id: int, reply_to_id: int, user_id: int, prompt: str) -> bool:
    with state_lock:
        if user_id in active_users:
            return False
        active_users.add(user_id)
        position = len(active_users)

    queued_ahead = position > 1
    status_text = (
        f"⏳ 已加入生成队列，当前排第 <b>{position}</b> 位，请稍候…"
        if queued_ahead
        else "🎨 正在生成图像，请稍候…"
    )
    try:
        status_msg = bot.send_message(
            chat_id,
            status_text,
            reply_parameters=ReplyParameters(
                message_id=reply_to_id,
                allow_sending_without_reply=True,
            ),
        )
    except Exception:
        with state_lock:
            active_users.discard(user_id)
        raise

    task_queue.put((chat_id, reply_to_id, status_msg.message_id, user_id, prompt, queued_ahead))
    return True


HELP_TEXT = (
    "📖 <b>使用指南</b>\n\n"
    "发送以下命令即可根据提示词生成图像：\n"
    "<code>/sd 您的画面描述（建议使用英文）</code>\n\n"
    "💡 <b>提示：</b>每位用户同一时间可进行 1 个生图任务，完成后可继续提交。"
)

EXAMPLE_TEXT = (
    "✨ <b>示例提示词（点击即可复制）</b>\n\n"
    "• <code>/sd serene cyberpunk street in rain, neon reflections, 8k</code>\n\n"
    "• <code>/sd studio ghibli landscape, floating islands, golden hour</code>\n\n"
    "• <code>/sd minimalist isometric cozy room, warm lamp light, 3d render</code>"
)


@bot.message_handler(commands=["start"])
def send_welcome(message) -> None:
    welcome_text = (
        "👋 <b>欢迎使用 Stable Diffusion 绘图机器人</b>\n\n"
        "发送 <code>/sd 提示词</code> 即可快速生成 AI 图像。\n"
        "点击下方按钮查看详细说明或获取示例提示词："
    )
    bot.reply_to(message, welcome_text, reply_markup=build_welcome_markup())


@bot.message_handler(commands=["help"])
def send_help(message) -> None:
    bot.reply_to(message, HELP_TEXT)


@bot.message_handler(commands=["sd"])
def stablediffusion_command(message) -> None:
    if not message.from_user:
        return

    parts = (message.text or "").split(maxsplit=1)
    prompt = parts[1].strip() if len(parts) > 1 else ""
    if not prompt:
        bot.reply_to(
            message,
            "ℹ️ 请输入提示词，例如：\n<code>/sd a cute astronaut cat in space</code>",
        )
        return

    accepted = enqueue_generation(
        chat_id=message.chat.id,
        reply_to_id=message.message_id,
        user_id=message.from_user.id,
        prompt=prompt,
    )
    if not accepted:
        bot.reply_to(message, "⏳ 您已有一个任务正在生成或排队中，请等待完成后再试。")


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call) -> None:
    data = call.data or ""

    if data == "help":
        bot.answer_callback_query(call.id)
        if call.message:
            bot.send_message(call.message.chat.id, HELP_TEXT)
        return

    if data == "example":
        bot.answer_callback_query(call.id)
        if call.message:
            bot.send_message(call.message.chat.id, EXAMPLE_TEXT)
        return

    if data.startswith("regen:"):
        token = data.partition(":")[2]
        cached = get_cached_prompt(token)
        if not cached or not call.message:
            bot.answer_callback_query(
                call.id,
                "该提示词缓存已过期，请重新发送 /sd 命令。",
                show_alert=True,
            )
            return

        _, prompt = cached
        accepted = enqueue_generation(
            chat_id=call.message.chat.id,
            reply_to_id=call.message.message_id,
            user_id=call.from_user.id,
            prompt=prompt,
        )
        if accepted:
            bot.answer_callback_query(call.id, "已提交重新生成任务")
        else:
            bot.answer_callback_query(
                call.id,
                "您已有一个任务正在生成或排队中，请稍候。",
                show_alert=True,
            )
        return

    if data.startswith("del:"):
        owner_id_str = data.partition(":")[2]
        if str(call.from_user.id) != owner_id_str:
            bot.answer_callback_query(call.id, "仅发起该任务的用户可删除此图片。", show_alert=True)
            return
        bot.answer_callback_query(call.id, "已删除")
        if call.message:
            safe_delete_message(call.message.chat.id, call.message.message_id)


def main() -> None:
    worker = threading.Thread(target=worker_loop, daemon=True)
    worker.start()
    bot.remove_webhook()
    logger.info("Bot started polling.")
    bot.infinity_polling(timeout=20, long_polling_timeout=20)


if __name__ == "__main__":
    main()
