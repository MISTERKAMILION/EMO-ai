# Emo Advanced - Multi-Feature AI (No Vision)
# 1. Start Ollama: ollama serve
# 2. Run this file

import re
import requests
import webbrowser
import json
import threading
import time
import os
from tkinter import BOTH, DISABLED, END, NORMAL, Button, Canvas, Entry, Frame, Label, StringVar, Text, Tk, simpledialog
from pathlib import Path

import cv2
import speech

# --- CONFIGURATION ---
MEMORY_FILE = Path(__file__).with_name("memory.json")
OLLAMA_CHAT_URL = "http://127.0.0.1:11434/api/chat"
MODEL_NAME = "qwen2.5:3b"

CAMERA_COMMANDS = ("take a picture", "take a pic", "capture image", "capture a photo", "take a photo", "open camera")
IMAGE_GEN_COMMANDS = ("generate image", "create image", "make a picture", "draw", "generate a photo")
MAP_TRIGGER_WORDS = ("closest", "nearest", "near me", "nearby", "close to me", "find me a", "where is the",
                     "where's the", "around me")

# IMAGE STYLES
STYLES = {
    "1": "Photorealistic", "2": "Anime/Manga", "3": "Cyberpunk",
    "4": "Oil Painting", "5": "3D Render", "6": "Sketch/Drawing"
}
RATIOS = {
    "1": (1024, 1024, "Square"),
    "2": (1280, 720, "Landscape"),
    "3": (720, 1280, "Portrait")
}

messages = [{"role": "system",
             "content": "Your name is Emo. You are a tiny playful boy. Be silly and friendly. Maker: Webs (#webs1001)."}]
state = {"emotion": "neutral", "status": "Ready", "speaking": False, "busy": False}


# --- CORE FUNCTIONS ---

def load_memory():
    global messages
    if MEMORY_FILE.exists():
        try:
            with open(MEMORY_FILE, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    messages = [messages[0]] + data
        except Exception as e:
            print(f"Load error: {e}")

def save_memory():
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(messages[1:], f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Save error: {e}")

def open_pc_file(filename):
    """Searches Administrateur's folders, PycharmProjects, and System32."""
    base_user = Path("C:/Users/Administrateur")
    search_paths = [
        base_user / "Desktop",
        base_user / "Documents",
        base_user / "Downloads",
        base_user / "PycharmProjects",
        Path("C:/ProgramData/Microsoft/Windows/Start Menu/Programs"),
        Path("C:/Windows/System32")
    ]

    found_files = []
    possible_names = [filename]
    if "." not in filename:
        possible_names.extend([f"{filename}.exe", f"{filename}.lnk", f"{filename}.py", f"{filename}.txt"])

    for path in search_paths:
        if not path.exists():
            continue
        try:
            for name in possible_names:
                exact_path = path / name
                if exact_path.is_file():
                    found_files.append(exact_path)
            for file in path.rglob(f"*{filename}*"):
                if file.is_file() and not file.name.startswith(('$', '~')):
                    found_files.append(file)
        except Exception:
            continue

    if found_files:
        target = min(found_files, key=lambda x: len(x.name))
        try:
            os.startfile(target)
            return f"Beep boop! I found it! Opening {target.name} now!"
        except Exception as e:
            return f"I found it, but my tiny hands couldn't open it: {e}"

    return f"I looked everywhere in your folders, Webs, but I couldn't find '{filename}'."

def capture_image():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return None
    set_state(emotion="shocked", status="Cheese! 📸")
    time.sleep(1)
    ret, frame = cap.read()
    cap.release()
    if ret:
        file_name = "captured_image.jpg"
        cv2.imwrite(file_name, frame)
        return file_name
    return None


# --- IMAGE CUSTOMIZATION HELPERS ---

def ask_custom_config():
    results = {}

    def _ask():
        count = simpledialog.askinteger("Emo Art", "How many images? (1-5)", parent=root, minvalue=1, maxvalue=5)
        if not count:
            results['data'] = None
            return

        style_msg = "Choose a style number:\n" + "\n".join([f"{k}: {v}" for k, v in STYLES.items()])
        style_idx = simpledialog.askstring("Emo Art", style_msg, parent=root)
        if not style_idx:
            results['data'] = None
            return
        style_name = STYLES.get(style_idx, "Digital Art")

        ratio_msg = "Choose Ratio:\n1: Square\n2: Landscape\n3: Portrait"
        ratio_idx = simpledialog.askstring("Emo Art", ratio_msg, parent=root)
        if not ratio_idx:
            results['data'] = None
            return
        w, h, r_name = RATIOS.get(ratio_idx, RATIOS["1"])

        results['data'] = (count, style_name, w, h)

    root.after(0, _ask)
    # Wait for dialog to complete (with timeout to avoid infinite hang)
    timeout = 60
    elapsed = 0
    while 'data' not in results and elapsed < timeout:
        time.sleep(0.1)
        elapsed += 0.1

    if 'data' not in results:
        return None
    return results.get('data')

def generate_image_logic(prompt):
    config = ask_custom_config()
    if not config:
        return None
    count, style, w, h = config

    generated_files = []
    try:
        for i in range(count):
            set_state(status=f"Drawing {i + 1}/{count}...")
            full_prompt = f"{prompt}, {style} style, high quality"
            clean_p = full_prompt.replace(" ", "%20")
            seed = int(time.time()) + i
            url = (
                f"https://image.pollinations.ai/prompt/{clean_p}"
                f"?width={w}&height={h}&seed={seed}&nologo=true&model=flux"
            )
            response = requests.get(url, timeout=60)
            if response.status_code == 200:
                fname = f"emo_art_{i + 1}.png"
                with open(fname, "wb") as f:
                    f.write(response.content)
                generated_files.append(fname)
    except Exception as e:
        print(f"Image generation error: {e}")
        return None

    return generated_files if generated_files else None


# --- MESSAGE PROCESSING ---

def process_user_message(user_input):
    if not user_input:
        set_state(busy=False)
        return
    lowered = user_input.lower()

    # 1. FILE/APP COMMANDS
    RUN_TRIGGERS = ("open ", "run ", "start ", "launch ")
    for cmd in RUN_TRIGGERS:
        if lowered.startswith(cmd):
            target_name = lowered[len(cmd):].strip()
            if target_name:
                append_chat_line("You", user_input)
                set_state(emotion="talking", status=f"Searching for {target_name}...")
                result = open_pc_file(target_name)
                finalize_action(result, "happy" if "Opening" in result else "sad")
                return

    # 2. CAMERA COMMANDS
    if any(cmd in lowered for cmd in CAMERA_COMMANDS):
        append_chat_line("You", user_input)
        path = capture_image()
        finalize_action("Pic captured!" if path else "Camera error!", "happy" if path else "sad")
        return

    # 3. IMAGE GENERATION
    if any(cmd in lowered for cmd in IMAGE_GEN_COMMANDS):
        append_chat_line("You", user_input)
        prompt = lowered
        for cmd in IMAGE_GEN_COMMANDS:
            prompt = prompt.replace(cmd, "")
        prompt = prompt.strip() or "something magical"
        set_state(emotion="talking", status="Preparing canvas...")
        images = generate_image_logic(prompt)
        if images:
            for p in images:
                os.startfile(p)
            finalize_action(f"I finished {len(images)} drawings for you!", "happy")
        else:
            finalize_action("I couldn't draw that today.", "sad")
        return

    # 4. MAPS
    if any(trigger in lowered for trigger in MAP_TRIGGER_WORDS):
        append_chat_line("You", user_input)
        webbrowser.open("https://www.google.com/maps/search/" + user_input.replace(" ", "+"))
        finalize_action("Opening maps! Beep boop!", "happy")
        return

    # 5. CHAT
    append_chat_line("You", user_input)
    set_state(emotion="shocked", status="Thinking...")
    messages.append({"role": "user", "content": user_input})
    reply = stream_ollama_chat(messages)
    if reply:
        finalize_action(reply, "happy")
    else:
        messages.pop()  # remove user msg if no reply
        finalize_action("Oops! My brain glitched. Try again!", "sad")

def finalize_action(reply, emo):
    messages.append({"role": "assistant", "content": reply})
    append_chat_line("Emo", reply)
    set_state(emotion=emo, status="Ready", busy=False)
    speak_text(reply, restore_emotion=emo)
    save_memory()


# --- UI & UTILS ---

def set_state(emotion=None, status=None, speaking=None, busy=None):
    if emotion is not None:
        state["emotion"] = emotion
    if status is not None:
        state["status"] = status
        root.after(0, lambda: status_var.set(status))
    if speaking is not None:
        state["speaking"] = speaking
    if busy is not None:
        state["busy"] = busy
        root.after(0, update_input_state)

def update_input_state():
    val = DISABLED if state["busy"] else NORMAL
    user_entry.config(state=val)
    send_button.config(state=val)
    if not state["busy"]:
        user_entry.focus_set()

def append_chat_line(speaker, text):
    def _insert():
        chat_log.config(state=NORMAL)
        chat_log.insert(END, f"{speaker}: {text}\n\n")
        chat_log.see(END)
        chat_log.config(state=DISABLED)
    root.after(0, _insert)

def speak_text(text, restore_emotion="neutral"):
    def worker():
        set_state(emotion="talking", status="Speaking...", speaking=True)
        try:
            speech.speak(text)
        except Exception as e:
            print(f"Speech error: {e}")
        root.after(500, lambda: set_state(emotion=restore_emotion, status="Ready", speaking=False))
    threading.Thread(target=worker, daemon=True).start()

def stream_ollama_chat(chat_messages):
    payload = {
        "model": MODEL_NAME,
        "messages": chat_messages,
        "stream": False
    }
    try:
        response = requests.post(
            OLLAMA_CHAT_URL,
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        data = response.json()
        content = data.get("message", {}).get("content", "")
        # Strip qwen3 <think>...</think> blocks
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        return content if content else "No response."
    except requests.exceptions.ConnectionError:
        return "Ollama is not running! Start it with: ollama serve"
    except requests.exceptions.Timeout:
        return "Ollama took too long! Maybe try a smaller model?"
    except requests.exceptions.HTTPError as e:
        return f"HTTP error: {e}"
    except Exception as e:
        return f"Error: {e}"

def submit_message(event=None):
    user_input = user_entry.get().strip()
    if user_input and not state["busy"]:
        user_entry.delete(0, END)
        set_state(busy=True)
        threading.Thread(target=process_user_message, args=(user_input,), daemon=True).start()

def draw_face():
    canvas.delete("all")
    canvas.create_rectangle(0, 0, 500, 260, fill="#0b1f1f", outline="")
    canvas.create_rectangle(85, 40, 415, 220, fill="#b8fff3", outline="#80fff0", width=3)
    emotion = state["emotion"]
    if emotion == "shocked":
        canvas.create_oval(155, 95, 175, 115, fill="#244040")
        canvas.create_oval(325, 95, 345, 115, fill="#244040")
        canvas.create_oval(230, 155, 270, 195, fill="#244040")
    elif state["speaking"]:
        canvas.create_rectangle(145, 100, 180, 107, fill="#244040")
        canvas.create_rectangle(320, 100, 355, 107, fill="#244040")
        if int(time.time() * 4) % 2 == 0:
            canvas.create_oval(225, 160, 275, 190, fill="#244040")
        else:
            canvas.create_rectangle(225, 170, 275, 175, fill="#244040")
    else:
        canvas.create_rectangle(145, 100, 180, 107, fill="#244040")
        canvas.create_rectangle(320, 100, 355, 107, fill="#244040")
        canvas.create_rectangle(210, 170, 290, 175, fill="#244040")
    root.after(120, draw_face)


# --- APP START ---
root = Tk()
root.title("Emo AI")
root.geometry("560x720")
root.configure(bg="#0b1f1f")

status_var = StringVar(value="Ready")
canvas = Canvas(root, width=500, height=260, bg="#0b1f1f", highlightthickness=0)
canvas.pack(pady=12)

Label(root, textvariable=status_var, fg="#d6fff8", bg="#0b1f1f", font=("Consolas", 12)).pack()

chat_log = Text(root, height=14, width=52, bg="#112828", fg="#d6fff8", font=("Consolas", 11), state=DISABLED)
chat_log.pack(padx=16, pady=10, fill=BOTH, expand=True)

input_frame = Frame(root, bg="#0b1f1f")
input_frame.pack(fill="x", padx=16, pady=16)

user_entry = Entry(input_frame, bg="#b8fff3", font=("Consolas", 12))
user_entry.pack(side="left", fill="x", expand=True, ipady=10, padx=8)
user_entry.bind("<Return>", submit_message)

send_button = Button(input_frame, text="Send", command=submit_message, bg="#80fff0", font=("Consolas", 11, "bold"))
send_button.pack(side="right")

load_memory()
draw_face()
root.mainloop()