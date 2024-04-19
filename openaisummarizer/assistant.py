import re
import os
import sys
import tkinter as tk
from tkinter import scrolledtext, simpledialog, Checkbutton, Label, messagebox
import sounddevice as sd
import soundfile as sf
from openai import OpenAI
import tempfile
from pydub import AudioSegment, playback
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from base64 import urlsafe_b64encode, urlsafe_b64decode
import threading
import tkinter as tk
from queue import Queue, Empty
import pyaudio
from pydub.utils import make_chunks

# key_file = 'openai_api.key'
# key_path = os.path.join(os.path.expanduser('~'), key_file)
# key_file_enc = 'openai_api.enc'
# key_path_enc = os.path.join(os.path.expanduser('~'), key_file_enc)
api_key_incorrect = ""
and_get_response = ""
system_cue = f"---- System ----\n"
user_cue = f"---- User Input Transcript ----\n"
assistant_cue = f"\n---- Documentation Assistant ----\n"

init_message = [
    {"role": "system", "content": "You are an assistant who helps the user logging and documenting. "
                                    "Your task is to summarize a transcript of what the user has entered via a "
                                    "speech-to-text interface. The goal is to digest the user input and create a "
                                    "text that is structured, understandable, complete and uses concise language. "
                                    "Keep the same narrative perspective as the transcript. It is possible that the "
                                    "input is split up into multiple overlapping segments so don't be surprised to "
                                    "see duplicated sentences. "}
]
counter = 1
toggle_recording = False
active_playback = False
playback_thread = threading.Thread()

# A queue to hold results from the background thread
result_queue = Queue()

def exit_program():
    print("Exiting the program...")
    sys.exit(0)

def clean_up_files():
    global temp_file, mp3_file
    try:
        temp_file.close()
        mp3_file.close()
        os.remove(temp_file.name)
        os.remove(mp3_file.name)
    except Exception as e:
        print(f"Error deleting file: {e}")

    result_queue.put(lambda: button_whisper.config(text='Start Recording', command=start_recording, state=tk.NORMAL))

def process_queue():
    try:
        func = result_queue.get_nowait()
    except Empty:
        pass
    else:
        func()
    finally:
        # Schedule the next poll
        root.after(100, process_queue)

# Function to derive a key from the password
def derive_key(password: str, salt: bytes, iterations: int = 100000):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
        backend=default_backend()
    )
    return urlsafe_b64encode(kdf.derive(password.encode()))

# Encrypt API key
def encrypt_api_key(api_key, password):
    salt = os.urandom(16)
    key = derive_key(password, salt)
    fernet = Fernet(key)
    encrypted_key = fernet.encrypt(api_key.encode())
    return urlsafe_b64encode(salt + encrypted_key).decode()

# Decrypt API key
def decrypt_api_key(encrypted_key, password):
    try:
        data = urlsafe_b64decode(encrypted_key.encode())
        salt, encrypted_key = data[:16], data[16:]
        key = derive_key(password, salt)
        fernet = Fernet(key)
        return fernet.decrypt(encrypted_key).decode()
    except Exception as e:
        return None

def check_API_key(api_key): 
    try: 
        OpenAI(api_key=api_key).models.list() 
        return True 
    except: 
        return False

def load_or_request_api_key():
    key_path = os.path.join(os.path.expanduser('~'), 'openai_api.enc')
    while True:
        if os.path.exists(key_path):
            with open(key_path, 'rb') as file:
                encrypted_key = file.read().decode()
            password = simpledialog.askstring("Password", "Enter your password:", show="*")
            if password is None:
                exit_program()
            api_key = decrypt_api_key(encrypted_key, password)
            if api_key and check_API_key(api_key):
                return api_key
            reply = messagebox.askyesnocancel("Invalid Password", "Invalid password. Would you like to retry (Yes) or enter a new OpenAI API Key (No)?")
            if reply == messagebox.NO:
                os.remove(key_path)
            if reply is None:
                exit_program()
        else:
            api_key = simpledialog.askstring("API Key", "Enter your OpenAI API Key:")
            if api_key and check_API_key(api_key):
                password = simpledialog.askstring("Password", "Create a password:", show="*")
                if password is None:
                    exit_program()
                encrypted_key = encrypt_api_key(api_key, password)
                with open(key_path, 'wb') as file:
                    file.write(encrypted_key.encode())
                return api_key
            elif api_key:
                messagebox.showwarning("Invalid API Key", "The provided API key is invalid. Please try again.")
            else:
                exit_program()

def start_recording():
    global audio_data, stream, temp_file, file_writer, toggle_recording
    temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    audio_data = []
    toggle_recording = True
    button_whisper.config(text='Stop Recording' + and_get_response, command=stop_recording)

    # Open stream for recording and a file writer to save the data
    file_writer = sf.SoundFile(temp_file.name, mode='w', samplerate=44100, channels=1, format='WAV')
    stream = sd.InputStream(samplerate=44100, channels=1, callback=audio_callback)
    stream.start()
    return

def stop_recording():
    global stream, mp3_file, counter, user_cue, toggle_recording
    toggle_recording = None
    button_whisper.config(text='Processing ...', command=start_recording, state=tk.DISABLED)
    stream.stop()
    stream.close()
    file_writer.close()

    # Convert WAV to MP3
    sound = AudioSegment.from_wav(temp_file.name)
    mp3_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
    sound.export(mp3_file.name, format="mp3")

    # Transcription
    transcript = transcribe_audio()
    textfield_add(transcript)   # Insert new text
    # Summarization
    if toggle_combine.get():
        async_summarize_text()
    # Cleanup
    clean_up_files()
    button_whisper.config(text='Start Recording', command=start_recording, state=tk.NORMAL)
    toggle_recording = False

def audio_callback(indata, frames, time, status):
    if status:
        print(status)
    file_writer.write(indata)  # Write data directly to file
    return
    
def transcribe_audio():
    with open(mp3_file.name, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-1", 
            response_format="verbose_json"
        )
    return transcription.text

def textfield_parse():
    global text_field, user_cue, assistant_cue
    cur_text = text_field.get("1.0", tk.END)
    sections = re.split(r'\n\n\=\= \d+ \=\=', cur_text)[0:]  # Skip the first split as it's empty
    formatted_data = []
    # Process each section to extract the user input and assistant response
    for section in sections:
        split_section = section.split(user_cue)[1].split(assistant_cue)
        # Append user part to the list as dictionary
        user_input = split_section[0].strip()
        formatted_data.append({"role": "user", "content": user_input})
        # Append assistant part to the list as dictionary
        if len(split_section) > 1 and len(split_section[1].strip()) > 1:
            assistant_response = split_section[1].strip()
            formatted_data.append({"role": "assistant", "content": assistant_response})
    return formatted_data

def async_summarize_text():
    # Run summarization in a separate thread
    threading.Thread(target=summarize_text).start()

def summarize_text():
    global assistant_cue, user_cue, counter
    textfield_add(assistant_cue)
    # Summarize the transcript using GPT-4 API
    completion = client.chat.completions.create(
        model="gpt-4-turbo",
        messages= init_message + textfield_parse()
    )
    textfield_add(f"{completion.choices[0].message.content}\n")
    if toggle_playback.get():
        async_playback_response(f"{completion.choices[0].message.content}")
    counter += 1
    textfield_add(f"\n== {counter} ==\n")
    textfield_add(user_cue)
    result_queue.put(lambda: button_whisper.config(text='Start Recording', command=start_recording, state=tk.NORMAL))

def async_playback_response(text):
    global playback_thread, stop_event
    stop_event = threading.Event()  # Event to signal stopping
    playback_thread = threading.Thread(target=playback_response, args=(text,))
    playback_thread.start()

def playback_response(text):
    try:
        mp3_response = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
        response = client.audio.speech.create(
            model="tts-1",
            voice="shimmer",
            input=text
        )
        response.write_to_file(mp3_response.name)
        audio_segment = AudioSegment.from_mp3(mp3_response.name)

        # Use PyAudio to play
        p = pyaudio.PyAudio()
        stream = p.open(format=p.get_format_from_width(audio_segment.sample_width),
                        channels=audio_segment.channels,
                        rate=audio_segment.frame_rate,
                        output=True)

        # Break audio into chunks and play each chunk
        chunk_length_ms = 100  # Length of each chunk in milliseconds
        chunks = make_chunks(audio_segment, chunk_length_ms)

        for chunk in chunks:
            if stop_event.is_set():
                break
            stream.write(chunk._data)

        stream.stop_stream()
        stream.close()
        p.terminate()
    finally:
        mp3_response.close()
        os.remove(mp3_response.name)

def stop_playback():
    global playback_thread, stop_event
    if playback_thread.is_alive():
        stop_event.set()  # Signal the thread to stop
        playback_thread.join()  # Now wait for it to finish

def textfield_add(text):
    global text_field
    text_field.insert(tk.END, text)
    return

def combine_toggled():
    global button_gpt, toggle_combine, and_get_response
    if toggle_combine.get():
        button_gpt.configure(state=tk.DISABLED)
        and_get_response=" and generate response"
    else:
        button_gpt.configure(state=tk.NORMAL)
        and_get_response=""

def on_ctrl_space(event):
    global toggle_recording
    if toggle_recording:
        stop_recording()
    elif toggle_recording is None:
        pass
    else:
        start_recording()

def on_ctrl_enter(event):
    cur_text = textfield_parse()
    if cur_text:
        if cur_text[-1]["role"] != "assistant":
            async_summarize_text()
        
def start_stop_playback(event=None):
    if playback_thread.is_alive():
        stop_playback()
    else:
        cur_text = textfield_parse()
        text = [c["content"] for c in cur_text if c["content"]][-1]
        async_playback_response(text)

# Main logic
if __name__ == "__main__":

    client = OpenAI(api_key = load_or_request_api_key())

    # Initialize the main window
    root = tk.Tk()
    root.title("Summarizer")

    # Configure the grid for flexibility
    root.grid_rowconfigure(0, weight=1)
    root.grid_rowconfigure(1, weight=0)  # Ensure the button row doesn't expand
    root.grid_columnconfigure(0, weight=1)
    root.grid_columnconfigure(1, weight=1)  # Adding a second column

    # Create a scrolled text field that resizes with the window
    text_field = scrolledtext.ScrolledText(root, wrap=tk.WORD, font=("Consolas", 11), state=tk.NORMAL)
    text_field.grid(row=0, column=0, columnspan=2, sticky="nsew")  # Stick to all sides of the grid cell
    textfield_add(f"\n== {counter} ==\n")
    textfield_add(user_cue)
    text_field.bind('<Control-Return>', lambda *args: None)
    text_field.bind('<Control-m>', lambda *args: None)

    # Create a button that sticks at the bottom
    button_whisper = tk.Button(root, text='Start Recording', command=start_recording)
    button_whisper.grid(row=1, column=0, sticky="ew")  # Stick to left and right, centered horizontally

    button_gpt = tk.Button(root, text='Get response', command=summarize_text, state=tk.DISABLED)
    button_gpt.grid(row=1, column=1, sticky="ew")

    button_playback = tk.Button(root, text='Read last', command=start_stop_playback)
    button_playback.grid(row=2, column=1, sticky="w")

    toggle_playback = tk.IntVar(value=1)
    check_button = Checkbutton(root, text="Audio Playback", variable=toggle_playback, command=stop_playback)
    check_button.grid(row=2, column=1, sticky="e")

    toggle_combine = tk.IntVar(value=1)
    check_button = Checkbutton(root, text="Combine STT & ChatGPT", variable=toggle_combine, command=combine_toggled)
    check_button.grid(row=2, column=0, sticky="e")

    label = Label(root, text="Toggle voice input and summarization:")
    label.grid(row=2, column=0, sticky="w")

    # Binding a single key press
    root.bind('<Control-space>', on_ctrl_space)
    root.bind('<Control-Return>', on_ctrl_enter)
    root.bind('<Control-m>', start_stop_playback)

    root.after(100, process_queue)
    root.mainloop()
    
