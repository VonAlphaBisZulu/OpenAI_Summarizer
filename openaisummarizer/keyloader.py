import os
import tkinter as tk
from tkinter import simpledialog
from openai import OpenAI
from cryptography.fernet import Fernet

key_file = 'openai_api.key'
key_path = os.path.join(os.path.expanduser('~'), key_file)
key_file_enc = 'openai_api.enc'
key_path_enc = os.path.join(os.path.expanduser('~'), key_file_enc)
incorrect = ""

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
        api_key = simpledialog.askstring("API Key", incorrect +"Enter your API Key:", parent=root)
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

# Main logic
if __name__ == "__main__":
    while True:
        api_key = load_or_request_api_key()
        if api_key:
            try:
                client = OpenAI(api_key=api_key)
                client.models.list()
                print("API Key loaded successfully")
                break
            except:
                os.remove(key_path_enc)
                os.remove(key_path)
                incorrect = f"The key you entered was incorrect\n"
                print("API Key invalid")
        elif api_key is None:
            print("Closing window.")
            break
        else:
            print("No API Key provided.")
