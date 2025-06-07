import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
import random
import json
import os
from keep_alive import keep_alive
keep_alive()

# Logging sozlamalari
logging.basicConfig(level=logging.INFO)

# Bot tokeni
API_TOKEN = os.environ.get('token')

# Botni yaratish
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Foydalanuvchilar ma'lumotlari uchun JSON fayli

# Boshlang'ich foydalanuvchi ma'lumotlari
DEFAULT_USER = {
    'level': 1,
    'xp': 0,
    'coins': 100,
    'health': 100,
    'max_health': 100,
    'power': 10,
    'weapon': {'name': 'Oddiy qilich', 'damage': 5, 'level': 1},
    'armor': {'name': 'Oddiy zirh', 'defense': 3, 'level': 1},
    'inventory': [],
    'missions_completed': 0,
    'bosses_defeated': 0,
    'aura_active': False,
    'aura_charges': 0
}

# Qurollar ro'yxati
WEAPONS = [
    {'name': 'Oddiy qilich', 'damage': 5, 'price': 100, 'level': 1},
    {'name': 'Temir qilich', 'damage': 10, 'price': 300, 'level': 2},
    {'name': 'Sehrli qilich', 'damage': 20, 'price': 700, 'level': 3},
    {'name': 'Afsonaviy qilich', 'damage': 40, 'price': 1500, 'level': 5}
]

# Zirhlar ro'yxati
ARMORS = [
    {'name': 'Oddiy zirh', 'defense': 3, 'price': 100, 'level': 1},
    {'name': 'Temir zirh', 'defense': 7, 'price': 300, 'level': 2},
    {'name': 'Sehrli zirh', 'defense': 15, 'price': 700, 'level': 3},
    {'name': 'Afsonaviy zirh', 'defense': 30, 'price': 1500, 'level': 5}
]

# Auralar ro'yxati
AURAS = [
    {'name': 'Kumush aura', 'price': 500, 'charges': 3, 'level': 2},
    {'name': 'Oltin aura', 'price': 1000, 'charges': 3, 'level': 3},
    {'name': 'Afsonaviy aura', 'price': 2000, 'charges': 3, 'level': 5}
]

# Missiyalar ro'yxati
MISSIONS = [
    {'name': 'Boshiq ov', 'xp': 50, 'coins': 100, 'health_cost': 10, 'min_level': 1},
    {'name': 'Bandiqlarni tozalash', 'xp': 100, 'coins': 200, 'health_cost': 20, 'min_level': 2},
    {'name': 'Qaroqchilar bazasiga hujum', 'xp': 200, 'coins': 400, 'health_cost': 40, 'min_level': 3},
    {'name': 'Ajdarhani o\'ldirish', 'xp': 500, 'coins': 1000, 'health_cost': 80, 'min_level': 5}
]

# Bosslar ro'yxati
BOSSES = [
    {'name': 'Qaroqchi boshliq', 'health': 100, 'damage': 15, 'xp': 200, 'coins': 300, 'min_level': 2},
    {'name': 'Sehrgar', 'health': 200, 'damage': 30, 'xp': 400, 'coins': 600, 'min_level': 3},
    {'name': 'Qora ritsar', 'health': 400, 'damage': 50, 'xp': 800, 'coins': 1200, 'min_level': 4},
    {'name': 'O\'lim shohi', 'health': 800, 'damage': 80, 'xp': 1600, 'coins': 2500, 'min_level': 6}
]

# Foydalanuvchilar ma'lumotlarini yuklash

# Foydalanuvchini tekshirish (agar yo'q bo'lsa yaratish)
# Foydalanuvchilar ma'lumotlari uchun global lug'at
users = {}

# Foydalanuvchini tekshirish (agar yo'q bo'lsa yaratish)
def get_user(user_id):
    if str(user_id) not in users:
        users[str(user_id)] = DEFAULT_USER.copy()
    return users[str(user_id)]

# Foydalanuvchi ma'lumotlarini yangilash
def update_user(user_id, data):
    users[str(user_id)] = data
# O'lim jarayoni
# Damage hisoblash
def calculate_damage(user, enemy_damage):
    if user['aura_active'] and user['aura_charges'] > 0:
        user['aura_charges'] -= 1
        if user['aura_charges'] == 0:
            user['aura_active'] = False
        return 0  # Aura faol bo'lsa, damage olinmaydi
    
    return max(0, enemy_damage - user['armor']['defense'])

async def handle_death(user_id, message: types.Message):
    user = get_user(user_id)
    
    # Jazolarni qo'llash
    xp_loss = int(user['xp'] * 0.4)  # XP ning 30% yo'qoladi
    coins_loss = int(user['coins'] * 0.4)  # Tangalarning 40% yo'qoladi
    
    user['xp'] = max(0, user['xp'] - xp_loss)
    user['coins'] = max(0, user['coins'] - coins_loss)
    
    # Bosslarni qayta tartiblash (oldingi darajaga tushirish)
    # Jonni 1 qilib qo'yamiz (to'liq o'ldirmaymiz)
    user['health'] = 1
    
    update_user(user_id, user)
    
    await message.answer(
        f"💀 Siz o'ldingiz! Jazo sifatida:\n"
        f"⭐ XP: -{xp_loss}\n"
        f"💰 Tangalar: -{coins_loss}\n\n"
        f"Qayta tirilish uchun /start buyrug'ini yuboring."
    )
    
    
# Asosiy menyu
async def show_main_menu(message: types.Message):
    user = get_user(message.from_user.id)
    
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [
        "📊 Profil", "🎒 Inventar", "⚔️ Jang", 
        "🏆 Missiyalar", "🛒 Do'kon", "ℹ️ Yordam"
    ]
    keyboard.add(*buttons)
    
    await message.answer("🏰 RPG O'yin Botiga xush kelibsiz! Quyidagi menyudan tanlang:", reply_markup=keyboard)

# Profilni ko'rsatish
async def show_profile(message: types.Message):
    user = get_user(message.from_user.id)
    
    profile_text = (
        f"👤 {message.from_user.full_name}\n\n"
        f"📊 Level: {user['level']}\n"
        f"⭐ XP: {user['xp']}/{user['level'] * 100}\n"
        f"💰 Tangalar: {user['coins']}\n"
        f"❤️ Jon: {user['health']}/{user['max_health']}\n"
        f"💪 Kuch: {user['power']}\n\n"
        f"⚔️ Qurol: {user['weapon']['name']} (Damage: {user['weapon']['damage']})\n"
        f"🛡️ Zirh: {user['armor']['name']} (Defense: {user['armor']['defense']})\n"
    )
    
    if user['aura_active']:
        profile_text += f"✨ Aura: Faol ({user['aura_charges']} ta hujum qoldi)\n\n"
    else:
        profile_text += "✨ Aura: Faol emas\n\n"
    
    profile_text += (
        f"🏆 Missiyalar: {user['missions_completed']}\n"
        f"👹 Bosslar: {user['bosses_defeated']}"
    )
    
    await message.answer(profile_text)

# Inventarni ko'rsatish
async def show_inventory(message: types.Message):
    user = get_user(message.from_user.id)
    
    if not user['inventory']:
        await message.answer("🎒 Sizning inventaringiz bo'sh!")
        return
    
    items_text = "🎒 Inventaringiz:\n\n"
    for i, item in enumerate(user['inventory'], 1):
        items_text += f"{i}. {item['name']} - {item.get('damage', item.get('defense', 0))} "
        if 'damage' in item:
            items_text += "damage (Qurol)"
        else:
            items_text += "defense (Zirh)"
        items_text += "\n"
    
    await message.answer(items_text)

# Jang menyusi
async def show_battle_menu(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["🐺 Yovvoyi hayvon", "👹 Boss", "🔙 Orqaga"]
    keyboard.add(*buttons)
    
    await message.answer("⚔️ Jangga xush kelibsiz! Kimga hujum qilmoqchisiz?", reply_markup=keyboard)

# Yovvoyi hayvon bilan jang
async def battle_wild_animal(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if user['health'] <= 0:
        await message.answer("💀 Sizning joningiz tugagan! Qayta tiklash uchun /start buyrug'ini yuboring.")
        return
    
    animal_health = random.randint(20, 50)
    animal_damage = random.randint(5, 15)
    xp_reward = random.randint(10, 30)
    coins_reward = random.randint(5, 20)
    
    battle_text = (
        f"🐺 Yovvoyi hayvon bilan jang boshlandi!\n\n"
        f"🧌 Hayvon jon: {animal_health}\n"
        f"⚔️ Hayvon damage: {animal_damage}\n\n"
        f"⚔️ {user['weapon']['name']} damage: {user['weapon']['damage']}\n"
        f"🛡️ {user['armor']['name']} defense: {user['armor']['defense']}"
    )
    
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["⚔️ Hujum qilish", "🏃 Qochish"]
    keyboard.add(*buttons)
    
    await message.answer(battle_text, reply_markup=keyboard)
    
    # Jang holatini saqlash
    battle_data = {
        'type': 'animal',
        'enemy_health': animal_health,
        'enemy_damage': animal_damage,
        'xp_reward': xp_reward,
        'coins_reward': coins_reward,
        'initial_enemy_health': animal_health
    }
    
    await BattleState.waiting_for_action.set()
    state = dp.current_state(user=user_id)
    await state.update_data(battle_data=battle_data)

# Boss bilan jang
async def battle_boss(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if user['health'] <= 0:
        await message.answer("💀 Sizning joningiz tugagan! Qayta tiklash uchun /start buyrug'ini yuboring.")
        return
    
    # Foydalanuvchi darajasiga mos boss topish
    available_bosses = [boss for boss in BOSSES if boss['min_level'] <= user['level']]
    if not available_bosses:
        await message.answer("⚠️ Sizning darajangiz hali hech qanday bossga hujum qilish uchun yetarli emas!")
        return
    
    # Agar user biror bossni mag'lub qilgan bo'lsa, keyingi bossni ko'rsatish
    boss_index = min(user['bosses_defeated'], len(available_bosses)-1)
    boss = available_bosses[boss_index]
    
    battle_text = (
        f"👹 {boss['name']} bilan jang boshlandi!\n\n"
        f"🧌 Boss jon: {boss['health']}\n"
        f"⚔️ Boss damage: {boss['damage']}\n\n"
        f"⚔️ {user['weapon']['name']} damage: {user['weapon']['damage']}\n"
        f"🛡️ {user['armor']['name']} defense: {user['armor']['defense']}"
    )
    
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["⚔️ Hujum qilish", "🏃 Qochish"]
    keyboard.add(*buttons)
    
    await message.answer(battle_text, reply_markup=keyboard)
    
    # Jang holatini saqlash
    battle_data = {
        'type': 'boss',
        'enemy': boss,
        'enemy_health': boss['health'],
        'enemy_damage': boss['damage'],
        'xp_reward': boss['xp'],
        'coins_reward': boss['coins'],
        'initial_enemy_health': boss['health']
    }
    
    await BattleState.waiting_for_action.set()
    state = dp.current_state(user=user_id)
    await state.update_data(battle_data=battle_data)

# Missiyalar menyusi
async def show_missions_menu(message: types.Message):
    user = get_user(message.from_user.id)
    
    missions_text = "🏆 Missiyalar:\n\n"
    for i, mission in enumerate(MISSIONS, 1):
        available = mission['min_level'] <= user['level']
        missions_text += (
            f"{i}. {mission['name']} {'✅' if available else '❌'}\n"
            f"   ⭐ XP: {mission['xp']}\n"
            f"   💰 Tangalar: {mission['coins']}\n"
            f"   ❤️ Jon narxi: {mission['health_cost']}\n"
            f"   📊 Minimal level: {mission['min_level']}\n\n"
        )
    
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [str(i+1) for i in range(len(MISSIONS)) if MISSIONS[i]['min_level'] <= user['level']]
    buttons.append("🔙 Orqaga")
    keyboard.add(*buttons)
    
    await message.answer(missions_text, reply_markup=keyboard)

# Missiya jangini boshlash
async def start_mission_battle(message: types.Message, mission_num):
    user_id = message.from_user.id
    user = get_user(user_id)
    mission = MISSIONS[mission_num]
    
    if mission['min_level'] > user['level']:
        await message.answer(f"⚠️ Bu missiya uchun minimal {mission['min_level']}-level kerak!")
        return
    
    if user['health'] <= mission['health_cost']:
        await message.answer(f"⚠️ Bu missiya uchun kamida {mission['health_cost']+1} jon kerak!")
        return
    
    battle_text = (
        f"🏆 {mission['name']} missiyasi boshlandi!\n\n"
        f"🧌 Dushman jon: {mission['health_cost'] * 10}\n"
        f"⚔️ Dushman damage: {mission['health_cost'] * 2}\n\n"
        f"⚔️ {user['weapon']['name']} damage: {user['weapon']['damage']}\n"
        f"🛡️ {user['armor']['name']} defense: {user['armor']['defense']}"
    )
    
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["⚔️ Hujum qilish", "🏃 Qochish"]
    keyboard.add(*buttons)
    
    await message.answer(battle_text, reply_markup=keyboard)
    
    battle_data = {
        'type': 'mission',
        'mission_num': mission_num,
        'enemy_health': mission['health_cost'] * 10,
        'enemy_damage': mission['health_cost'] * 2,
        'xp_reward': mission['xp'],
        'coins_reward': mission['coins'],
        'initial_enemy_health': mission['health_cost'] * 10
    }
    
    await BattleState.waiting_for_action.set()
    state = dp.current_state(user=user_id)
    await state.update_data(battle_data=battle_data)

# Do'kon menyusi
async def show_shop_menu(message: types.Message):
    user = get_user(message.from_user.id)
    
    shop_text = "🛒 Do'kon:\n\n"
    shop_text += "⚔️ Qurollar:\n"
    for i, weapon in enumerate(WEAPONS, 1):
        if weapon['level'] <= user['level']:
            shop_text += (
                f"{i}. {weapon['name']}\n"
                f"   ⚔️ Damage: {weapon['damage']}\n"
                f"   💰 Narx: {weapon['price']}\n"
                f"   📊 Level: {weapon['level']}\n\n"
            )
    
    shop_text += "\n🛡️ Zirhlar:\n"
    for i, armor in enumerate(ARMORS, 1):
        if armor['level'] <= user['level']:
            shop_text += (
                f"{i}. {armor['name']}\n"
                f"   🛡️ Defense: {armor['defense']}\n"
                f"   💰 Narx: {armor['price']}\n"
                f"   📊 Level: {armor['level']}\n\n"
            )
    
    shop_text += "\n✨ Auralar:\n"
    for i, aura in enumerate(AURAS, 1):
        if aura['level'] <= user['level']:
            shop_text += (
                f"{i}. {aura['name']}\n"
                f"   🛡️ Himoya: 3 ta hujum\n"
                f"   💰 Narx: {aura['price']}\n"
                f"   📊 Level: {aura['level']}\n\n"
            )
    
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [f"⚔️ {i+1}-qurol" for i in range(len(WEAPONS)) if WEAPONS[i]['level'] <= user['level']]
    buttons += [f"🛡️ {i+1}-zirh" for i in range(len(ARMORS)) if ARMORS[i]['level'] <= user['level']]
    buttons += [f"✨ {i+1}-aura" for i in range(len(AURAS)) if AURAS[i]['level'] <= user['level']]
    buttons.append("🔙 Orqaga")
    keyboard.add(*buttons)
    
    await message.answer(shop_text, reply_markup=keyboard)

# Qurol yoki zirh sotib olish
async def buy_item(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    try:
        parts = message.text.split()
        item_type = parts[0]
        item_num = int(parts[1].replace("-qurol", "").replace("-zirh", "").replace("-aura", "")) - 1
    except (IndexError, ValueError):
        await message.answer("⚠️ Noto'g'ri buyum tanlandi!")
        return
    
    if item_type == "⚔️":
        # Qurol sotib olish
        if item_num >= len(WEAPONS):
            await message.answer("⚠️ Noto'g'ri qurol tanlandi!")
            return
        
        weapon = WEAPONS[item_num]
        if weapon['level'] > user['level']:
            await message.answer("⚠️ Bu qurolni sotib olish uchun darajangiz yetarli emas!")
            return
        
        if user['coins'] < weapon['price']:
            await message.answer("⚠️ Bu qurolni sotib olish uchun tangalaringiz yetarli emas!")
            return
        
        # Qurolni sotib olish
        user['coins'] -= weapon['price']
        user['weapon'] = {
            'name': weapon['name'],
            'damage': weapon['damage'],
            'level': weapon['level']
        }
        
        update_user(user_id, user)
        await message.answer(f"🎉 {weapon['name']} quroli muvaffaqiyatli sotib olindi!")
    
    elif item_type == "🛡️":
        # Zirh sotib olish
        if item_num >= len(ARMORS):
            await message.answer("⚠️ Noto'g'ri zirh tanlandi!")
            return
        
        armor = ARMORS[item_num]
        if armor['level'] > user['level']:
            await message.answer("⚠️ Bu zirhni sotib olish uchun darajangiz yetarli emas!")
            return
        
        if user['coins'] < armor['price']:
            await message.answer("⚠️ Bu zirhni sotib olish uchun tangalaringiz yetarli emas!")
            return
        
        # Zirhni sotib olish
        user['coins'] -= armor['price']
        user['armor'] = {
            'name': armor['name'],
            'defense': armor['defense'],
            'level': armor['level']
        }
        
        update_user(user_id, user)
        await message.answer(f"🎉 {armor['name']} zirhi muvaffaqiyatli sotib olindi!")
    
    else:
        await message.answer("⚠️ Noto'g'ri buyum turi tanlandi!")

# Aura sotib olish
async def buy_aura(message: types.Message, aura_num):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if aura_num >= len(AURAS):
        await message.answer("⚠️ Noto'g'ri aura tanlandi!")
        return
    
    aura = AURAS[aura_num]
    if aura['level'] > user['level']:
        await message.answer("⚠️ Bu aurani sotib olish uchun darajangiz yetarli emas!")
        return
    
    if user['coins'] < aura['price']:
        await message.answer("⚠️ Bu aurani sotib olish uchun tangalaringiz yetarli emas!")
        return
    
    user['coins'] -= aura['price']
    user['aura_active'] = True
    user['aura_charges'] = aura['charges']
    
    update_user(user_id, user)
    await message.answer(f"🎉 {aura['name']} muvaffaqiyatli sotib olindi! Keyingi 3 ta hujumda damage olmaysiz.")

# Yordam menyusi
async def show_help(message: types.Message):
    help_text = (
        "ℹ️ RPG O'yin Boti Yordam\n\n"
        "📊 Profil - O'yinchining statistikasini ko'rish\n"
        "🎒 Inventar - O'yinchining inventarini ko'rish\n"
        "⚔️ Jang - Yovvoyi hayvonlar va bosslar bilan jang\n"
        "🏆 Missiyalar - Missiyalarni bajarish (jang orqali)\n"
        "🛒 Do'kon - Yangi qurol, zirh va auralar sotib olish\n\n"
        "✨ Auralar - 3 ta hujum davomida sizga damage yetkazilmaydi\n"
        "💀 O'lim - O'lganda XP va tangalaringizning bir qismini yo'qotasiz\n\n"
        "Botda barcha amallar knopkalar orqali boshqariladi!"
    )
    
    await message.answer(help_text)

# Jang holatlari
class BattleState(StatesGroup):
    waiting_for_action = State()

# Jangda harakat qilish
@dp.message_handler(state=BattleState.waiting_for_action)
async def process_battle_action(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user = get_user(user_id)
    data = await state.get_data()
    battle_data = data['battle_data']
    
    if message.text == "⚔️ Hujum qilish":
        # Foydalanuvchi hujumi
        damage = user['weapon']['damage'] + user['power']
        battle_data['enemy_health'] -= damage
        
        # Dushman hujumi (aura hisobga olinadi)
        enemy_damage = calculate_damage(user, battle_data['enemy_damage'])
        user['health'] -= enemy_damage
        
        # Natijani tekshirish
        if battle_data['enemy_health'] <= 0:
            # G'alaba
            user['xp'] += battle_data['xp_reward']
            user['coins'] += battle_data['coins_reward']
            
            # Missiya bo'lsa, missiyani hisoblash
            if battle_data['type'] == 'mission':
                user['missions_completed'] += 1
            
            # Level tekshirish
            level_up = False
            while user['xp'] >= user['level'] * 100:
                user['xp'] -= user['level'] * 100
                user['level'] += 1
                user['max_health'] += 20
                user['health'] = user['max_health']
                user['power'] += 5
                level_up = True
            
            if battle_data['type'] == 'boss':
                user['bosses_defeated'] += 1
            
            result_text = f"🎉 G'alaba! {battle_data.get('enemy', {}).get('name', 'Dushman')} mag'lub etildi!\n\n"
            result_text += f"⭐ XP: +{battle_data['xp_reward']}\n"
            result_text += f"💰 Tangalar: +{battle_data['coins_reward']}\n"
            
            if enemy_damage > 0:
                result_text += f"❤️ Jon: -{enemy_damage}\n\n"
            else:
                result_text += f"✨ Aura sizni himoya qildi! Damage: 0\n\n"
            
            if level_up:
                result_text += (
                    f"🎊 Tabriklaymiz! Level {user['level']} ga ko'tarildingiz!\n"
                    f"❤️ Maksimal jon: +20\n"
                    f"💪 Kuch: +5\n"
                    f"⭐ XP: {user['xp']}/{user['level'] * 100}"
                )
            
            update_user(user_id, user)
            await state.finish()
            await message.answer(result_text, reply_markup=types.ReplyKeyboardRemove())
            await show_main_menu(message)
            return
        
        elif user['health'] <= 0:
            # O'lim
            await handle_death(user_id, message)
            await state.finish()
            return
        
        else:
            # Jang davom etmoqda
            battle_text = f"⚔️ Siz {damage} damage yetkazdingiz!\n"
            battle_text += f"🧌 {battle_data.get('enemy', {}).get('name', 'Dushman')} "
            battle_text += f"joni: {battle_data['enemy_health']}/{battle_data['initial_enemy_health']}\n\n"
            
            if enemy_damage > 0:
                battle_text += f"⚔️ {battle_data.get('enemy', {}).get('name', 'Dushman')} "
                battle_text += f"sizga {enemy_damage} damage yetkazdi!\n"
            else:
                battle_text += f"✨ Aura sizni himoya qildi! Damage: 0\n"
            
            battle_text += f"❤️ Sizning joningiz: {user['health']}/{user['max_health']}"
            
            if user['aura_active']:
                battle_text += f"\n✨ Aura: {user['aura_charges']} ta hujum qoldi"
            
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            buttons = ["⚔️ Hujum qilish", "🏃 Qochish"]
            keyboard.add(*buttons)
            
            await state.update_data(battle_data=battle_data)
            update_user(user_id, user)
            await message.answer(battle_text, reply_markup=keyboard)
    
    elif message.text == "🏃 Qochish":
        # Qochish
        success = random.choice([True, False])
        
        if success:
            await state.finish()
            await message.answer("🏃 Siz muvaffaqiyatli qochib qoldingiz!", reply_markup=types.ReplyKeyboardRemove())
            await show_main_menu(message)
        else:
            # Qochish muvaffaqiyatsiz - dushman hujumi
            enemy_damage = calculate_damage(user, battle_data['enemy_damage'])
            user['health'] -= enemy_damage
            
            if user['health'] <= 0:
                # Mag'lubiyat
                await handle_death(user_id, message)
                await state.finish()
                return
            
            else:
                # Qochish muvaffaqiyatsiz, lekin jon qoldi
                battle_text = (
                    f"⚠️ Qochish muvaffaqiyatsiz!\n\n"
                )
                
                if enemy_damage > 0:
                    battle_text += f"⚔️ {battle_data.get('enemy', {}).get('name', 'Dushman')} "
                    battle_text += f"sizga {enemy_damage} damage yetkazdi!\n"
                else:
                    battle_text += f"✨ Aura sizni himoya qildi! Damage: 0\n"
                
                battle_text += f"❤️ Sizning joningiz: {user['health']}/{user['max_health']}"
                
                if user['aura_active']:
                    battle_text += f"\n✨ Aura: {user['aura_charges']} ta hujum qoldi"
                
                keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                buttons = ["⚔️ Hujum qilish", "🏃 Qochish"]
                keyboard.add(*buttons)
                
                await state.update_data(battle_data=battle_data)
                update_user(user_id, user)
                await message.answer(battle_text, reply_markup=keyboard)
    
    else:
        await message.answer("⚠️ Iltimos, faqat knopkalardan foydalaning!")

# Asosiy commandalar
# O'lim jarayoni - yangi versiya


# /start handler - yangi versiya
@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    # Agar jon past bo'lsa (o'lim holati), to'liq tiklash
    if user['health'] <= 1:
        user['health'] = user['max_health']
        update_user(user_id, user)
        await message.answer("❤️ Joningiz to'liq tiklandi!")
    
    await show_main_menu(message)

# Boshqa xabarlarga javob
@dp.message_handler()
async def process_message(message: types.Message):
    text = message.text
    
    if text == "📊 Profil":
        await show_profile(message)
    elif text == "🎒 Inventar":
        await show_inventory(message)
    elif text == "⚔️ Jang":
        await show_battle_menu(message)
    elif text == "🐺 Yovvoyi hayvon":
        await battle_wild_animal(message)
    elif text == "👹 Boss":
        await battle_boss(message)
    elif text == "🏆 Missiyalar":
        await show_missions_menu(message)
    elif text.isdigit() and 1 <= int(text) <= len(MISSIONS):
        await start_mission_battle(message, int(text)-1)
    elif text == "🛒 Do'kon":
        await show_shop_menu(message)
    elif text.startswith("⚔️"):
        await buy_item(message)
    elif text.startswith("🛡️"):
        await buy_item(message)
    elif text.startswith("✨"):
        parts = text.split()
        if len(parts) == 2 and parts[1].replace("-aura", "").isdigit():
            aura_num = int(parts[1].replace("-aura", "")) - 1
            if 0 <= aura_num < len(AURAS):
                await buy_aura(message, aura_num)
            else:
                await message.answer("⚠️ Noto'g'ri aura tanlandi!")
        else:
            await message.answer("⚠️ Noto'g'ri buyum tanlandi!")
    elif text == "ℹ️ Yordam":
        await show_help(message)
    elif text == "🔙 Orqaga":
        await show_main_menu(message)
    else:
        await message.answer("⚠️ Iltimos, faqat menyu knopkalaridan foydalaning!")

# Botni ishga tushurish
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
