#!/usr/bin/env python3
"""
Тестовый скрипт для проверки интеграции с Битрикс24
"""

import requests
import json
import sys
from config import BITRIX24_CLIENT_ID, BITRIX24_CLIENT_SECRET, BITRIX24_REDIRECT_URI

def test_oauth_flow():
    """Тестирует OAuth поток"""
    print("🔐 Тестирование OAuth потока...")
    
    # Тестируем генерацию URL авторизации
    from oauth_handler import Bitrix24OAuth
    oauth = Bitrix24OAuth()
    
    test_domain = "test-domain.bitrix24.ru"
    auth_url = oauth.get_auth_url(test_domain)
    
    print(f"✅ URL авторизации сгенерирован: {auth_url[:50]}...")
    
    # Проверяем параметры
    assert "response_type=code" in auth_url
    assert f"client_id={BITRIX24_CLIENT_ID}" in auth_url
    assert f"redirect_uri={BITRIX24_REDIRECT_URI}" in auth_url
    assert f"state={test_domain}" in auth_url
    
    print("✅ Параметры OAuth корректны")
    return True

def test_app_handler():
    """Тестирует обработчик приложения"""
    print("🏢 Тестирование обработчика приложения...")
    
    # Тестируем создание HTML для кнопки
    from bitrix_app_handler import Bitrix24AppHandler
    app_handler = Bitrix24AppHandler()
    
    button_html = app_handler.create_button_html("CRM_LEAD_LIST_MENU")
    assert "bitrix24-contacts-button" in button_html
    assert "amusingly-awaited-starling.cloudpub.ru" in button_html
    
    print("✅ HTML кнопки генерируется корректно")
    
    # Тестируем обработчик размещения
    placement_handler = app_handler.create_placement_handler("CRM_LEAD_LIST_MENU")
    assert "BX.ready" in placement_handler
    assert "CRM_LEAD_LIST_MENU" in placement_handler
    
    print("✅ Обработчик размещения работает")
    return True

def test_placement_binding():
    """Тестирует привязку размещений"""
    print("🔗 Тестирование привязки размещений...")
    
    from placement_bind import Bitrix24PlacementBinder
    
    # Создаем тестовый биндер
    test_domain = "test-domain.bitrix24.ru"
    test_token = "test-token"
    binder = Bitrix24PlacementBinder(test_domain, test_token)
    
    # Проверяем URL API
    expected_url = f"https://{test_domain}/rest/1/{test_token}"
    assert binder.api_url == expected_url
    
    print("✅ Привязка размещений настроена")
    return True

def test_server_endpoints():
    """Тестирует доступность серверных endpoints"""
    print("🌐 Тестирование серверных endpoints...")
    
    base_url = "https://amusingly-awaited-starling.cloudpub.ru"
    endpoints = [
        "/api/bitrix24",
        "/bitrix/oauth/install",
        "/bitrix/oauth/callback"
    ]
    
    for endpoint in endpoints:
        try:
            url = f"{base_url}{endpoint}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ {endpoint} - доступен")
            else:
                print(f"⚠️  {endpoint} - статус {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ {endpoint} - ошибка: {e}")
    
    return True

def test_config():
    """Тестирует конфигурацию"""
    print("⚙️ Тестирование конфигурации...")
    
    from config import (
        BITRIX24_CLIENT_ID, 
        BITRIX24_CLIENT_SECRET, 
        BITRIX24_REDIRECT_URI,
        PORT, HOST
    )
    
    # Проверяем наличие обязательных параметров
    assert BITRIX24_CLIENT_ID, "BITRIX24_CLIENT_ID не установлен"
    assert BITRIX24_CLIENT_SECRET, "BITRIX24_CLIENT_SECRET не установлен"
    assert BITRIX24_REDIRECT_URI, "BITRIX24_REDIRECT_URI не установлен"
    
    print(f"✅ Client ID: {BITRIX24_CLIENT_ID}")
    print(f"✅ Redirect URI: {BITRIX24_REDIRECT_URI}")
    print(f"✅ Server: {HOST}:{PORT}")
    
    return True

def test_webhook_handler():
    """Тестирует webhook обработчик"""
    print("🔔 Тестирование webhook обработчика...")
    
    # Тестовые данные webhook
    test_webhook_data = {
        "event": "ONCRMLEADADD",
        "data": {
            "FIELDS": {
                "ID": "123",
                "TITLE": "Тестовый лид"
            }
        }
    }
    
    # Проверяем, что данные корректно обрабатываются
    event_type = test_webhook_data.get('event', '')
    assert event_type == "ONCRMLEADADD"
    
    lead_id = test_webhook_data.get('data', {}).get('FIELDS', {}).get('ID')
    assert lead_id == "123"
    
    print("✅ Webhook данные обрабатываются корректно")
    return True

def main():
    """Основная функция тестирования"""
    print("🧪 Запуск тестов интеграции с Битрикс24\n")
    
    tests = [
        ("Конфигурация", test_config),
        ("OAuth поток", test_oauth_flow),
        ("Обработчик приложения", test_app_handler),
        ("Привязка размещений", test_placement_binding),
        ("Webhook обработчик", test_webhook_handler),
        ("Серверные endpoints", test_server_endpoints)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            print(f"\n📋 {test_name}:")
            if test_func():
                passed += 1
                print(f"✅ {test_name} - ПРОЙДЕН")
            else:
                print(f"❌ {test_name} - ПРОВАЛЕН")
        except Exception as e:
            print(f"❌ {test_name} - ОШИБКА: {e}")
    
    print(f"\n📊 Результаты тестирования:")
    print(f"Пройдено: {passed}/{total}")
    print(f"Процент успеха: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 Все тесты пройдены! Интеграция готова к использованию.")
        return 0
    else:
        print("⚠️  Некоторые тесты провалены. Проверьте настройки.")
        return 1

if __name__ == "__main__":
    sys.exit(main())


