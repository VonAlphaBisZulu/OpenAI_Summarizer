import tkinter as tk
from tkinter import scrolledtext
import sounddevice as sd
import soundfile as sf
from openai import OpenAI
import tempfile
import os
from time import sleep
from pydub import AudioSegment

# API_KEY = 'Your-API-Key-here'
client = OpenAI(api_key=API_KEY)
message_history = [
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
    button.config(text='Stop Recording', command=stop_recording)
    
    # Open stream for recording and a file writer to save the data
    file_writer = sf.SoundFile(temp_file.name, mode='w', samplerate=44100, channels=1, format='WAV')
    stream = sd.InputStream(samplerate=44100, channels=1, callback=audio_callback)
    stream.start()

def stop_recording():
    global stream, mp3_file, counter
    textfield_add(f"\n{counter})\n")
    button.config(text='Processing ...', command=start_recording, state=tk.DISABLED)
    stream.stop()
    stream.close()
    file_writer.close()

    # Convert WAV to MP3
    sound = AudioSegment.from_wav(temp_file.name)
    mp3_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
    sound.export(mp3_file.name, format="mp3")

    # Transcription
    transcript = transcribe_audio()
    textfield_add(f"---- User Input Transcript ----\n")
    textfield_add(transcript)   # Insert new text
    # Summarization
    summary = summarize_text(transcript)
    textfield_add(f"\n---- Documentation Assistant ----\n")
    textfield_add(f"{summary}\n")
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
    counter += 1
    button.config(text='Start Recording', command=start_recording, state=tk.NORMAL)

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

def summarize_text(text):
    global message_history
    message_history +=  [{"role": "user", "content": text}]
    # Summarize the transcript using GPT-4 API
    completion = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=message_history
    )
    message_history += [{"role": "assistant", "content": completion.choices[0].message.content}]
    return completion.choices[0].message.content

def textfield_add(text):
    global text_field
    text_field.configure(state=tk.NORMAL)
    text_field.insert(tk.END, text)
    text_field.configure(state=tk.DISABLED)

# Initialize the main window
root = tk.Tk()
root.title("Summarizer")

# Configure the grid
root.grid_rowconfigure(0, weight=1)  # Allows text field to expand vertically
root.grid_columnconfigure(0, weight=1)  # Allows text field to expand horizontally

# Create a scrolled text field that resizes with the window
text_field = scrolledtext.ScrolledText(root, wrap=tk.WORD, font=("Consolas", 11), state=tk.NORMAL)
text_field.grid(row=0, column=0, sticky="nsew")  # Stick to all sides of the grid cell

# Create a button that sticks at the bottom
button = tk.Button(root, text='Start Recording', command=start_recording)
button.grid(row=1, column=0, sticky="ew")  # Stick to left and right, centered horizontally

root.mainloop()
