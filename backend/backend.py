import time
import random
import requests
from faker import Faker
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(title="Bitrix24 Contacts API")

# CORS middleware для работы с React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WEBHOOK_URL = "https://b24-lkgkv0.bitrix24.ru/rest/1/90qyb3sbcjem26bq/"
NUM_CONTACTS = 100
NUM_COMPANIES = 100

fake = Faker("ru_RU")

class Contact(BaseModel):
    id: Optional[int] = None
    name: str
    last_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    post: Optional[str] = None
    company_id: Optional[int] = None

class Company(BaseModel):
    id: Optional[int] = None
    title: str
    phone: Optional[str] = None
    email: Optional[str] = None
    contacts: List[Contact] = []

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
    fields = {
        "TITLE": fake.company(),
        "PHONE": [{"VALUE": fake.phone_number(), "VALUE_TYPE": "WORK"}],
        "EMAIL": [{"VALUE": fake.company_email(), "VALUE_TYPE": "WORK"}]
    }
    payload = {"fields": fields, "params": {"REGISTER_SONET_EVENT": "N"}}
    res = bx_call("crm.company.add", payload)
    return res.get("result") if res and "result" in res else None

def link_contact_to_company(contact_id, company_id):
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
            return True
        return False
    except Exception as e:
        print(f"Error linking contact {contact_id} to company {company_id}: {e}")
        return False

async def get_all_companies():
    companies = []
    start = 0
    has_more = True

    while has_more:
        data = bx_call("crm.company.list", {
            "start": start,
            "select": ["ID", "TITLE", "PHONE", "EMAIL"]
        })

        if not data or "result" not in data:
            break

        companies.extend(data["result"])
        has_more = data.get("next") is not None
        start += 50

    return companies

async def get_contacts_for_company(company_id):
    try:
        links_data = bx_call("crm.company.contact.items.get", {
            "id": company_id
        })

        contacts = []
        for link in links_data.get("result", []):
            try:
                contact_data = bx_call("crm.contact.get", {
                    "id": link["CONTACT_ID"],
                    "select": ["ID", "NAME", "LAST_NAME", "PHONE", "EMAIL", "POST", "COMPANY_ID"]
                })
                if contact_data and "result" in contact_data:
                    contact = contact_data["result"]
                    contacts.append(Contact(
                        id=contact.get("ID"),
                        name=contact.get("NAME", ""),
                        last_name=contact.get("LAST_NAME", ""),
                        phone=contact.get("PHONE", [{}])[0].get("VALUE") if contact.get("PHONE") else None,
                        email=contact.get("EMAIL", [{}])[0].get("VALUE") if contact.get("EMAIL") else None,
                        post=contact.get("POST"),
                        company_id=contact.get("COMPANY_ID")
                    ))
            except Exception as e:
                print(f"Error loading contact {link.get('CONTACT_ID')}: {e}")
        return contacts
    except Exception as e:
        print(f"Error getting contacts for company {company_id}: {e}")
        return []

@app.get("/")
async def root():
    return {"message": "Bitrix24 Contacts API"}

@app.post("/create-test-data")
async def create_test_data():
    """Создание тестовых данных в Bitrix24"""
    try:
        print("🚀 Начинаем создание тестовых данных в Битрикс 24...")
        
        # Создание контактов
        print("\n📱 Создаём контакты...")
        contact_ids = []
        for i in range(NUM_CONTACTS):
            cid = create_contact()
            if cid:
                contact_ids.append(cid)
                if (i + 1) % 5 == 0:
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
                if (i + 1) % 5 == 0:
                    print(f"Создано компаний: {len(company_ids)}/{NUM_COMPANIES}")
            time.sleep(0.05)
        print(f"✅ Создано компаний: {len(company_ids)}")

        # Распределение контактов по компаниям
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
            contacts_for_this_company = contacts_per_company
            if i < remainder:
                contacts_for_this_company += 1

            print(f"\nКомпания {i + 1}/{len(company_ids)} (ID: {company_id}): назначаем {contacts_for_this_company} контактов")

            for j in range(contacts_for_this_company):
                if contact_index < len(contact_ids):
                    contact_id = contact_ids[contact_index]
                    if link_contact_to_company(contact_id, company_id):
                        successful_links += 1
                        print(f"  ✓ Контакт {contact_id} → Компания {company_id}")
                    else:
                        print(f"  ✗ Ошибка: Контакт {contact_id} → Компания {company_id}")
                    contact_index += 1
                    time.sleep(0.05)

            print(f"  Итого для компании {company_id}: {contacts_for_this_company} контактов")

        print(f"\n✅ Готово! Распределение завершено:")
        print(f"📊 Статистика:")
        print(f"   - Контактов создано: {len(contact_ids)}")
        print(f"   - Компаний создано: {len(company_ids)}")
        print(f"   - Успешно привязано: {successful_links}")
        print(f"   - Контактов распределено: {contact_index}")

        return {
            "message": "Test data created successfully",
            "contacts_created": len(contact_ids),
            "companies_created": len(company_ids),
            "successful_links": successful_links
        }
    except Exception as e:
        print(f"❌ Ошибка создания данных: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/companies", response_model=List[Company])
async def get_companies():
    """Получение всех компаний с контактами"""
    try:
        print("📋 Загружаем все компании...")
        companies_data = await get_all_companies()
        print(f"✅ Найдено {len(companies_data)} компаний")
        
        companies = []
        for i, company in enumerate(companies_data):
            print(f"Обрабатываем компанию {i + 1}/{len(companies_data)}: {company['TITLE']}")
            contacts = await get_contacts_for_company(company["ID"])
            print(f"  - Найдено контактов: {len(contacts)}")
            
            company_obj = Company(
                id=company["ID"],
                title=company["TITLE"],
                phone=company.get("PHONE", [{}])[0].get("VALUE") if company.get("PHONE") else None,
                email=company.get("EMAIL", [{}])[0].get("VALUE") if company.get("EMAIL") else None,
                contacts=contacts
            )
            companies.append(company_obj)

        print(f"✅ Загружено {len(companies)} компаний с контактами")
        return companies
    except Exception as e:
        print(f"❌ Ошибка загрузки компаний: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
