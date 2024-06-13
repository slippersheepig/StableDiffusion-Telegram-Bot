import telebot
import requests
import numpy as np
import cv2
import io
import logging
from decouple import config
from queue import Queue
from threading import Lock
from time import sleep

# 设置日志
logging.basicConfig(level=logging.INFO)

# 常量
BOT_TOKEN = config('BOT_TOKEN')
HUGGINGFACE_TOKEN = config('HUGGINGFACE_TOKEN')
API_URL = config('API_URL')

if not BOT_TOKEN or not HUGGINGFACE_TOKEN or not API_URL:
    raise ValueError("请确保BOT_TOKEN, HUGGINGFACE_TOKEN和API_URL在环境变量中正确设置")

# 创建机器人
bot = telebot.TeleBot(BOT_TOKEN)
bot.set_webhook()

# 队列和锁
queue = Queue()
queue_lock = Lock()

# 请求到stablediffusion
headers = {"Authorization": f"Bearer {HUGGINGFACE_TOKEN}"}

def stablediffusion(payload, retries=3):
    for attempt in range(retries):
        try:
            response = requests.post(API_URL, headers=headers, json=payload)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                logging.warning(f"stablediffusion请求错误: {str(e)}，重试中... ({attempt+1}/{retries})")
                sleep(2)  # 等待一段时间后重试
            else:
                logging.error(f"stablediffusion请求错误: {str(e)}，重试次数用尽")
                raise Exception(f"stablediffusion请求错误: {str(e)}")

def generate_image(message, user, prompt):
    try:
        # 发送 "upload_photo" 动作
        bot.send_chat_action(message.chat.id, "upload_photo")
        image_bytes = stablediffusion({'inputs': prompt})
        img_bytes = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        success, png_image = cv2.imencode('.png', img_bytes)
        if not success:
            raise ValueError("图像编码失败")
        photo = io.BytesIO(png_image)
        photo.seek(0)
        bot.send_message(message.chat.id, text=f"请求: {prompt}\nstablediffusion:")
        bot.send_photo(message.chat.id, photo)
    except Exception as e:
        bot.reply_to(message, f"生成图片错误: {str(e)}")
        logging.error(f"生成图片错误: {str(e)}")
    finally:
        with queue_lock:
            if user in queue.queue:
                queue.get()  # 从队列中移除用户
        photo.close()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "嗨！我是一个用于生成stablediffusion图像的机器人，请输入 /help 以获取详细信息")

@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(message, "输入 /sd 以使用您的提示生成图像")

@bot.message_handler(commands=['sd'])
def stablediffusion_command(message):
    user = message.from_user.username
    if not user:
        bot.reply_to(message, "无法获取用户名，请确保您的帐户有用户名")
        return
    
    with queue_lock:
        if user not in queue.queue:
            prompt = message.text.replace("/sd", "").strip()
            if prompt:
                queue.put(user)
                bot.reply_to(message, f'请稍等... \n您在队列中的位置: {queue.qsize()}')
                generate_image(message, user, prompt)
            else:
                bot.reply_to(message, '请求不能为空.')
        else:
            bot.reply_to(message, "您已经在生成此模型的查询，请等待完成.")

def main():
    bot.polling(none_stop=True)

if __name__ == "__main__":
    main()
