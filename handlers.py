from aiogram import F, Router,Bot
from random import randrange
from aiogram.filters import CommandStart,Command
from aiogram.types import Message, CallbackQuery, BufferedInputFile

from aiogram.fsm.state import State,StatesGroup
from aiogram.fsm.context import FSMContext

import app.keyboards  as kb
import re

main_id=1

import app.database.requests as req

class Reg(StatesGroup):
    name=State()
    phone=State()
    mail=State()
    item_id=State()
    name=State()
    main_category=State()



router = Router() 

@router.callback_query(F.data.startswith('buy_'))
async def first_step(callback: CallbackQuery, state: FSMContext):
    item_id = callback.data.replace('buy_', '')
    await state.update_data(name=callback.from_user.id)
    await state.update_data(item_id=item_id)
    
    tg_id = callback.from_user.id
    user_exists = await req.get_user(tg_id)
    

    
    if not user_exists:
        await callback.message.reply(text="😊Отлично, давайте оформим ваш заказ! Как к вам обращаться?")
    else:

        await callback.message.reply(
            text="😊Отлично, давайте оформим ваш заказ! Как к вам обращаться?",
            reply_markup=await kb.helper(tg_id=tg_id, field='name')
        )

    await state.set_state(Reg.name)

@router.message(Reg.name)
async def get_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(Reg.phone)
    
    tg_id = message.from_user.id
    
    user=await req.get_user(tg_id=tg_id)
    if user and user.phone:  
        await message.reply(
            text='🔢Введите номер телефона по следующему образцу:\n+70000000 (например +79591112233)',
            reply_markup=await kb.helper(tg_id=tg_id, field='phone')
        )
    else:
        await message.reply(
            text='🔢Введите номер телефона по следующему образцу:\n+70000000 (например +79591112233)'
        )

@router.message(Reg.phone)
async def get_phone(message: Message, state: FSMContext):
    if re.fullmatch(r'^(\+7|8)\d{10}$', message.text):
        await state.update_data(phone=message.text)
        
        tg_id = message.from_user.id
        user = await req.get_user(tg_id)
        
        if user and user.email: 
            await message.answer(
                "✉️Отлично! Последний шаг\nВведите электронную почту, по которой мы свяжемся с вами\nПример почты: telegram@mail.ru, krossovki.krutie@gmail.com",
                reply_markup=await kb.helper(tg_id=tg_id, field='email')
            )
        else:
            await message.answer(
                "✉️Отлично! Последний шаг\nВведите электронную почту, по которой мы свяжемся с вами\nПример почты: telegram@mail.ru, krossovki.krutie@gmail.com"
            )
        await state.set_state(Reg.mail)
    else:
        await message.reply(
            "❌Неправильный ввод!\nВведите номер телефона по следующему образцу:\n+70000000 (например +79591112233)"
        )
        await state.set_state(Reg.phone)

@router.message(Reg.mail)
async def get_mmail(message: Message, state: FSMContext, bot: Bot):
    if re.fullmatch(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z0-9-]{2,}$', message.text):
        data = await state.get_data()
        item_id1 = data.get("item_id")
        email = message.text
        items = await req.get_item(item_id1)
        
        if not items:
            await message.answer("Товар не найден!")
            await state.clear()
            return
 
        for item in items:
            name1 = item.name
            desc1 = item.description
            cost1 = item.price
        
        id_zakaz = randrange(10000, 99999)
        

        await req.update_user(
            tg_id=message.from_user.id,
            username=message.from_user.username,
            name=data['name'],
            email=email,
            phone=data['phone']
        )
        
        mes = f'✅Заказ №{id_zakaz}:\n\nНазвание товара: {name1}\n\nОписание товара: {desc1}\n\nЦена товара: {cost1}'
        await message.answer(mes)
        
        admin_mes = f'✉️Заказ №{id_zakaz}:\n\nTelegram username: {message.from_user.username}\n\nОбращаться по имени: {data["name"]}\n\nНомер телефона заказчика: {data["phone"]}\n\nЭлектронная почта: {email}\n\nНазвание товара: {name1}\n\nОписание товара: {desc1}\n\nЦена товара: {cost1}'
        
        await bot.send_message(chat_id=5035457204, text=admin_mes)
        await message.answer("Наш менеджер свяжется с вами в течение 24-х часов для проведения покупки!\nСпасибо, что выбрали нас!😊",reply_markup=kb.main)
        await state.clear()
    else:
        await message.answer(
            "❌Почта введена неверно!\nВведите электронную почту, по которой мы свяжемся с вами\nПример почты: telegram@mail.ru, krossovki.krutie@gmail.com"
        )
        await state.set_state(Reg.mail)






@router.message(Command('help'))
async def get_help(message: Message):
    await message.answer('/shop - начать поиск товаров для покупки\n/start - запустить бота\n/help - вызвать меню подсказки еще раз\nПроцесс покупки происходит путем нажатия по клавишам после /shop. Когда вы выбрали нужный товар введите имя, по которому вы хотели бы, чтобы к вам обращались. После - номер телефона и почту для электронной связи. Наш менеджер так же сможет связаться с вами в телеграм по вашему username',reply_markup=kb.main)





@router.message(Command('start'))
async def starting(message: Message):
    await message.answer('😊Здравствуйте! Вас приветсвует спортивный магазин "GYM RATS"\nЧтобы выбрать себе лучшие товары, нажмите кнопку Каталог\nДля более подробной информации о магазине введите /help',reply_markup=kb.main)


@router.message(Command("shop"))
async def market(message:Message):
    await catelog(message)

@router.message(F.text=='🛍Каталог')
async def catelog(message:Message):
    await message.answer(text="Доступны следующие категории товаров",reply_markup=await kb.main_categories())


@router.callback_query(F.data.startswith('main_'))
async def category(callback: CallbackQuery):
    await callback.answer()
    global main_id
    main_id = callback.data.split('_')[1]
    
    try:

        keyboard = await kb.categories(int(main_id))
        await callback.message.edit_text(
            "🛒Выберите категорию/бренд",
            reply_markup=keyboard
        )
    except Exception as e:
        await callback.message.answer(f"Ошибка: {e}")

@router.callback_query(F.data.startswith('category_'))
async def category(callback: CallbackQuery):
    await callback.answer()
    global category_id 
    category_id = callback.data.split('_')[1]
    
    try:

        keyboard = await kb.items(int(category_id))
        await callback.message.edit_text(
            "🛒Выберите товар",
            reply_markup=keyboard
        )
    except Exception as e:
        await callback.message.answer(f"Ошибка: {e}")



@router.callback_query(F.data.startswith('item_'))
async def item(callback: CallbackQuery):
    global category_id
    category_id=callback.data.split('_')[1]
    items= await req.get_item(int(category_id))
    await callback.message.delete()
    for item123 in items:
        item1= f"Имя товара: {item123.name}\n\nОписание товара: {item123.description}\n\nСтоимость товара: {item123.price} руб."
        image1= BufferedInputFile(item123.picture,filename="image1.jpeg")
        await callback.message.answer_photo((image1),caption=item1,reply_markup=await kb.item(int(item123.id)))

        

         

@router.callback_query(F.data.startswith("category"))
async def handle_category_selection(callback: CallbackQuery):

    await callback.message.delete()

@router.callback_query(F.data.startswith("go_back"))
async def go_back(callback: CallbackQuery):
   
    global main_id
    await callback.message.delete()
    await callback.message.answer(text="🛒Выберите категорию/бренд",reply_markup=await kb.categories(main_id))

@router.callback_query(F.data.startswith("go_start"))
async def go_start(callback: CallbackQuery):

    await callback.message.delete()
    await catelog(callback.message)

  
        
        

    
    
  


