import os
import psycopg2
import json
import random
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Bot tokenini o'rnating
API_TOKEN = '7327999954:AAH3syk5kiNsH84VS3NzxM5UysQcxPbwLeo'

def get_db_connection():
    """PostgreSQL ulanishini olish"""
    return psycopg2.connect(os.environ['DATABASE_URL'])

def init_db():
    """Ma'lumotlar bazasini ishga tushirish"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                data JSONB NOT NULL
            )
        ''')
        conn.commit()
    except Exception as e:
        print(f"Xatolik yuz berdi: {e}")
    finally:
        conn.close()

# Botni ishga tushirish
bot = Bot(token=os.environ['API_TOKEN'])
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Dastur boshida ma'lumotlar bazasini ishga tushirish
init_db()

def load_user_data():
    """Barcha foydalanuvchi ma'lumotlarini yuklash"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT user_id, data FROM users')
        return {row[0]: row[1] for row in cursor.fetchall()}
    except Exception as e:
        print(f"Xatolik yuz berdi: {e}")
        return {}
    finally:
        conn.close()

def save_user_data(data):
    """Foydalanuvchi ma'lumotlarini saqlash (butun lug'atni yangilash)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Avval barcha eski ma'lumotlarni o'chirish
        cursor.execute('DELETE FROM users')
        
        # Yangi ma'lumotlarni qo'shish
        for user_id, user_data in data.items():
            cursor.execute(
                'INSERT INTO users (user_id, data) VALUES (%s, %s)',
                (user_id, user_data)
            )
        
        conn.commit()
    except Exception as e:
        print(f"Xatolik yuz berdi: {e}")
        conn.rollback()
    finally:
        conn.close()
# O'yin holatlari
class GameStates(StatesGroup):
    MAIN_MENU = State()
    EXPLORING = State()
    INVENTORY = State()
    SHOP = State()
    UPGRADE = State()
    COMBAT = State()
    COMBAT_SELECT = State()  # <-- Yangi holat
    MISSION = State()

# Do'kon buyumlari
shop_items = {
    1: {"name": "Temir qilich", "type": "weapon", "damage": "15-25", "price": 200},
    2: {"name": "Sehrli tayoq", "type": "weapon", "damage": "10-20", "mana": "+5", "price": 300},
    3: {"name": "Charm zirh", "type": "armor", "defense": 10, "price": 150},
    4: {"name": "Hayot eliksiri", "type": "potion", "effect": "+25 HP", "price": 50},
    5: {"name": "Kuch eliksiri", "type": "potion", "effect": "strength", "duration": 3, "price": 150},
    6: {"name": "Qarshilik eliksiri", "type": "potion", "effect": "resistance", "duration": 3, "price": 120},
    7: {"name": "Tiklanish eliksiri", "type": "potion", "effect": "regeneration", "duration": 5, "price": 200},
    8: {"name": "Hayot kuchaytirgich", "type": "potion", "effect": "health_boost", "duration": 0, "price": 250},
}

# Bosslar
bosses = {
    1: {"name": "Qal'a qo'riqchisi", "hp": 100, "damage": "10-15", "reward": 150, "min_level": 1},
    2: {"name": "Qora jodugar", "hp": 400, "damage": "20-30", "reward": 600, "min_level": 2},
    3: {"name": "Yovuz shahzoda", "hp": 1600, "damage": "40-60", "reward": 2400, "min_level": 3},
    4: {"name": "Ajdaho", "hp": 6400, "damage": "80-120", "reward": 9600, "min_level": 4},
    5: {"name": "Qora sehrgar", "hp": 25600, "damage": "160-240", "reward": 38400, "min_level": 5}
}

# Missiyalar
missions = {
    "beginner": {
        "name": "Boshqotirma qo'riqchisini yengish",
        "reward": 100,
        "enemy_hp": 50,
        "enemy_damage": "5-10",
        "description": "Qal'a darvozasini qo'riqlayotgan qo'riqchini yengib, darvozadan kirishga urining."
    },
    "advanced": {
        "name": "Qora jodugar bilan jang",
        "reward": 300,
        "enemy_hp": 120,
        "enemy_damage": "15-25",
        "description": "Qal'aning maxfiy xonasida yashovchi qora jodugarga qarshi kurashing."
    },
    "secret": {
        "name": "Afsonaviy ajdaho",
        "reward": 1000,
        "enemy_hp": 300,
        "enemy_damage": "30-50",
        "description": "Faqat haqiqiy qahramonlar bu jangda g'alaba qozonishi mumkin!",
        "required_level": 3
    }
}

async def apply_effect(user_id, effect_type, duration):
    user_data = load_user_data()
    user_stats = user_data.get(user_id, {})
    if not user_stats:
        return
    
    if "active_effects" not in user_stats:
        user_stats["active_effects"] = {}
    
    user_stats["active_effects"][effect_type] = duration
    user_data[user_id] = user_stats
    save_user_data(user_data)

async def process_effects(user_id):
    user_data = load_user_data()
    user_stats = user_data.get(user_id, {})
    if not user_stats or not user_stats.get("active_effects"):
        return []
    
    effects = user_stats["active_effects"]
    messages = []
    
    for effect in list(effects.keys()):
        effects[effect] -= 1
        
        if effect == "regeneration":
            heal = 10
            user_stats["hp"] = min(user_stats["max_hp"], user_stats["hp"] + heal)
            messages.append(f"♻️ Regeneratsiya: +{heal} HP")
        elif effect == "strength":
            messages.append("💪 Kuch eliksiri faol")
        elif effect == "resistance":
            messages.append("🛡️ Qarshilik eliksiri faol")
        elif effect == "health_boost":
            if effects[effect] == 0:
                user_stats["max_hp"] += 20
                user_stats["hp"] += 20
                messages.append("❤️ Hayot kuchaytirgich ta'sir ko'rsatmoqda")
        
        if effects[effect] <= 0:
            del effects[effect]
    
    user_data[user_id] = user_stats
    save_user_data(user_data)
    return messages

# Asosiy menyu tugmalari
def main_menu_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton('🏰 Asosiy menyu'))
    keyboard.add(KeyboardButton('⚔️ Jang'), KeyboardButton('🔍 Ekspeditsiya'))
    keyboard.add(KeyboardButton('🛒 Do\'kon'), KeyboardButton('🎒 Inventar'))
    keyboard.add(KeyboardButton('📊 Statistika'), KeyboardButton('🏆 Reyting'))
    return keyboard

# Jang menyusi
def combat_menu_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton('1. Hujum qilish'), KeyboardButton('2. Maxsus hujum'))
    keyboard.add(KeyboardButton('3. Doridan foydalanish'), KeyboardButton('4. Qochish'))
    keyboard.add(KeyboardButton('🏰 Asosiy menyu'))
    return keyboard

# Boshlash
@dp.message_handler(commands=['start'], state="*")
async def start_game(message: types.Message):
    user_id = str(message.from_user.id)
    user_data = load_user_data()
    
    if user_id not in user_data:
        user_data[user_id] = {
            "name": message.from_user.full_name,
            "level": 1,
            "xp": 0,
            "max_hp": 100,
            "hp": 100,
            "max_mana": 50,
            "mana": 50,
            "gold": 50,
            "weapon": {"name": "Oddiy qilich", "damage": "5-10", "level": 1, "upgrade_cost": 100},
            "armor": {"name": "Oddiy zirh", "defense": 5},
            "inventory": [],
            "missions_completed": [],
            "bosses_defeated": [],
            "active_effects": {}
        }
        save_user_data(user_data)
    else:
        # Agar foydalanuvchi allaqachon mavjud bo'lsa, kerakli maydonlarni tekshirish
        user_stats = user_data[user_id]
        if 'name' not in user_stats:
            user_stats['name'] = message.from_user.full_name
        if 'inventory' not in user_stats:
            user_stats['inventory'] = []
        if 'missions_completed' not in user_stats:
            user_stats['missions_completed'] = []
        if 'bosses_defeated' not in user_stats:
            user_stats['bosses_defeated'] = []
        if 'active_effects' not in user_stats:
            user_stats['active_effects'] = {}
        
        save_user_data(user_data)
    
    await GameStates.MAIN_MENU.set()
    await message.answer(
        "🎮 Qahramonlik sarguzashtlariga xush kelibsiz!\n"
        "Quyidagi menyulardan birini tanlang:",
        reply_markup=main_menu_keyboard()
    )
# Asosiy menyu
@dp.message_handler(text='🏰 Asosiy menyu', state="*")
async def main_menu(message: types.Message):
    await GameStates.MAIN_MENU.set()
    await message.answer("Asosiy menyu:", reply_markup=main_menu_keyboard())

# Ekspeditsiya
@dp.message_handler(text='🔍 Ekspeditsiya', state="*")
async def explore(message: types.Message):
    user_id = str(message.from_user.id)
    user_data = load_user_data()
    user_stats = user_data.get(user_id, {})
    
    if not user_stats:
        await message.answer("⚠️ Iltimos, avval /start buyrug'ini bering!", reply_markup=main_menu_keyboard())
        return
    
    events = [
    ("Siz yo'lda xazina topdingiz! +50 gold", lambda s: s.update({"gold": s.get("gold", 0) + 50})),
    ("Siz dushman tomonidan hujumga uchradingiz! -10 HP", lambda s: s.update({"hp": max(1, s.get("hp", 100) - 10)})),
    ("Siz sehrli manba topdingiz! +20 Mana", lambda s: s.update({"mana": min(s.get("max_mana", 50), s.get("mana", 0) + 20)})),
    ("Siz hech narsa topolmadingiz...", lambda s: s),
    ("Siz tajribali jangchi bilan uchrashdingiz! +10 XP", lambda s: s.update({"xp": s.get("xp", 0) + 10}))
]
    
    event_text, event_func = random.choice(events)
    event_func(user_stats)
    
    # XP tekshirish va daraja oshirish
    if user_stats["xp"] >= user_stats["level"] * 100:
        user_stats["level"] += 1
        user_stats["max_hp"] += 20
        user_stats["max_mana"] += 10
        user_stats["hp"] = user_stats["max_hp"]
        user_stats["mana"] = user_stats["max_mana"]
        level_up_msg = f"\n\n🎉 Tabriklaymiz! Siz {user_stats['level']} darajaga ko'tarildingiz!"
    else:
        level_up_msg = ""
    
    user_data[user_id] = user_stats
    save_user_data(user_data)
    
    await message.answer(f"🔍 Ekspeditsiya natijasi:\n\n{event_text}{level_up_msg}", reply_markup=main_menu_keyboard())
@dp.message_handler(text='⚔️ Jang', state="*")
async def start_combat(message: types.Message):
    user_id = str(message.from_user.id)
    user_data = load_user_data()
    user_stats = user_data.get(user_id, {})
    
    if not user_stats:
        await message.answer("⚠️ Iltimos, avval /start buyrug'ini bering!", reply_markup=main_menu_keyboard())
        return
    
    # Bosslarni ro'yxatini tayyorlash
    boss_list = []
    for boss_id, boss in bosses.items():
        # Foydalanuvchi darajasi yetarlimi yoki yo'qmi tekshirish
        if boss["min_level"] <= user_stats["level"]:
            # Boss allaqachon yengilganmi tekshirish
            defeated = boss_id in user_stats.get("bosses_defeated", [])
            boss_list.append((boss_id, boss, defeated))
    
    if not boss_list:
        await message.answer("⚠️ Siz hali hech qanday bossga hujum qila olmaysiz!", reply_markup=main_menu_keyboard())
        return
    
    # Bosslarni tanlash uchun klaviatura yaratish
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    for boss_id, boss, defeated in boss_list:
        status = "✅" if defeated else "❌"
        keyboard.add(KeyboardButton(f"{boss_id}. {boss['name']} (Lvl {boss['min_level']}) {status}"))
    
    keyboard.add(KeyboardButton('🏰 Asosiy menyu'))
    
    await GameStates.COMBAT_SELECT.set()
    await message.answer(
        "⚔️ Jang qilish uchun bossni tanlang:\n"
        "✅ - allaqachon yengilgan\n"
        "❌ - hali yengilmagan",
        reply_markup=keyboard
    )

@dp.message_handler(state=GameStates.COMBAT_SELECT)
async def select_boss(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    user_data = load_user_data()
    user_stats = user_data.get(user_id, {})
    
    if not user_stats:
        await message.answer("⚠️ Iltimos, avval /start buyrug'ini bering!", reply_markup=main_menu_keyboard())
        return
    
    # Asosiy menyuga qaytish
    if message.text == '🏰 Asosiy menyu':
        await GameStates.MAIN_MENU.set()
        await message.answer("Asosiy menyu:", reply_markup=main_menu_keyboard())
        return
    
    # Boss ID sini olish
    try:
        boss_id = int(message.text.split('.')[0])
        boss = bosses.get(boss_id)
        
        if not boss:
            await message.answer("⚠️ Noto'g'ri boss raqami!", reply_markup=main_menu_keyboard())
            return
        
        # Foydalanuvchi darajasi yetarlimi tekshirish
        if boss["min_level"] > user_stats["level"]:
            await message.answer(
                f"⚠️ Ushbu bossga jang qilish uchun siz kamida {boss['min_level']} darajada bo'lishingiz kerak!",
                reply_markup=main_menu_keyboard()
            )
            return
        
        # Jang ma'lumotlarini saqlash
        user_stats["combat"] = {
            "boss_id": boss_id,
            "enemy_hp": boss["hp"],
            "enemy_max_hp": boss["hp"],
            "enemy_damage": boss["damage"],
            "reward": boss["reward"]
        }
        
        user_data[user_id] = user_stats
        save_user_data(user_data)
        
        effect_msgs = await process_effects(user_id)
        effect_text = "\n".join(effect_msgs) + "\n\n" if effect_msgs else ""
        
        await GameStates.COMBAT.set()
        await message.answer(
            f"{effect_text}"
            f"⚔️ {boss['name']} bilan jang! ⚔️\n\n"
            f"❤️ Sizning HP: {user_stats['hp']}/{user_stats['max_hp']}\n"
            f"✨ Mana: {user_stats['mana']}/{user_stats['max_mana']}\n"
            f"☠️ Dushman HP: {boss['hp']}/{boss['hp']}\n\n"
            "Jang tanlovlari:",
            reply_markup=combat_menu_keyboard()
        )
    
    except Exception as e:
        await message.answer(f"⚠️ Xatolik yuz berdi: {str(e)}", reply_markup=main_menu_keyboard())
# Jang logikasi
@dp.message_handler(state=GameStates.COMBAT)
async def combat_handler(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    user_data = load_user_data()
    user_stats = user_data.get(user_id, {})
    combat_stats = user_stats.get("combat", {})
    
    if not combat_stats:
        await message.answer("⚠️ Jang ma'lumotlari topilmadi! /start bilan qayta boshlang.", reply_markup=main_menu_keyboard())
        return
    
    boss_id = combat_stats["boss_id"]
    boss = bosses[boss_id]
    enemy_hp = combat_stats["enemy_hp"]
    
    # Effektlarni qayta ishlash
    effect_msgs = await process_effects(user_id)
    effect_text = "\n".join(effect_msgs) + "\n\n" if effect_msgs else ""
    
    # Tanlovni qayta ishlash
    choice = message.text
    
    if choice == '1. Hujum qilish':
        # Oddiy hujum
        min_dmg, max_dmg = map(int, user_stats["weapon"]["damage"].split('-'))
        damage = random.randint(min_dmg, max_dmg)
        
        # Kuch eliksiri tekshirish
        if "strength" in user_stats.get("active_effects", {}):
            damage = int(damage * 1.5)
        
        enemy_hp -= damage
        combat_stats["enemy_hp"] = enemy_hp
        
        # Dushman javobi
        enemy_min, enemy_max = map(int, combat_stats["enemy_damage"].split('-'))
        enemy_damage = random.randint(enemy_min, enemy_max)
        
        # Qarshilik eliksiri tekshirish
        if "resistance" in user_stats.get("active_effects", {}):
            enemy_damage = int(enemy_damage * 0.7)
        
        # Zirh himoyasi
        defense = user_stats["armor"].get("defense", 0)
        user_stats["hp"] -= max(0, enemy_damage - defense)
        
        response = [
            f"{effect_text}",
            f"⚔️ Siz {damage} zarar yetkazdingiz!",
            f"☠️ Dushman sizga {enemy_damage} zarar yetkazdi!",
            ""
        ]
    
    elif choice == '2. Maxsus hujum' and user_stats["mana"] >= 10:
        # Maxsus hujum
        user_stats["mana"] -= 10
        damage = random.randint(20, 30)
        
        # Kuch eliksiri tekshirish
        if "strength" in user_stats.get("active_effects", {}):
            damage = int(damage * 1.5)
        
        enemy_hp -= damage
        combat_stats["enemy_hp"] = enemy_hp
        
        response = [
            f"{effect_text}",
            f"✨ Maxsus hujum! {damage} zarar yetkazdingiz!",
            f"☠️ Dushman sizga 0 zarar yetkazdi (hujumni blokladingiz)!",
            ""
        ]
    
    elif choice == '3. Doridan foydalanish':
        # Doridan foydalanish
        potions = [item for item in user_stats["inventory"] if item.get("type") == "potion"]
        if potions:
            potion = potions[0]
            user_stats["inventory"].remove(potion)
            
            if "effect" in potion:
                if potion["effect"] == "+25 HP":
                    heal = 25
                    user_stats["hp"] = min(user_stats["max_hp"], user_stats["hp"] + heal)
                    response = [f"{effect_text}🧪 Doridan foydalandingiz! +{heal} HP", ""]
                else:
                    await apply_effect(user_id, potion["effect"], potion.get("duration", 3))
                    response = [f"{effect_text}🧪 {potion['name']} ta'siri faollashdi!", ""]
            else:
                response = [f"{effect_text}⚠️ Dorida xatolik!", ""]
        else:
            response = [f"{effect_text}⚠️ Sizda dorilar yo'q!", ""]
    
    elif choice == '4. Qochish':
        # Qochish
        if random.random() < 0.5:
            await GameStates.MAIN_MENU.set()
            await message.answer("🏃‍♂️ Qochishga muvaffaq bo'ldingiz! Asosiy menyuga qaytdingiz.", reply_markup=main_menu_keyboard())
            return
        else:
            response = [f"{effect_text}⚠️ Qochishga urinish muvaffaqiyatsiz yakunlandi!", ""]
    else:
        await message.answer("⚠️ Noto'g'ri tanlov! Qayta urinib ko'ring.", reply_markup=combat_menu_keyboard())
        return
    
    # Jang natijasi
    if enemy_hp <= 0:
        # G'alaba
        reward = combat_stats["reward"]
        user_stats["gold"] += reward
        user_stats["xp"] += reward // 2
        
        # Bossni yengilganlar ro'yxatiga qo'shish
        if "bosses_defeated" not in user_stats:
            user_stats["bosses_defeated"] = []
        user_stats["bosses_defeated"].append(boss_id)
        
        # XP tekshirish va daraja oshirish
        level_up_msg = ""
        if user_stats["xp"] >= user_stats["level"] * 100:
            user_stats["level"] += 1
            user_stats["max_hp"] += 20
            user_stats["max_mana"] += 10
            user_stats["hp"] = user_stats["max_hp"]
            user_stats["mana"] = user_stats["max_mana"]
            level_up_msg = f"\n🎉 Tabriklaymiz! Siz {user_stats['level']} darajaga ko'tarildingiz!"
        
        user_data[user_id] = user_stats
        save_user_data(user_data)
        
        await GameStates.MAIN_MENU.set()
        await message.answer(
            f"{effect_text}"
            f"🎉 G'alaba! {boss['name']}ni yengdingiz!\n"
            f"💰 {reward} gold qozondingiz!\n"
            f"⭐ +{reward//2} XP{level_up_msg}",
            reply_markup=main_menu_keyboard()
        )
        return
    elif user_stats["hp"] <= 0:
        # Mag'lubiyat
        user_stats["hp"] = 1  # O'limdan qutulish
        user_data[user_id] = user_stats
        save_user_data(user_data)
        
        await GameStates.MAIN_MENU.set()
        await message.answer(
            f"{effect_text}"
            "☠️ Siz yutqazdingiz! Qutulib qoldingiz...\n"
            "Asosiy menyuga qaytdingiz.",
            reply_markup=main_menu_keyboard()
        )
        return
    
    # Jang davom etmoqda
    user_data[user_id] = user_stats
    save_user_data(user_data)
    
    response.extend([
        f"❤️ Sizning HP: {user_stats['hp']}/{user_stats['max_hp']}",
        f"✨ Mana: {user_stats['mana']}/{user_stats['max_mana']}",
        f"☠️ Dushman HP: {enemy_hp}/{combat_stats['enemy_max_hp']}",
        "",
        "Keyingi harakatni tanlang:"
    ])
    
    await message.answer("\n".join(response), reply_markup=combat_menu_keyboard())

# Do'kon
@dp.message_handler(text='🛒 Do\'kon', state="*")
async def shop(message: types.Message):
    user_id = str(message.from_user.id)
    user_data = load_user_data()
    user_stats = user_data.get(user_id, {})
    
    if not user_stats:
        await message.answer("⚠️ Iltimos, avval /start buyrug'ini bering!", reply_markup=main_menu_keyboard())
        return
    
    shop_text = ["🛒 Do'kon - Quyidagi buyumlarni sotib olishingiz mumkin:", ""]
    
    for item_id, item in shop_items.items():
        item_info = [
            f"{item_id}. {item['name']} - {item['price']} gold",
            f"Turi: {item['type']}",
        ]
        
        if item["type"] == "weapon":
            item_info.append(f"Damage: {item['damage']}")
        elif item["type"] == "armor":
            item_info.append(f"Defense: +{item['defense']}")
        elif item["type"] == "potion":
            item_info.append(f"Ta'siri: {item['effect']}")
        
        shop_text.append("\n".join(item_info))
        shop_text.append("")
    
    shop_text.append(f"💰 Sizda {user_stats.get('gold', 0)} gold bor")
    shop_text.append("Buyum sotib olish uchun /buy_[raqam] buyrug'ini yuboring")
    
    await GameStates.SHOP.set()
    await message.answer("\n".join(shop_text), reply_markup=main_menu_keyboard())

# Buyum sotib olish
@dp.message_handler(lambda m: m.text and m.text.startswith('/buy_'), state=GameStates.SHOP)
async def buy_item(message: types.Message):
    user_id = str(message.from_user.id)
    user_data = load_user_data()
    user_stats = user_data.get(user_id, {})
    
    try:
        item_id = int(message.text.split('_')[1])
        item = shop_items.get(item_id)
        
        if not item:
            await message.answer("⚠️ Noto'g'ri buyum raqami!", reply_markup=main_menu_keyboard())
            return
        
        if user_stats.get("gold", 0) < item["price"]:
            await message.answer("⚠️ Yetarli pul mablag'ingiz yo'q!", reply_markup=main_menu_keyboard())
            return
        
        user_stats["gold"] -= item["price"]
        
        if item["type"] == "weapon":
            user_stats["weapon"] = {
                "name": item["name"],
                "damage": item["damage"],
                "level": 1,
                "upgrade_cost": 100
            }
        elif item["type"] == "armor":
            user_stats["armor"] = {
                "name": item["name"],
                "defense": item["defense"]
            }
        else:
            if "inventory" not in user_stats:
                user_stats["inventory"] = []
            user_stats["inventory"].append(item)
        
        user_data[user_id] = user_stats
        save_user_data(user_data)
        
        await message.answer(f"✅ {item['name']} sotib olindi!", reply_markup=main_menu_keyboard())
        await GameStates.MAIN_MENU.set()
    
    except Exception as e:
        await message.answer(f"⚠️ Xatolik yuz berdi: {str(e)}", reply_markup=main_menu_keyboard())

# Statistika
@dp.message_handler(text='📊 Statistika', state="*")
async def show_stats(message: types.Message):
    user_id = str(message.from_user.id)
    user_data = load_user_data()
    user_stats = user_data.get(user_id, {})
    
    if not user_stats:
        await message.answer("⚠️ Iltimos, avval /start buyrug'ini bering!", reply_markup=main_menu_keyboard())
        return
    
    # Standart qiymatlarni o'rnatish
    name = user_stats.get('name', message.from_user.full_name)
    level = user_stats.get('level', 1)
    xp = user_stats.get('xp', 0)
    hp = user_stats.get('hp', 0)
    max_hp = user_stats.get('max_hp', 100)
    mana = user_stats.get('mana', 0)
    max_mana = user_stats.get('max_mana', 50)
    gold = user_stats.get('gold', 0)
    
    weapon = user_stats.get('weapon', {'name': 'Yoq', 'damage': '0', 'level': 1})
    armor = user_stats.get('armor', {'name': 'Yoq', 'defense': 0})
    
    stats_text = [
        f"📊 {name} statistikasi:",
        "",
        f"🧙‍♂️ Daraja: {level}",
        f"⭐ XP: {xp}/{level * 100}",
        f"❤️ Hayot: {hp}/{max_hp}",
        f"✨ Mana: {mana}/{max_mana}",
        f"💰 Gold: {gold}",
        "",
        f"⚔️ Qurol: {weapon['name']}",
        f"   Damage: {weapon['damage']} (Level: {weapon.get('level', 1)})",
        f"🛡️ Zirh: {armor['name']}",
        f"   Defense: +{armor.get('defense', 0)}",
        "",
        f"🎯 Yengilgan bosslar: {len(user_stats.get('bosses_defeated', []))}/5",
    ]
    
    if user_stats.get("active_effects"):
        stats_text.extend(["", "✨ Faol Effektlar:"])
        for effect, duration in user_stats["active_effects"].items():
            stats_text.append(f"- {effect.capitalize()} ({duration} qolgan navbat)")
    
    await message.answer("\n".join(stats_text), reply_markup=main_menu_keyboard())

# Inventar
@dp.message_handler(text='🎒 Inventar', state="*")
async def show_inventory(message: types.Message):
    user_id = str(message.from_user.id)
    user_data = load_user_data()
    user_stats = user_data.get(user_id, {})
    
    if not user_stats:
        await message.answer("⚠️ Iltimos, avval /start buyrug'ini bering!", reply_markup=main_menu_keyboard())
        return
    
    # Standart qiymatlarni o'rnatish
    name = user_stats.get('name', message.from_user.full_name)
    weapon = user_stats.get('weapon', {'name': 'Yoq', 'damage': '0', 'level': 1})
    armor = user_stats.get('armor', {'name': 'Yoq', 'defense': 0})
    gold = user_stats.get('gold', 0)
    
    inventory_text = [
        f"🎒 {name} inventari:",
        "",
        f"⚔️ Qurol: {weapon['name']}",
        f"   Damage: {weapon['damage']}",
        f"   Level: {weapon['level']}",
        "",
        f"🛡️ Zirh: {armor['name']}",
        f"   Defense: +{armor['defense']}",
        ""
    ]
    
    # Inventar buyumlari
    if user_stats.get("inventory"):
        inventory_text.append("🧪 Dorilar va buyumlar:")
        for item in user_stats["inventory"]:
            effect = item.get("effect", "")
            if isinstance(effect, str) and effect.startswith("+"):
                inventory_text.append(f"- {item['name']} ({effect})")
            else:
                inventory_text.append(f"- {item['name']} ({effect.capitalize() if effect else 'Nomalum'})")
    else:
        inventory_text.append("⚠️ Inventaringiz bosh")
    
    inventory_text.extend([
        "",
        f"💰 Gold: {gold}"
    ])
    
    # Qurolni yangilash
    if weapon.get("level", 1) < 15:
        upgrade_cost = weapon.get('upgrade_cost', 100)
        inventory_text.extend([
            "",
            f"⚒️ Qurolni yangilash: /upgrade (Narxi: {upgrade_cost} gold)"
        ])
    
    await GameStates.INVENTORY.set()
    await message.answer("\n".join(inventory_text), reply_markup=main_menu_keyboard())

# Qurolni yangilash
@dp.message_handler(commands=['upgrade'], state="*")
async def upgrade_weapon(message: types.Message):
    user_id = str(message.from_user.id)
    user_data = load_user_data()
    user_stats = user_data.get(user_id, {})
    
    if not user_stats:
        await message.answer("⚠️ Iltimos, avval /start buyrug'ini bering!", reply_markup=main_menu_keyboard())
        return
    
    weapon = user_stats.get("weapon", {})
    if weapon.get("level", 1) >= 15:
        await message.answer("⚠️ Sizning qurolingiz maksimal darajaga yetgan!", reply_markup=main_menu_keyboard())
        return
    
    cost = weapon.get("upgrade_cost", 100)
    if user_stats.get("gold", 0) < cost:
        await message.answer(f"⚠️ Yangilash uchun yetarli pul yo'q! Kerak: {cost} gold", reply_markup=main_menu_keyboard())
        return
    
    # Qurolni yangilash
    min_dmg, max_dmg = map(int, weapon["damage"].split('-'))
    new_min = min_dmg + 5
    new_max = max_dmg + 5
    weapon["damage"] = f"{new_min}-{new_max}"
    weapon["level"] += 1
    weapon["upgrade_cost"] = cost * 2  # Har yangilashda narx ikki baravar oshadi
    
    user_stats["gold"] -= cost
    user_data[user_id] = user_stats
    save_user_data(user_data)
    
    text = [
        f"⚒️ Qurol yangilandi! Yangi daraja: {weapon['level']}",
        f"⚔️ Yangi damage: {weapon['damage']}",
        f"💰 Keyingi yangilash narxi: {weapon['upgrade_cost']} gold"
    ]
    
    await message.answer("\n".join(text), reply_markup=main_menu_keyboard())

# Reyting jadvali
@dp.message_handler(text='🏆 Reyting', state="*")
async def show_leaderboard(message: types.Message):
    user_data = load_user_data()
    
    if not user_data:
        await message.answer("⚠️ Hozircha statistika mavjud emas", reply_markup=main_menu_keyboard())
        return
    
    # Eng yaxshi 10 o'yinchini saralash
    sorted_players = sorted(
        user_data.items(),
        key=lambda x: (x[1].get("level", 0), x[1].get("xp", 0)),
        reverse=True
    )[:10]
    
    leaderboard = ["🏆 Top 10 O'yinchilar 🏆", ""]
    
    for idx, (user_id, stats) in enumerate(sorted_players, 1):
        name = stats.get("name", f"Foydalanuvchi {user_id}")
        player_info = [
            f"{idx}. {name} -",
            f"Level: {stats.get('level', 1)} |",
            f"XP: {stats.get('xp', 0)} |",
            f"Gold: {stats.get('gold', 0)} |",
            f"Bosslar: {len(stats.get('bosses_defeated', []))}/5"
        ]
        leaderboard.append(" ".join(player_info))
    
    await message.answer("\n".join(leaderboard), reply_markup=main_menu_keyboard())

# Botni ishga tushirish
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)