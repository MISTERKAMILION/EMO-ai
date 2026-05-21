import pyttsx3
import time
import threading

speech_lock = threading.Lock()


def speak(text):
    if not text:
        return

    with speech_lock:
        print(f'BMO says: {text}')
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        if voices:
            engine.setProperty('voice', voices[0].id)
        engine.setProperty('rate', 140)
        engine.setProperty('volume', 1.0)
        engine.say(text)
        engine.runAndWait()
        engine.stop()

    time.sleep(2)


# Testing
if __name__ == '__main__':
    speak("I'm BEEMOO")
    speak("I'm fish")
    speak("I'm ready")
