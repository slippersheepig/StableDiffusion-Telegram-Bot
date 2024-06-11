搭配[Hugging Face](https://huggingface.co/models)使用的图片生成机器人
> [!TIP]
> 需注册Hugging Face账号，在个人信息profile处点击settings-access tokens生成api复制备用

> [!NOTE]
> 该代码仅兼容StableDiffusion模型，其他模型未测试

`.env`
```bash
HUGGINGFACE_TOKEN=hf_ABCDEFGHIJKLMNOPQRSTUVWXYZ
BOT_TOKEN=123456789:abcdefghijklmnopqrstuvwxyz
API_URL=https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2-1
```
（必填）HUGGINGFACEHUB_TOKEN：填入tip提到的api  
（必填）BOT_TOKEN：电报机器人token  
（必填）API_URL：调用模型的API链接，可在HuggingFace的模型详情页面右上方Deploy-Inference API查看  
`docker-compose.yml`
```bash
services:
  chatgpt:
    image: sheepgreen/sdbot #或使用github镜像ghcr.io/slippersheepig/sdbot
    container_name: sdbot
    volumes:
      - ./.env:/app/.env
    restart: always
```
以上两个文件放同一目录，然后运行`docker-compose up -d`命令即可
