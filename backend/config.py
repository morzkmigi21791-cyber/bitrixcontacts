import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Получаем настройки из переменных окружения
PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "0.0.0.0")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
WEBHOOK_URL = os.getenv("BITRIX24_WEBHOOK_URL", "https://b24-lkgkv0.bitrix24.ru/rest/1/90qyb3sbcjem26bq/")
NUM_CONTACTS = int(os.getenv("NUM_CONTACTS", 100))
NUM_COMPANIES = int(os.getenv("NUM_COMPANIES", 100))
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# OAuth настройки для серверного приложения
BITRIX24_CLIENT_ID = os.getenv("BITRIX24_CLIENT_ID", "local.68f61a51897255.41591672")
BITRIX24_CLIENT_SECRET = os.getenv("BITRIX24_CLIENT_SECRET", "l0xHY0JBM6Gy5dpCDeTW8IMO1l7mK7ZNGqruUL1Nnz3pbv2GMr")
BITRIX24_REDIRECT_URI = os.getenv("BITRIX24_REDIRECT_URI", "https://amusingly-awaited-starling.cloudpub.ru/bitrix/oauth/callback")
