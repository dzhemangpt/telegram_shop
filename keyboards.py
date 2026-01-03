from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup

from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from requests import get_categories,get_items,get_item,get_user,get_maincategories


main= ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="🛍Каталог")]]
,resize_keyboard=True
,input_field_placeholder='Для просмотра каталога товаров нажмите кнопку ниже')



async def categories(main_categories_id):
    kb=InlineKeyboardBuilder()
    all_categories= await get_categories(main_category_id=main_categories_id)

    for category in all_categories:
        kb.add(InlineKeyboardButton(text=category.name,callback_data=f"category_{category.id}",))

    kb.add(InlineKeyboardButton(text="🔼На главную", callback_data='go_start')) 
    return  kb.adjust(1).as_markup()  


async def main_categories():
    kb=InlineKeyboardBuilder()
    all_categories= await get_maincategories()

    for category in all_categories:
        kb.add(InlineKeyboardButton(text=category.name,callback_data=f"main_{category.id}",))

    
    return  kb.adjust(1).as_markup() 

async def helper(tg_id, field:str = 'name'):
    kb = ReplyKeyboardBuilder()
    
    user_data = await get_user(tg_id, field)
    
    if user_data and user_data != "error":
        kb.add(KeyboardButton(text=str(user_data)))
 
    
    return kb.adjust(1).as_markup(one_time_keyboard=True, resize_keyboard=True)
    



async def item(item_id):
    kb = InlineKeyboardBuilder()
    all_items = await get_item(item_id)

    for item in all_items:
        kb.add(InlineKeyboardButton(
            text="🛒Купить",
            callback_data=f"buy_{item.id}"  
        ))
    kb.add(InlineKeyboardButton(text="🔼На главную", callback_data='go_start'))    
    return kb.adjust(1).as_markup()  

async def items(category_id):
    kb = InlineKeyboardBuilder()
    all_items = await get_items(category_id)

    for item in all_items:

        kb.add(InlineKeyboardButton(
            text=f"{item.name} - {item.price} RUB💸",
            callback_data=f"item_{item.id}"  
        ))
    kb.add(InlineKeyboardButton(text="◀️Назад", callback_data='go_back'))    
    return kb.adjust(1).as_markup()  
