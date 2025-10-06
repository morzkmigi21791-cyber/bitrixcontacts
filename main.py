import time
import random
import requests
from faker import Faker

WEBHOOK_URL = "https://b24-lkgkv0.bitrix24.ru/rest/1/90qyb3sbcjem26bq/"
NUM_CONTACTS = 100
NUM_COMPANIES = 100

fake = Faker("ru_RU")


def bx_call(method, params=None):
    url = f"{WEBHOOK_URL}{method}.json"
    try:
        resp = requests.post(url, json=params or {}, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            print(f"API Error in {method}: {data['error']}")
            return None

        return data
    except Exception as e:
        print(f"Error calling {method}: {e}")
        return None


def create_contact():
    fields = {
        "NAME": fake.first_name(),
        "LAST_NAME": fake.last_name(),
        "PHONE": [{"VALUE": fake.phone_number(), "VALUE_TYPE": "WORK"}],
        "EMAIL": [{"VALUE": fake.company_email(), "VALUE_TYPE": "WORK"}],
        "POST": fake.job()
    }
    payload = {"fields": fields, "params": {"REGISTER_SONET_EVENT": "N"}}
    res = bx_call("crm.contact.add", payload)
    return res.get("result") if res and "result" in res else None


def create_company():
    """Создание компании"""
    fields = {
        "TITLE": fake.company(),
        "PHONE": [{"VALUE": fake.phone_number(), "VALUE_TYPE": "WORK"}],
        "EMAIL": [{"VALUE": fake.company_email(), "VALUE_TYPE": "WORK"}]
    }
    payload = {"fields": fields, "params": {"REGISTER_SONET_EVENT": "N"}}
    res = bx_call("crm.company.add", payload)
    return res.get("result") if res and "result" in res else None


def link_contact_to_company(contact_id, company_id):
    """Простая привязка контакта к компании через COMPANY_ID"""
    try:
        payload = {
            "id": int(contact_id),
            "fields": {
                "COMPANY_ID": int(company_id)
            },
            "params": {"REGISTER_SONET_EVENT": "N"}
        }

        res = bx_call("crm.contact.update", payload)
        if res and "result" in res and res["result"]:
            print(f"✓ Контакт {contact_id} привязан к компании {company_id}")
            return True
        else:
            print(f"✗ Ошибка привязки контакта {contact_id} к компании {company_id}")
            print(f"   Ответ API: {res}")
            return False

    except Exception as e:
        print(f"✗ Исключение при привязке контакта {contact_id} к компании {company_id}: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Начинаем создание тестовых данных в Битрикс 24...")

    # Создание контактов
    print("\n📱 Создаём контакты...")
    contact_ids = []
    for i in range(NUM_CONTACTS):
        cid = create_contact()
        if cid:
            contact_ids.append(cid)
            if (i + 1) % 10 == 0:
                print(f"Создано контактов: {len(contact_ids)}/{NUM_CONTACTS}")
        time.sleep(0.05)
    print(f"✅ Создано контактов: {len(contact_ids)}")

    # Создание компаний
    print("\n🏢 Создаём компании...")
    company_ids = []
    for i in range(NUM_COMPANIES):
        coid = create_company()
        if coid:
            company_ids.append(coid)
            if (i + 1) % 10 == 0:
                print(f"Создано компаний: {len(company_ids)}/{NUM_COMPANIES}")
        time.sleep(0.05)
    print(f"✅ Создано компаний: {len(company_ids)}")

    print("\n🔗 Распределяем контакты по компаниям...")

    random.shuffle(contact_ids)
    random.shuffle(company_ids)

    contacts_per_company = len(contact_ids) // len(company_ids)
    remainder = len(contact_ids) % len(company_ids)

    print(f"📊 Планируемое распределение:")
    print(f"   - Контактов: {len(contact_ids)}")
    print(f"   - Компаний: {len(company_ids)}")
    print(f"   - Контактов на компанию: {contacts_per_company}")
    print(f"   - Остаток контактов: {remainder}")

    successful_links = 0
    contact_index = 0

    for i, company_id in enumerate(company_ids):
        # Определяем сколько контактов назначить этой компании
        contacts_for_this_company = contacts_per_company
        if i < remainder:  # Распределяем остаток по первым компаниям
            contacts_for_this_company += 1

        print(
            f"\nКомпания {i + 1}/{len(company_ids)} (ID: {company_id}): назначаем {contacts_for_this_company} контактов")

        # Назначаем контакты этой компании
        company_contacts = []
        for j in range(contacts_for_this_company):
            if contact_index < len(contact_ids):
                contact_id = contact_ids[contact_index]
                company_contacts.append(contact_id)
                contact_index += 1

        # Привязываем контакты к компании
        for contact_id in company_contacts:
            if link_contact_to_company(contact_id, company_id):
                successful_links += 1
                print(f"  ✓ Контакт {contact_id} → Компания {company_id}")
            else:
                print(f"  ✗ Ошибка: Контакт {contact_id} → Компания {company_id}")
            time.sleep(0.05)

        print(f"  Итого для компании {company_id}: {len(company_contacts)} контактов")

    print(f"\n✅ Готово! Распределение завершено:")
    print(f"📊 Статистика:")
    print(f"   - Контактов создано: {len(contact_ids)}")
    print(f"   - Компаний создано: {len(company_ids)}")
    print(f"   - Успешно привязано: {successful_links}")
    print(f"   - Контактов распределено: {contact_index}")