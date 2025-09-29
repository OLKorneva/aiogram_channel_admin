from aiogram import types

event_message = {'add': '👤 <b>Новый участник присоединился к каналу:</b>',
                 'left': '😢 <b>Участник покинул канал:</b>',
                 'choice': 'Какое сообщение нужно написать для {}?',
                 'greet_message': '''Уважаемый {}!

👋 Добро пожаловать в сообщество профессионалов рынка ГЧП и инфраструктуры ГЧП Прайм!

🔎 Дополнительные аналитические материалы и исследования компании You & Partners доступны по <a href={}>ссылке</a>.

Также Вы можете подписаться на рассылку нашей экспертной аналитики (выходит 1 раз в месяц)''',
                'farewell_message': '''Уважаемый {}! 

Нам жаль прощаться с Вами! 

Если Вы хотите не более 1 раза в месяц получать  рассылку нашей экспертной аналитики, подпишитесь на неё.'''
                 }

def get_user_inf(user: types.User, event: str):
    deep_link = f"tg://user?id={user.id}"
    user_inf = f'''
ID: <code>{user.id}</code>
Имя: {user.first_name or 'Отсутствует'}
Фамилия: {user.last_name or 'Отсутствует'}
Юзернейм: {'@' + user.username if user.username else 'Отсутствует'}

📩 <a href="{deep_link}">Написать сообщение</a>'''

    return f'{event}\n{user_inf}'

def get_user_name(user):
    return user.first_name or user.last_name or user.username or 'коллега'