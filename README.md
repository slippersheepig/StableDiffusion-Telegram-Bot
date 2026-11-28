# StableDiffusion Telegram Bot

搭配 [Hugging Face Inference API](https://huggingface.co/models) 使用的 Telegram 文生图机器人。

> [!TIP]
> 需注册 Hugging Face 账号，前往个人主页 **Settings -> Access Tokens** 生成具有推理调用权限的 Token 备用。

> [!NOTE]
> 默认适配 Stable Diffusion 等文生图（Text-to-Image）推理接口。

## 快速部署

在同一目录下创建 `.env` 与 `docker-compose.yml` 两个文件：

### 1. 配置环境变量 `.env`

```ini
HUGGINGFACE_TOKEN=hf_ABCDEFGHIJKLMNOPQRSTUVWXYZ
BOT_TOKEN=123456789:abcdefghijklmnopqrstuvwxyz
API_URL=https://router.huggingface.co/hf-inference/models/stabilityai/stable-diffusion-xl-base-1.0
```

| 变量名 | 是否必填 | 说明 |
| :--- | :---: | :--- |
| `HUGGINGFACE_TOKEN` | 必填 | Hugging Face Access Token |
| `BOT_TOKEN` | 必填 | Telegram Bot Token（通过 `@BotFather` 获取） |
| `API_URL` | 必填 | 模型推理 API 地址，可在模型详情页 **Deploy -> Inference API** 查看 |

### 2. 配置 `docker-compose.yml`

```yaml
services:
  sdbot:
    image: sheepgreen/sdbot # 或使用 GitHub 镜像 ghcr.io/slippersheepig/sdbot
    container_name: sdbot
    env_file:
      - .env
    restart: unless-stopped
```

> 兼容旧版挂载方式：也可继续使用 `volumes: ["./.env:/app/.env:ro"]`。

### 3. 启动服务

```bash
docker compose up -d
```

## 机器人指令

- `/start` — 启动机器人并打开快捷操作菜单
- `/help` — 查看指令使用说明
- `/sd <提示词>` — 根据提示词生成图像（支持重新生成与一键删除）
