event_message = {'add': '👤 <b>Новый участник присоединился к каналу:</b>',
                 'left': '😢 <b>Участник покинул канал:</b>'}

async def give_user_inf(user):
    deep_link = f"tg://user?id={user.id}"
    return f'''
ID: <code>{user.id}</code>
Имя: {user.first_name or 'Отсутствует'}
Фамилия: {user.last_name or 'Отсутствует'}
Юзернейм: {user.username or 'Отсутствует'}

📩 <a href="{deep_link}">Написать сообщение</a>'''

