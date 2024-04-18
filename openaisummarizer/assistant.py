import re
import os
import tkinter as tk
from tkinter import scrolledtext, simpledialog, Checkbutton, Label
import sounddevice as sd
import soundfile as sf
from openai import OpenAI
import tempfile
from time import sleep
from pydub import AudioSegment
from cryptography.fernet import Fernet

key_file = 'openai_api.key'
key_path = os.path.join(os.path.expanduser('~'), key_file)
key_file_enc = 'openai_api.enc'
key_path_enc = os.path.join(os.path.expanduser('~'), key_file_enc)
api_key_incorrect = ""
and_get_response = ""

# Function to load or request API key
def load_or_request_api_key():
    global key_file_enc, key_path_enc
    # Try to load the existing encrypted key
    if os.path.exists(key_path_enc):
        with open(key_path_enc, 'rb') as file:
            encrypted_key = file.read()
        fernet = Fernet(load_encryption_key())
        api_key = fernet.decrypt(encrypted_key).decode()
        return api_key
    else:
        root = tk.Tk()
        root.withdraw()  # Hide the root window
        api_key = simpledialog.askstring("API Key", api_key_incorrect +"Enter your API Key:", parent=root)
        if api_key:
            save_api_key(api_key, key_path_enc)
        root.destroy()
        if api_key == "":
            return None
        return api_key

# Function to save the API key encrypted
def save_api_key(api_key, key_path):
    fernet = Fernet(generate_encryption_key())
    encrypted_key = fernet.encrypt(api_key.encode())
    with open(key_path, 'wb') as file:
        file.write(encrypted_key)

# Generate a new encryption key and save it or load the existing one
def generate_encryption_key():
    global key_file, key_path
    if not os.path.exists(key_path):
        key = Fernet.generate_key()
        with open(key_path, 'wb') as key_file:
            key_file.write(key)
        return key
    else:
        with open(key_path, 'rb') as key_file:
            return key_file.read()

# Function to load the existing encryption key
def load_encryption_key():
    global key_file, key_path
    with open(key_path, 'rb') as key_file:
        return key_file.read()


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

def start_recording():
    global audio_data, stream, temp_file, file_writer
    temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    audio_data = []
    button_whisper.config(text='Stop Recording'+and_get_response, command=stop_recording)
    
    # Open stream for recording and a file writer to save the data
    file_writer = sf.SoundFile(temp_file.name, mode='w', samplerate=44100, channels=1, format='WAV')
    stream = sd.InputStream(samplerate=44100, channels=1, callback=audio_callback)
    stream.start()

def stop_recording():
    global stream, mp3_file, counter, user_cue, assistant_cue
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
    textfield_add(assistant_cue)
    # Summarization
    if toggle.get():
        summarize_text()
    # Cleanup
    while True:
        try:
            temp_file.close()
            mp3_file.close()
            os.remove(temp_file.name)
            os.remove(mp3_file.name)
            break
        except Exception as e:
            print(f"Error deleting file: {e}")
        sleep(0.1)
    button_whisper.config(text='Start Recording', command=start_recording, state=tk.NORMAL)

def audio_callback(indata, frames, time, status):
    if status:
        print(status)
    file_writer.write(indata)  # Write data directly to file
    
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
        if len(split_section) > 1:
            assistant_response = split_section[1].strip()
            formatted_data.append({"role": "assistant", "content": assistant_response})
    return formatted_data

def summarize_text():
    global assistant_cue, user_cue, counter
    # Summarize the transcript using GPT-4 API
    completion = client.chat.completions.create(
        model="gpt-4-turbo",
        messages= init_message + textfield_parse()
    )
    textfield_add(f"{completion.choices[0].message.content}\n")
    counter += 1
    textfield_add(f"\n== {counter} ==\n")
    textfield_add(user_cue)
    return

def textfield_add(text):
    global text_field
    text_field.insert(tk.END, text)

def toggled():
    global button_gpt, toggle, and_get_response
    if toggle.get():
        button_gpt.configure(state=tk.DISABLED)
        and_get_response=" and generate response"
    else:
        button_gpt.configure(state=tk.NORMAL)
        and_get_response=""

# Main logic
if __name__ == "__main__":
    while True:
        api_key = load_or_request_api_key()
        if api_key:
            try:
                client = OpenAI(api_key=api_key)
                client.models.list()
                break
            except:
                os.remove(key_path_enc)
                os.remove(key_path)
                api_key_incorrect = f"The key you entered was incorrect\n"
                print("API Key invalid")
        elif api_key is None:
            print("Closing window.")
            break
        else:
            print("No API Key provided.")
            
    client = OpenAI(api_key=api_key)

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

    # Create a button that sticks at the bottom
    button_whisper = tk.Button(root, text='Start Recording', command=start_recording)
    button_whisper.grid(row=1, column=0, sticky="ew")  # Stick to left and right, centered horizontally

    button_gpt = tk.Button(root, text='Get response', command=summarize_text, state=tk.DISABLED)
    button_gpt.grid(row=1, column=1, sticky="ew")

    toggle = tk.IntVar(value=1)
    check_button = Checkbutton(root, text="Enable Feature", variable=toggle, command=toggled)
    check_button.grid(row=2, column=1, sticky="e")  # Align to the right

    label = Label(root, text="Toggle voice input and summarization:")
    label.grid(row=2, column=0, sticky="e")  # Align to the left

    root.mainloop()
