import telebot
import requests
import numpy as np
import cv2
import io
import time
from decouple import config

# Load environment variables
BOT_TOKEN = config('BOT_TOKEN')
HUGGINGFACE_TOKEN = config('HUGGINGFACE_TOKEN')
API_URL = config('API_URL')

# Create bot
bot = telebot.TeleBot(BOT_TOKEN)
bot.set_webhook()

# Queue
queue = []

# Request to stable diffusion
headers = {"Authorization": f"Bearer {HUGGINGFACE_TOKEN}"}

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
@bot.message_handler(commands=['stablediffusion'])
def stablediffusion(message):
    use = message.from_user.username
    if use not in queue:
        check = (
            message.text.replace("/stablediffusion", "")
            .replace("@BOT_USE", "")
            .strip()
        )
        if check != "":
            queue.append(use)
            bot.reply_to(message, 'Wait... \nYour position in the queue: {}'.format(len(queue)))
            try:
                image_bytes = diffusion({'inputs': check})
                img_bytes = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
                success, png_image = cv2.imencode('.png', img_bytes)
                photo = io.BytesIO(png_image)
                photo.seek(0)
                bot.send_message(message.chat.id, text=f"Request: {check}\nStable Diffusion:")
                bot.send_photo(message.chat.id, photo)
            except Exception as e:
                bot.reply_to(message, "Error: Admin is already working on fixing it")
                bot.send_message(chat_id=TARGET_CHAT_ID, text="AI Model: Stability AI Stable Diffusion\ error: " + str(e))
            queue.remove(use)
        else:
            bot.reply_to(message, 'Request cannot be empty.')
    else:
        bot.reply_to(message, "You are already generating a query for this model, wait for completion.")

################################################################
@bot.message_handler(commands=['queue'])
def queue_command(message):
    if len(queue) > 0:
        queue_list = "Users in queue:\n"
        queue_list_min = "Users in queue:\n"
        total_length = 0
        is_exceeding_length = False
        if len(stabllediffusion_queue) > 0:
            stabllediffusion_queue_len = len(queue)
            queue_users = ", ".join([f"@{user}" for user in queue])
            total_length += len(f"Queue for Stable Diffusion ({queue_len} {queue_users}\n")
            if total_length > 4000:
                is_exceeding_length = True
                queue_list_min += f"Queue for Stable Diffusion ({queue_len})\n"
            else:
                queue_list_min += f"Queue for Stable Diffusion ({queue_len})\n"
                queue_list += f"Queue for Stable Diffusion ({queue_len} {queue_users})\n"
        if is_exceeding_length:
            bot.reply_to(message, queue_list_min)
        else:
            bot.reply_to(message, queue_list)
    else:
        bot.reply_to(message, "All queues are empty.")

###############################################################
def main():
    bot.polling()

if __name__ == "__main__":
    main()
