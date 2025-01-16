from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from collections import defaultdict
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")  # Kanal IDsi yoki username
ADMIN_ID =  os.getenv("ADMIN_ID")  # Admin ID raqami (uni almashtiring)




bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Telefon raqamni yuborish uchun tugma
def contact_request_button():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = KeyboardButton("📞 Telefon raqamni ulashish", request_contact=True)
    markup.add(button)
    return markup

# Tilga mos xabarlar
messages = {
    "uz": "✅ Siz muvaffaqiyatli ro'yxatdan o'tdingiz!",
    "ru": "✅ Вы успешно зарегистрировались!",
    "en": "✅ You have successfully registered!"
}

link_messages = {
    "uz": "Sizning taklif havolangiz: {link}",
    "ru": "Ваша пригласительная ссылка: {link}",
    "en": "Your invitation link: {link}"
}

# Foydalanuvchi ma'lumotlarini saqlash
user_language = {}
user_invite_links = {}
user_referrals = defaultdict(int)
user_info = {}

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    if message.from_user.id in user_info:
        # Agar foydalanuvchi allaqachon ro'yxatdan o'tgan bo'lsa
        lang = user_language.get(message.from_user.id, "uz")  # Default Uzbek
        link_message = link_messages[lang].format(link=user_invite_links[message.from_user.id])
        await message.answer("❗ Siz allaqachon ro'yxatdan o'tgansiz. \n" + link_message)
    else:
        await message.answer("📄 Iltimos, ism va familiyangizni kiriting:")

@dp.message_handler(lambda message: message.from_user.id not in user_info)
async def capture_name(message: types.Message):
    user_info[message.from_user.id] = {"name": message.text}
    await message.answer("📞 Telefon raqamingizni ulashing:", reply_markup=contact_request_button())

@dp.message_handler(content_types=types.ContentType.CONTACT)
async def handle_contact(message: types.Message):
    lang = user_language.get(message.from_user.id, "uz")  # Default Uzbek

    # Tekshirish: Agar foydalanuvchi avval ro'yxatdan o'tgan bo'lsa
    if message.contact.phone_number in [info.get("phone") for info in user_info.values()]:
        existing_user_id = next(uid for uid, info in user_info.items() if info.get("phone") == message.contact.phone_number)
        link_message = link_messages[lang].format(link=user_invite_links[existing_user_id])
        await message.answer("❗ Siz allaqachon ro'yxatdan o'tgansiz. Mana sizning taklif havolangiz:\n" + link_message)
        return

    # Yangi foydalanuvchi uchun ma'lumotlarni saqlash
    user_info[message.from_user.id]["phone"] = message.contact.phone_number
    await message.answer(messages[lang])

    # Takrorlanmas link yaratish
    try:
        invite_link = await bot.create_chat_invite_link(chat_id=CHANNEL_ID, member_limit=0, name=f"User {user_info[message.from_user.id]['name']}")
        user_invite_links[message.from_user.id] = invite_link.invite_link
        link_message = link_messages[lang].format(link=invite_link.invite_link)
        await message.answer(link_message)
    except Exception as e:
        await message.answer("❌ Kechirasiz, kanalga taklif havolasini yaratishda xatolik yuz berdi.")

@dp.chat_join_request_handler()
async def handle_new_member(update: types.ChatJoinRequest):
    inviter_id = None
    for user_id, invite_link in user_invite_links.items():
        if update.invite_link.invite_link == invite_link:
            inviter_id = user_id
            break

    if inviter_id:
        user_referrals[inviter_id] += 1
        lang = user_language.get(inviter_id, "uz")
        await bot.send_message(inviter_id, f"🎉 {update.from_user.first_name} kanalga sizning havolangiz orqali qo'shildi.\nJami takliflar: {user_referrals[inviter_id]}.")

@dp.message_handler(commands=['my_stats'])
async def my_stats(message: types.Message):
    if message.from_user.id in user_info:
        count = user_referrals.get(message.from_user.id, 0)
        await message.answer(f"📊 Siz taklif qilgan obunachilar soni: {count} ta.")
    else:
        await message.answer("ℹ️ Statistikani ko'rish uchun avval ro'yxatdan o'tishingiz kerak.")

@dp.message_handler(commands=['admin_panel'])
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        stats_message = "📊 Admin paneli:\n"
        for user_id, count in user_referrals.items():
            name = user_info.get(user_id, {}).get("name", "Noma'lum")
            stats_message += f"👤 {name}: {count} ta obunachi\n"
        await message.answer(stats_message)
    else:
        await message.answer("❌ Siz admin emassiz.")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
