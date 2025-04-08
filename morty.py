import json
import queue
import random
import requests
import sounddevice as sd
import pyttsx3
from vosk import Model, KaldiRecognizer
import json
import queue
import random
import requests
import sounddevice as sd
import pyttsx3
import webbrowser
import time
from vosk import Model, KaldiRecognizer

# Модель Vosk
model = Model("model")
recognizer = KaldiRecognizer(model, 16000)
q = queue.Queue()

# TTS
engine = pyttsx3.init()
engine.setProperty('rate', 170)

# Флаги и состояния
is_speaking = False
last_response_time = 0
last_response = ("", "")

# фразы
MORTY_PHRASES = {
    'greeting': [
        "Э-эм... привет, Рик! Я готов к работе... наверное",
        "Окей, я включился... только не ори, пожалуйста",
        "Снова работаем? Ладно... я готов, вроде"
    ],
    'error': [
        "Ч-что? Я не понял... повтори медленнее!",
        "Э-это вообще по-русски? Я запутался...",
        "Рик, я не смог распознать... может, повторишь?"
    ],
    'result': [
        "Вот что я нашёл: {result}... это то, что нужно?",
        "Кажется, это {result}... надеюсь, я не ошибся",
        "Смотри, Рик! {result}... круто, да?"
    ],
    'action': [
        "Делаю... э-эм... только не взорви ничего!",
        "Пытаюсь выполнить... о боже, это страшно",
        "Ща сделаю... пожалуйста, не убивай меня"
    ],
    'exit': [
        "Фух... наконец-то закончили! Я устал...",
        "Вырубаюсь... если что, я в своей комнате",
        "Пока, Рик! Надеюсь, я не накосячил..."
    ]
}

def get_input_device():
    devices = sd.query_devices()
    input_devices = []
    for i, d in enumerate(devices):
        if d['max_input_channels'] > 0:
            print(f"{i}: {d['name']}")
            input_devices.append(i)
    
    if not input_devices:
        raise ValueError("No input devices found!")
    
    choice = int(input("Выберите микрофон: "))
    return choice

def callback(indata, frames, time, status):
    global is_speaking
    if not is_speaking:
        data = bytes(indata)
        if recognizer.AcceptWaveform(data):
            result = recognizer.Result()
            text = json.loads(result)["text"]
            q.put(text)

# Говорит Морти
def say_morty(key, result=None):
    global is_speaking, last_response_time, last_response
    is_speaking = True
    
    phrase = random.choice(MORTY_PHRASES[key])
    if result:
        phrase = phrase.format(result=result)
        last_response = (key, result)  # Сохраняем последний ответ
    
    print("🗣", phrase)
    engine.say(phrase)
    engine.runAndWait()
    
    is_speaking = False
    last_response_time = time.time()


#  Ассистент Морти
class MortyAssistant:
    def __init__(self):
        self.current_character = {}

    def random_character(self):
        say_morty('action')
        char_id = random.randint(1, 826)
        res = requests.get(f"https://rickandmortyapi.com/api/character/{char_id}").json()
        self.current_character = res
        say_morty('result', result=res['name'])

    def show_image(self):
        say_morty('action')
        webbrowser.open(self.current_character["image"])

    def save_image(self):
        say_morty('action')
        img_data = requests.get(self.current_character["image"]).content
        with open("character.png", "wb") as f:
            f.write(img_data)
        say_morty('result', result="Изображение сохранено!")

    def first_episode(self):
        say_morty('action')
        first_ep = self.current_character["episode"][0]
        ep_data = requests.get(first_ep).json()
        say_morty('result', result=ep_data["name"])

    def get_resolution(self):
        say_morty('action')
        from PIL import Image
        from io import BytesIO
        img_data = requests.get(self.current_character["image"]).content
        img = Image.open(BytesIO(img_data))
        res = f"{img.width} на {img.height} пикселей"
        say_morty('result', result=res)

    def handle_command(self, command):
        cmd = command.lower()
        if 'случайный' in cmd:
            self.random_character()
        elif 'показать' in cmd and self.current_character:
            self.show_image()
        elif 'сохранить' in cmd and self.current_character:
            self.save_image()
        elif 'эпизод' in cmd and self.current_character:
            self.first_episode()
        elif 'разрешение' in cmd and self.current_character:
            self.get_resolution()
        elif 'статус' in cmd and self.current_character:
            status = self.current_character.get('status', 'неизвестен')
            say_morty('result', result=f"его статус — {status}")
        elif 'локация' in cmd and self.current_character:
            location = self.current_character.get('location', {}).get('name', 'неизвестная локация')
            say_morty('result', result=f"он находится в {location}")
        elif 'где он был' in cmd and self.current_character:
            episodes = self.current_character.get('episode', [])
            num = len(episodes)
            say_morty('result', result=f"он появился в  {num} эпизодах")
        elif 'выход' in cmd or 'стоп' in cmd:
            say_morty('exit')
            return False
        else:
            say_morty('error')
        return True
    
# Загрузка голосовой модели
model = Model("model")  # путь к распакованной папке модели
recognizer = KaldiRecognizer(model, 16000)
q = queue.Queue()

# Настройка синтеза речи
engine = pyttsx3.init()
engine.setProperty('rate', 170)

# Переменная для хранения текущего персонажа
current_character = {}

# Функция для обработки аудио в реальном времени
def callback(indata, frames, time, status):
    data = bytes(indata)
    if recognizer.AcceptWaveform(data):
        result = recognizer.Result()
        text = json.loads(result)["text"]
        q.put(text)

def main():
    morty = MortyAssistant()
    device = get_input_device()
    
    say_morty('greeting')
    
    with sd.RawInputStream(device=device,
                          samplerate=16000,
                          blocksize=8000,
                          dtype='int16',
                          channels=1,
                          callback=callback):
        while True:
            global last_response_time
            # Проверка таймаута
            if time.time() - last_response_time > 10 and last_response[0]:
                say_morty('error', last_response[1])
            
            try:
                text = q.get(timeout=1)
                print("📥 Ты сказал:", text)
                if not morty.handle_command(text):
                    break
            except queue.Empty:
                continue

if __name__ == '__main__':
    main()

