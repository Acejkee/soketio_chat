import eventlet
from eventlet import wsgi
import socketio
from loguru import logger

from src.models.user import User
from src.models.message import Message

ROOMS = ["lobby", "general", "random"]

class User:
    def __init__(self, sid, name, room):
        self.sid = sid
        self.name = name
        self.room = room
        self.messages = []

# src/models/message.py
class Message:
    def __init__(self, text, author):
        self.text = text
        self.author = author

# Хранилище пользователей
users = {}

def get_user(sid):
    return users.get(sid)


# Заставляем работать пути к статике
static_files = {'/': 'static/index.html', '/static': './static'}
sio = socketio.Server(cors_allowed_origins='*', async_mode='eventlet')
app = socketio.WSGIApp(sio, static_files=static_files)


# Обрабатываем подключение пользователя
@sio.event
def connect(sid, environ):
    logger.info(f"Пользователь {sid} подключился")


# Отправляем комнаты
@sio.on('get_rooms')
def on_get_rooms(sid, data):
    sio.emit('rooms', ROOMS, to=sid)


@sio.on('join')
def on_join(sid, data):
    name = data.get('name')
    room = data.get('room')

    if not name or not room or room not in ROOMS:
        sio.emit('error', {'message': 'Invalid room or name'}, room=sid)
        return

    user = User(sid, name, room)
    users[sid] = user
    sio.enter_room(sid, room)

    # Уведомляем всех в комнате о новом пользователе
    sio.emit('move', {'room': room}, room=user.room)
    logger.info(f"Пользователь {name} присоединился к комнате {room}")



@sio.on('leave')
def on_leave(sid, data):
    user = get_user(sid)
    if user:
        sio.leave_room(sid, user.room)
        del users[sid]
        logger.info(f"Пользователь {user.name} покинул комнату {user.room}")


@sio.on('send_message')
def on_message(sid, data):
    text = data.get('text')
    user = get_user(sid)

    if not text or not user:
        sio.emit('error', {'message': 'Invalid message or user'}, room=sid)
        return

    message = Message(text, user.name)
    user.messages.append(message)
    print(message.author)
    # Отправляем сообщение всем в комнате
    sio.emit('message', {'text': message.text, 'name': message.author}, room=user.room)

# Обрабатываем отключение пользователя
@sio.event
def disconnect(sid):
    user = get_user(sid)
    if user:
        del users[sid]
        logger.info(f"Пользователь {user.name} отключился")


if __name__ == '__main__':
    wsgi.server(eventlet.listen(("127.0.0.1", 8000)), app)
