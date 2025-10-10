import random
import requests
from faker import Faker
from bitrix_api import bx_batch_import, bx_call
from config import WEBHOOK_URL

fake = Faker("ru_RU")

def create_companies_batch_import(count):
    """Создает компании через batch import (до 20 за раз)"""
    data = []
    for i in range(count):
        item = {
            "TITLE": fake.company(),
            "PHONE": [{"VALUE": fake.phone_number(), "VALUE_TYPE": "WORK"}],
            "EMAIL": [{"VALUE": fake.company_email(), "VALUE_TYPE": "WORK"}]
        }
        data.append(item)
    
    result = bx_batch_import(4, data)  # 4 = Company entity type
    if result and "items" in result:
        return [item["item"]["id"] for item in result["items"] if "item" in item and "id" in item["item"]]
    return []

def create_contacts_batch_import(count):
    """Создает контакты через batch import (до 20 за раз)"""
    data = []
    for i in range(count):
        item = {
            "NAME": fake.first_name(),
            "LAST_NAME": fake.last_name(),
            "PHONE": [{"VALUE": fake.phone_number(), "VALUE_TYPE": "WORK"}],
            "EMAIL": [{"VALUE": fake.company_email(), "VALUE_TYPE": "WORK"}],
            "POST": fake.job()
        }
        data.append(item)
    
    result = bx_batch_import(3, data)  # 3 = Contact entity type
    if result and "items" in result:
        return [item["item"]["id"] for item in result["items"] if "item" in item and "id" in item["item"]]
    return []

def create_one_to_one_links(contact_ids, company_ids):
    """
    Создает случайные пары контакт-компания (1 к 1).
    Каждая компания получает ровно один контакт.
    """
    # Перемешиваем списки для случайности
    random.shuffle(contact_ids)
    random.shuffle(company_ids)
    
    # Создаем пары 1 к 1
    links = []
    min_count = min(len(contact_ids), len(company_ids))
    
    for i in range(min_count):
        links.append((contact_ids[i], company_ids[i]))
    
    return links

def update_contacts_company_batch(contact_company_pairs):
    """
    Привязывает контакты к компаниям (1 контакт → 1 компания) через batch API.
    Использует crm.contact.update, обновляя поле COMPANY_ID.
    """
    commands = {}
    for i, (contact_id, company_id) in enumerate(contact_company_pairs):
        commands[f"update_{i}"] = f"crm.contact.update?id={int(contact_id)}&fields[COMPANY_ID]={int(company_id)}&params[REGISTER_SONET_EVENT]=N"

    url = f"{WEBHOOK_URL}batch.json"
    try:
        payload = {"halt": 0, "cmd": commands}
        resp = requests.post(url, json=payload, timeout=60)

        if resp.status_code != 200:
            print(f"Batch update HTTP Error {resp.status_code}: {resp.text}")
            return []

        response_data = resp.json()

        if "error" in response_data:
            print(f"Batch update Error: {response_data['error']}")
            return []

        results = response_data.get("result", {}).get("result", {})
        successful = [k for k, v in results.items() if v is True]
        return successful

    except Exception as e:
        print(f"Error calling batch update: {e}")
        return []
