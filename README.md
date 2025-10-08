# 🏢 Bitrix24 Контакты

Проект для управления компаниями и контактами в Bitrix24 с использованием React + FastAPI.

## 📁 Структура проекта

```
├── backend/                 # FastAPI backend
│   ├── backend.py          # Основной файл API
│   └── requirements.txt    # Python зависимости
├── frontend/               # React frontend
│   ├── package.json        # Node.js зависимости
│   ├── public/             # Статические файлы
│   └── src/                # Исходный код React
├── start.bat              # CMD файл для Windows
└── README.md              # Документация
```

## 🚀 Быстрый старт

### Windows (рекомендуется):
1. **Двойной клик на `start.bat`** - автоматически установит зависимости и запустит проект

### Альтернативные способы:
1. **Ручной запуск backend:**
   ```bash
   cd backend
   pip install -r requirements.txt
   python backend.py
   ```

3. **Ручной запуск frontend:**
   ```bash
   cd frontend
   npm install
   npm start
   ```

## 🌐 Доступные URL

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API документация**: http://localhost:8000/docs

## ⚙️ Настройка

Отредактируйте `WEBHOOK_URL` в файле `backend/backend.py` для подключения к вашему Bitrix24.

## 📱 Функциональность

- Создание тестовых данных (20 компаний + 20 контактов)
- Просмотр компаний с привязанными контактами
- Современный адаптивный UI
- Автоматическое открытие браузера
- Улучшенный CMD запуск для Windows
