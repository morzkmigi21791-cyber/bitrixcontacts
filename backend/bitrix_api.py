import requests
from config import WEBHOOK_URL

def bx_call(method, params=None):
    """Выполняет вызов к Bitrix24 API"""
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

def bx_batch_import(entity_type, data):
    """Выполняет batch import для CRM сущностей"""
    url = f"{WEBHOOK_URL}crm.item.batchImport.json"
    try:
        payload = {
            "entityTypeId": entity_type,
            "data": data
        }
        resp = requests.post(url, json=payload, timeout=60)
        
        if resp.status_code != 200:
            print(f"HTTP Error {resp.status_code}")
            return None
            
        response_data = resp.json()

        if "error" in response_data:
            print(f"Batch Import Error: {response_data['error']}")
            return None

        return response_data.get("result", {})
    except Exception as e:
        print(f"Error calling batch import: {e}")
        return None
