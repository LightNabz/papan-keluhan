import os
import requests
from dotenv import load_dotenv

load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def send_discord_report(content: str):
    data = {
        "content": content
    }
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=data)
        if response.status_code == 204:
            print("Laporan berhasil dikirim ke Discord!")
        else:
            print(f"Gagal kirim laporan. Status: {response.status_code}, Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")