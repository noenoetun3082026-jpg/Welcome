import os
import io
import asyncio
import logging
from datetime import datetime
from aiohttp import web
from PIL import Image, ImageDraw, ImageFont
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, BufferedInputFile

# Logging Configuration
logging.basicConfig(level=logging.INFO)

# Telegram Bot Token (Render Environment Variable မှ ရယူမည်)
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# 🎨 Welcome Banner/Card ဖန်တီးပေးသည့် Function
async def create_welcome_card(bot: Bot, user_id: int, full_name: str, group_name: str) -> io.BytesIO:
    # 1. Background Image ဖန်တီးခြင်း (Dark Theme: 800x450)
    width, height = 800, 450
    background = Image.new("RGB", (width, height), color=(20, 24, 33))
    draw = ImageDraw.Draw(background)

    # 2. အဖွဲ့ဝင်သစ်၏ Profile Picture ကို Telegram ထံမှ ဖမ်းယူခြင်း
    avatar = None
    try:
        user_photos = await bot.get_user_profile_photos(user_id, limit=1)
        if user_photos.total_count > 0:
            file_id = user_photos.photos[0][-1].file_id
            file = await bot.get_file(file_id)
            file_path = file.file_path
            
            # Photo ကို Bytes အဖြစ် ဒေါင်းလုဒ်ဆွဲယူခြင်း
            photo_bytes = await bot.download_file(file_path)
            avatar = Image.open(photo_bytes).convert("RGBA")
            avatar = avatar.resize((160, 160))
    except Exception as e:
        logging.error(f"Error fetching profile photo: {e}")

    # Profile Photo မရှိပါက သို့မဟုတ် Privacy ပိတ်ထားပါက အရန် Gray Background သုံးခြင်း
    if not avatar:
        avatar = Image.new("RGBA", (160, 160), color=(100, 100, 100))

    # Profile Photo ကို စက်ဝိုင်းပုံစံ ကတ်ဖြတ်ခြင်း (Circular Mask)
    mask = Image.new("L", (160, 160), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, 160, 160), fill=255)

    # Background ပေါ်သို့ Profile Photo တင်ခြင်း (Center နေရာ)
    avatar_x = (width - 160) // 2
    background.paste(avatar, (avatar_x, 40), mask)

    # စက်ဝိုင်း အနားသတ် အဖြူရောင် လိုင်းဆွဲခြင်း
    draw.ellipse((avatar_x - 3, 37, avatar_x + 163, 203), outline=(255, 255, 255), width=3)

    # 3. စာသားများ ရေးသားခြင်း
    current_date = datetime.now().strftime("%d.%m.%y")
    font_large = ImageFont.load_default()
    
    # Header စာသားများ
    draw.text((width // 2, 230), f"Welcome to {group_name}", fill=(255, 255, 255), anchor="mm", font=font_large)
    draw.text((width // 2, 260), f"Hello 👋 {full_name}", fill=(72, 160, 255), anchor="mm", font=font_large)

    # User Info အချက်အလက်များ
    info_text = (
        f"User ID : {user_id}\n"
        f"Username : @{full_name.replace(' ', '_')}\n"
        f"Date Joined : {current_date}"
    )
    draw.multiline_text((width // 2, 330), info_text, fill=(200, 200, 200), anchor="mm", align="center", font=font_large)

    # Image ကို Memory (BytesIO) ထဲသိမ်း၍ Return ပြန်ပေးခြင်း
    output = io.BytesIO()
    background.save(output, format="PNG")
    output.seek(0)
    return output

# 📩 Welcome Message Handler
@dp.message(F.new_chat_members)
async def welcome_new_member(message: Message):
    for member in message.new_chat_members:
        if member.id == bot.id:
            continue
        
        full_name = member.full_name or "New Member"
        user_id = member.id
        username = f"@{member.username}" if member.username else "မရှိပါ"
        group_name = message.chat.title or "Group"
        current_date = datetime.now().strftime("%d.%m.%y")

        # Profile Picture ပါသော Welcome Card ဖန်တီးခြင်း
        image_bytes = await create_welcome_card(bot, user_id, full_name, group_name)
        input_file = BufferedInputFile(image_bytes.read(), filename="welcome.png")

        # စာသား ဖော်ပြချက် (Caption Text)
        caption_text = (
            f"Hello 👋 **{full_name}** .\n\n"
            f"🔺 Welcome to 🔺\n"
            f"**{group_name}** .\n\n"
            f"📑 **User Info**\n"
            f"🟢 **ID** : `{user_id}`\n"
            f"🟢 **Full Name** : **{full_name}**\n"
            f"🟢 **Username** : {username}\n"
            f"🟢 **Date** : `{current_date}`"
        )

        # Photo ကို Group ထဲသို့ ပို့ပေးခြင်း
        await message.answer_photo(
            photo=input_file,
            caption=caption_text,
            parse_mode="Markdown"
        )

# Render Web Server Health Check (Free Plan မရပ်သွားစေရန်)
async def handle(request):
    return web.Response(text="Welcome Bot is running live!")

async def main():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    print("Welcome Bot with PF Fetcher is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
