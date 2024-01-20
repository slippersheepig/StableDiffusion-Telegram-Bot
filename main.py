import telebot
import requests
import numpy as np
import cv2
import io
import time  # 添加缺失的import语句
from decouple import config

# Load environment variables
BOT_TOKEN = config('BOT_TOKEN')
ALLOWED_USER = config('ALLOWED_USER').split(',')
ADMIN_USERS = config('ADMIN_USERS').split(',')
HUGGINGFACE_TOKEN = config('HUGGINGFACE_TOKEN')
API_URL = config('API_URL')
BOT_USE = config('BOT_USE')
TARGET_CHAT_ID = config('TARGET_CHAT_ID')

# Create bot
bot = telebot.TeleBot(BOT_TOKEN)

# Queue
queue = []

# Request to stable diffusion
headers = {"Authorization": f"Bearer {HUGGINGFACE_TOKEN}"}  # 修正此行代码

def diffusion(payload):
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.content

###############################################################
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Hi! I'm a bot for generating images with stable diffusion, write /help to output details")

###############################################################
@bot.message_handler(commands=['help'])
def send_Help(message):
    bot.reply_to(message, "Enter /stablediffusion for generating an image with your prompt")

#################################################################
@bot.message_handler(commands=["report"])
def report(message):
    global message_text
    if message.chat.id in ALLOWED_USER or (message.from_user.id in ALLOWED_USER and message.chat.type == "private"):  # 修正此行代码
        sobaka = message.from_user.username
        check = message.text
        check = check.replace("/report", "")
        check = check.replace("@BOT_USE", "")
        if check != "":
            bot.reply_to(message, "Message sent successfully")
            bot.send_message(chat_id=TARGET_CHAT_ID, text="Report:\n@" + sobaka + " : " + check)
        else:
            bot.reply_to(message, "The request cannot be blank.")
    else:
        bot.reply_to(message, "You have no access.")

#################################################################
@bot.message_handler(commands=['ad'])
def ad(message):
    global message_text
    if (message.from_user.id in ADMIN_USERS):  # 修正此行代码
        message_text = message.text
        message_text = message_text.replace("/ad", "")
        message_text = message_text.replace("@BOT_USE", "")
        users = 0
        bot.reply_to(message, 'ads are being sent...')
        for user in ALLOWED_USER:  # 修正此行代码
            time.sleep(5)
            bot.send_message(user, message_text)
            users += 1
        bot.reply_to(message, 'Ads sent successfully, number of recipients:' + str(users))
    else:
        bot.reply_to(message, 'You are not an administrator.')

#################################################################
@bot.message_handler(commands=['stablediffusion'])
def stablediffusion(message):
    global message_text
    if message.chat.id in ALLOWED_USER or (message.from_user.id in ALLOWED_USER and message.chat.type == 'private'):  # 修正此行代码
        use = message.from_user.username
        if use not in queue:  # 修正此行代码
            check = message.text.replace("/stablediffusion", "").replace("@BOT_USE", "").strip()
            if check != "":
                queue.append(use)
                bot.reply_to(message, 'Wait... \nYour position in the queue: {}'.format(len(queue)))  # 修正此行代码
                try:
                    image_bytes = diffusion({'inputs': check})
                    img_bytes = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
                    success, png_image = cv2.imencode('.png', img_bytes)
                    photo = io.BytesIO(png_image)
                    photo.seek(0)
                    bot.send_message(message.chat.id, text=f"Request: {check}\nStable Diffusion:")
                    bot.send_photo(message.chat.id, photo)
                    image_bytes = diffusion({"inputs": check})  # 修正此行代码
                    img_bytes = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
                    success, png_image = cv2.imencode('.png', img_bytes)
                    photo = io.BytesIO(png_image)
                    photo.seek(0)
                    bot.send_message(chat_id=TARGET_CHAT_ID, text=f"AI Model: Stable Diffusion \n@{use} {check}\nStable Diffusion:")
                    bot.send_photo(TARGET_CHAT_ID, photo)
                except Exception as e:
                    bot.reply_to(message, "Error: Admin is already working on fixing it")
                    bot.send_message(chat_id=TARGET_CHAT_ID, text="AI Model: Stability AI Stable Diffusion\ error: " + str(e))
                queue.remove(use)
            else:
                bot.reply_to(message, 'Request cannot be empty.')
        else:
            bot.reply_to(message, "You are already generating a query for this model, wait for completion.")
    else:
        bot.reply_to(message, 'You do not have access.')

################################################################
@bot.message_handler(commands=['queue'])
def queue_command(message):
    global queue
    if message.from_user.id in ADMIN_USERS:
        if len(queue) > 0:
            queue_list = "Users in queue:\n"
            queue_list_min = "Users in queue:\n"
            total_length = 0
            is_exceeding_length = False
            if len(queue) > 0:  # 修正此行代码
                queue_len = len(queue)  # 修正此行代码
                queue_users = ", ".join([f"@{user}" for user in queue])
                total_length += len(f"Queue for Stable Diffusion ({queue_len} {queue_users}\n")
                if total_length > 4000:
                    is_exceeding_length = True
                    queue_list_min += f"Queue for Stable Diffusion ({queue_len})\n"
                else:
                    queue_list_min += f"Queue for Stable Diffusion ({queue_len})\n"
                    queue_list += f"Queue for Stable Diffusion ({queue_len} {queue_users}\n")
            if is_exceeding_length:
                bot.reply_to(message, queue_list_min)
            else:
                bot.reply_to(message, queue_list)
        else:
            bot.reply_to(message, "All queues are empty.")
    else:
        bot.reply_to(message, "You are not an administrator.")

###############################################################
@bot.message_handler(commands=['add_id'])
def add_id(message):
    global message_text
    if (message.from_user.id in ADMIN_USERS):
        message_text = message.text
        message_text = message_text.replace("/add_id", "")
        ALLOWED_USER.append(message_text)  # 修正此行代码
        bot.reply_to(message, 'User ID successfully added')
    else:
        bot.reply_to(message, 'You are not an administrator.')

###############################################################
@bot.message_handler(commands=['ban'])
def ban(message):
    global message_text
    if (message.from_user.id in ADMIN_USERS):
        message_text = message.text
        message_text = message_text.replace("/ban", "")
        ALLOWED_USER.remove(message_text)  # 修正此行代码
        bot.reply_to(message, 'The user is banned, you can use the command /unban [ID]')
    else:
        bot.reply_to(message, 'You are not an administrator.')

###############################################################
@bot.message_handler(commands=['unban'])
def unban(message):
    global message_text
    if (message.from_user.id in ADMIN_USERS):
        message_text = message.text
        message_text = message_text.replace("/unban", "")
        ALLOWED_USER.append(message_text)  # 修正此行代码
        bot.reply_to(message, 'User is unbanned')
    else:
        bot.reply_to(message, 'You are not an administrator.')

###############################################################
def main():
    bot.polling()

if __name__ == "__main__":
    main()
