import json
import queue
import random
import requests
import sounddevice as sd
import pyttsx3
from vosk import Model, KaldiRecognizer
import webbrowser
import time

# подгрузка модели vosk
recognizer = KaldiRecognizer(Model("model"), 16000)
audio_queue = queue.Queue() 

# настройки TTS
tts_engine = pyttsx3.init() # инит голосового движка
tts_engine.setProperty('rate', 180) #cкорость речи Морти
is_speaking = False
last_speech_time = 0  # время последнего синтеза речи

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

def audio_callback(indata, frames, time, _):#обрабатывает информацию с микро
    data = bytes(indata) # преобразуем в массив байт (для Vosk)
    if recognizer.AcceptWaveform(data):
        result = json.loads(recognizer.Result()) #результат распознования
        if result.get("text"):  # проверка на наличие текста
            audio_queue.put(result["text"])


def say_morty(key, result=None): #key - тип фразы
    global last_speech_time
    phrase = random.choice(MORTY_PHRASES[key]) #рандомная фраза по ключу
    if result:
        phrase = phrase.format(result=result)

    print("🤯", phrase)
    tts_engine.say(phrase)  # синтез речи
    tts_engine.runAndWait()  # ожидаем завершения синтеза
    last_speech_time = time.time()  # обновляем время последней речи

class MortyAssistant:
    def __init__(self):
        self.current_character = {} # словарь с данными от текущ персонаже

    def random_character(self): #получаем слчайного персонажа из API 
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
        res = f"{img.width}×{img.height} пикселей"
        say_morty('result', result=res)

    def handle_command(self, command):
        cmd = command.lower()
        if 'случайный' in cmd:
            self.random_character()
        elif 'покажи' in cmd and self.current_character:
            self.show_image()
        elif 'сохрани' in cmd and self.current_character:
            self.save_image()
        elif 'эпизод' in cmd and self.current_character:
            self.first_episode()
        elif 'разрешени' in cmd and self.current_character:
            self.get_resolution()
        elif 'статус' in cmd and self.current_character:
            status = self.current_character.get('status', 'неизвестен')
            say_morty('result', result=f"его статус — {status}")
        elif 'локаци' in cmd and self.current_character:
            location = self.current_character.get('location', {}).get('name', 'неизвестная локация')
            say_morty('result', result=f"он находится в {location}")
        elif 'где он был' in cmd and self.current_character:
            episodes = self.current_character.get('episode', [])
            num = len(episodes)
            say_morty('result', result=f"он появился в {num} эпизодах")
        elif 'выход' in cmd or 'стоп' in cmd:
            say_morty('exit')
            return False
        else:
            say_morty('error')
        return True

def main():
    morty = MortyAssistant()
    device = 1 #микрофон
    
    say_morty('greeting')
    
    with sd.RawInputStream( # считываем аудио с микро
        device=device,
        samplerate=16000,
        blocksize=8000,
        dtype='int16',
        channels=1,
        callback=audio_callback
    ):
        while True:
            global last_speech_time
           
            try:
                text = audio_queue.get(timeout=1)
                
                # игнорируем команды, если прошло меньше 2 секунд после последней речи
                if time.time() - last_speech_time < 2:
                    continue
                
                if text.strip():  # Убедимся, что строка не пустая
                    print("💀 Рик:", text)
                    if not morty.handle_command(text):
                        break
                else:
                    say_morty('error')
            except queue.Empty:
                continue

if __name__ == '__main__':
    main()