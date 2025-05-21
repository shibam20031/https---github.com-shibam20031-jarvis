# main.py
import webbrowser
import pyautogui
import time
import urllib.parse
import wikipedia
import requests
from bs4 import BeautifulSoup
import subprocess
import pyttsx3
from pytube import Search
import eel
import threading
import queue
import datetime
import pyjokes
import sys
import re

eel.init('web')
speech_queue = queue.Queue()
assistant_active = True
user_name = ''
assistant_name = 'Jarvis'

# TTS setup
class TTSEngine:
    def __init__(self):
        self.engine = pyttsx3.init()
        voices = self.engine.getProperty('voices')
        self.engine.setProperty('voice', voices[1].id)  # female
        self.engine.setProperty('rate', 150)

    def speak(self, text):
        print("Speaking:", text)
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            print("TTS error:", e)

tts_engine = TTSEngine()

@eel.expose
def speak(text):
    print(f"Assistant: {text}")
    eel.updateResponse(text)
    speech_queue.put(text)

def speech_worker():
    while assistant_active:
        try:
            text = speech_queue.get(timeout=1)
            if text:
                tts_engine.speak(text)
            speech_queue.task_done()
        except queue.Empty:
            continue

@eel.expose
def wish_me():
    hour = datetime.datetime.now().hour
    if 0 <= hour < 12:
        speak(f"Good morning! I'm {assistant_name}. How can I help you?")
    elif 12 <= hour < 18:
        speak(f"Good afternoon! I'm {assistant_name}. How can I help you?")
    else:
        speak(f"Good evening! I'm {assistant_name}. How can I help you?")

@eel.expose
def take_command():
    import speech_recognition as sr
    r = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            eel.updateStatus("Listening...")
            r.adjust_for_ambient_noise(source, duration=1)
            audio = r.listen(source, timeout=5, phrase_time_limit=8)

        eel.updateStatus("Recognizing...")
        query = r.recognize_google(audio, language='en-in').lower()
        eel.updateStatus("Ready")
        print("You said:", query)
        eel.handle_web_command(query)  # immediately handle
        return query
    except:
        eel.updateStatus("Ready")
        speak("Sorry, I couldn't understand.")
        return "none"

def clean_wiki_text(text):
    return re.sub(r'\[\d+\]', '', text).replace('\n', ' ').strip()

def get_wikipedia_summary(query):
    try:
        query = query.replace("wikipedia", "").replace("search", "").replace("who is", "").replace("what is", "").strip()
        if not query:
            speak("Please specify what to search on Wikipedia.")
            return "Please specify what to search on Wikipedia."
        
        # First acknowledge we're getting the information
        speak(f"Let me look up {query} on Wikipedia...")
        
        # Then fetch the summary (this might take a moment)
        summary = wikipedia.summary(query, sentences=2)
        clean_summary = clean_wiki_text(summary)
        speak( assistant_name + " says: " + clean_summary)
        
        # Speak the summary in a separate thread to avoid blocking
        threading.Thread(target=speak, args=(clean_summary,)).start()
        
        return clean_summary
    except wikipedia.exceptions.DisambiguationError as e:
        error_msg = "There are multiple matches. Please be more specific."
        speak(error_msg)
        return error_msg
    except wikipedia.exceptions.PageError as e:
        error_msg = "I couldn't find any information on that topic."
        speak(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Wikipedia error: {str(e)}"
        speak(error_msg)
        return error_msg
def play_on_youtube(query):
    try:
        query = query.replace("play", "").replace("on youtube", "").strip()
        s = Search(query)
        if s.results:
            video = s.results[0]
            webbrowser.open(f"https://youtube.com/watch?v={video.video_id}")
            return f"Playing {video.title} on YouTube."
        return "No video found."
    except Exception as e:
        return f"YouTube error: {str(e)}"

def search_google(query):
    try:
        query = query.replace("search", "").replace("on google", "").strip()
        if not query:
            return "What do you want to search?"
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        webbrowser.open(url)
        return f"Searching Google for: {query}"
    except Exception as e:
        return f"Search failed: {str(e)}"

def open_application(app_name):
    app_paths = {
        'notepad': 'notepad.exe',
        'calculator': 'calc.exe',
        'paint': 'mspaint.exe'
    }
    try:
        app = app_name.strip().lower()
        if app in app_paths:
            subprocess.Popen(app_paths[app])
            return f"Opened {app}."
        return "Application not recognized."
    except Exception as e:
        return str(e)

def get_weather(city="India"):
    try:
        api_key = "d850f7f52bf19300a9eb4b0aa6b80f0d"
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}"
        data = requests.get(url, timeout=5).json()
        if data["cod"] != 200:
            return "City not found."
        temp = data["main"]["temp"] - 273.15
        desc = data["weather"][0]["description"]
        speak( f"{city} weather: {desc}, {temp:.1f}°C")
        return f"{city} weather: {desc}, {temp:.1f}°C"
    except:
        return "Could not get weather info."

def get_news():
    try:
        url = "https://www.bbc.com/news"
        soup = BeautifulSoup(requests.get(url).text, 'html.parser')
        headlines = [h.text.strip() for h in soup.find_all('h3') if h.text.strip()]
        return "Top news:\n" + "\n".join(headlines[:5])
    except:
        return "Couldn't fetch news."

@eel.expose
def handle_web_command(command):
    command = command.lower()
    result = None  # Initialize as None

    if "wikipedia" in command or "who is" in command or "what is" in command:
        # Start Wikipedia search in a separate thread to prevent UI blocking
        threading.Thread(
            target=lambda: get_wikipedia_summary(command),
            daemon=True
        ).start()
        return "Searching Wikipedia..."  # Immediate response


    elif "play" in command and "youtube" in command:
        result = play_on_youtube(command)
        speak(result)

    elif "open youtube" in command:
        webbrowser.open("https://www.youtube.com")
        result = "Opening YouTube."
        speak(result)

    elif "open google" in command:
        webbrowser.open("https://www.google.com")
        result = "Opening Google."
        speak(result)

    elif "search" in command and "google" in command:
        result = search_google(command)
        speak(result)

    elif "open" in command:
        app = command.split("open")[-1].strip()
        result = open_application(app)
        speak(result)

    elif "weather" in command:
        city = command.split("in")[-1].strip() if "in" in command else "India"
        result = get_weather(city)
        speak(result)

    elif "news" in command:
        result = get_news()
        speak(result)

    elif "joke" in command:
        result = pyjokes.get_joke()
        speak(result)

    elif "time" in command:
        result = datetime.datetime.now().strftime("%I:%M %p")
        speak(f"The current time is {result}")

    elif "date" in command:
        result = datetime.datetime.now().strftime("%B %d, %Y")
        speak(f"Today's date is {result}")

    elif "bye" in command or "exit" in command:
        global assistant_active
        assistant_active = False
        result = "Goodbye!"
        speak(result)

    elif not result:  # Only say this if no other command was matched
        result = "Sorry, I didn't understand that."
        speak(result)

    return result  # Return the result for any potential UI updates

# Start speech thread and app
if __name__ == '__main__':
    threading.Thread(target=speech_worker, daemon=True).start()
    eel.start('index.html', size=(900, 700), mode='chrome')