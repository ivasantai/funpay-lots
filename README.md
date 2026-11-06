<p align="center"><img src="assets/icon.png" width="128" alt="FunPay Lots"></p>

<h1 align="center">FunPay Lots</h1>

<p align="center">Десктоп-приложение для управления лотами на FunPay — Windows 11 x64 и macOS (Apple Silicon).</p>

## Возможности
- Все свои лоты по разделам, включая неактивные; поиск и фильтр по статусу.
- Создание, редактирование и удаление лотов, включение/выключение одним переключателем.
- Массовые действия: включить, выключить, удалить выбранные.
- Редактор повторяет форму FunPay, поэтому поддерживаются поля любого раздела.
- Вход по ключу аккаунта (`golden_key`), ключ хранится только на вашем компьютере.

## Скачать
[Releases](https://github.com/ivasantai/funpay-lots/releases):
`FunPayLots.exe` для Windows, `FunPayLots-macos-arm64.zip` для Mac на M1–M4.

## Документация
- [Руководство пользователя](docs/USER_GUIDE.md): установка, где взять ключ, работа с лотами, частые проблемы.
- [Устройство проекта](docs/ARCHITECTURE.md): архитектура, запросы к FunPay, формат данных.
- [Разработка и сборка](docs/DEVELOPMENT.md): запуск из исходников, сборка, релизы, что делать, если FunPay изменил сайт.
- [История изменений](CHANGELOG.md)

## Быстрый старт для разработчика
```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt   # Windows: .venv\Scripts\pip
.venv/bin/python app.py
```

> У FunPay нет официального API: приложение работает через те же запросы, что и сайт, и может
> потребовать правок, если FunPay изменит вёрстку.
