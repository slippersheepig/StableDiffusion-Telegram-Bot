import telebot
import requests
import numpy as np
import cv2
import io
from decouple import config
from queue import Queue
import time

# 常量
BOT_TOKEN = config('BOT_TOKEN')
HUGGINGFACE_TOKEN = config('HUGGINGFACE_TOKEN')
API_URL = config('API_URL')

# 创建机器人
bot = telebot.TeleBot(BOT_TOKEN)
bot.set_webhook()

# 队列
queue = Queue()

# 用户请求时间字典
user_last_request_time = {}

# 请求到stablediffusion
headers = {"Authorization": f"Bearer {HUGGINGFACE_TOKEN}"}

def stablediffusion(payload):
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        raise Exception(f"stablediffusion请求错误: {str(e)}")

def generate_image(message, user, prompt):
    try:
        # 发送 "upload_photo" 动作
        bot.send_chat_action(message.chat.id, "upload_photo")
        image_bytes = stablediffusion({'inputs': prompt})
        img_bytes = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        success, png_image = cv2.imencode('.png', img_bytes)
        photo = io.BytesIO(png_image)
        photo.seek(0)
        bot.send_message(message.chat.id, text=f"请求: {prompt}\nstablediffusion:")
        bot.send_photo(message.chat.id, photo)
    except Exception as e:
        bot.reply_to(message, f"生成图片错误: {str(e)}")
    finally:
        queue.get()  # 从队列中移除用户

# 增加频率限制函数
def check_request_limit(user):
    current_time = time.time()
    last_request_time = user_last_request_time.get(user, 0)
    time_since_last_request = current_time - last_request_time
    # 设置请求时间间隔为60秒
    request_interval = 60
    if time_since_last_request < request_interval:
        return False
    else:
        user_last_request_time[user] = current_time
        return True

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "嗨！我是一个用于生成stablediffusion图像的机器人，请输入 /help 以获取详细信息")

@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(message, "输入 /sd 以使用您的提示生成图像")

@bot.message_handler(commands=['sd'])
def stablediffusion_command(message):
    user = message.from_user.username
    if user not in queue.queue:
        prompt = message.text.replace("/sd", "").strip()
        if prompt:
            if check_request_limit(user):
                queue.put(user)
                bot.reply_to(message, f'请稍等... \n您在队列中的位置: {queue.qsize()}')
                generate_image(message, user, prompt)
            else:
                bot.reply_to(message, f"请求太频繁，请等待 {request_interval} 秒后再试.")
        else:
            bot.reply_to(message, '请求不能为空.')
    else:
        bot.reply_to(message, "您已经在生成此模型的查询，请等待完成.")

@bot.message_handler(commands=['queue'])
def queue_command(message):
    if not queue.empty():
        users_in_queue = ", ".join([f"@{user}" for user in queue.queue])
        bot.reply_to(message, f"在队列中的用户: {users_in_queue}")
    else:
        bot.reply_to(message, "所有队列都是空的.")

def main():
    bot.polling()
    
if __name__ == "__main__":
    main()
