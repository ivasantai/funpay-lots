<p align="center"><img src="assets/icon.png" width="128" alt="FunPay Lots"></p>

<h1 align="center">FunPay Lots</h1>

<p align="center">Десктоп-приложение для управления лотами на FunPay — Windows, macOS (Apple Silicon и Intel) и Linux.</p>

## Возможности
- Все свои лоты по разделам, включая неактивные; поиск и фильтр по статусу.
- Создание, редактирование и удаление лотов, включение/выключение одним переключателем.
- Массовые действия: включить, выключить, удалить выбранные.
- Редактор повторяет форму FunPay, поэтому поддерживаются поля любого раздела.
- Нейросеть (Claude): описание лота по паре фраз и автоперевод на английский.
- Финансы: балансы, история операций, вывод средств с расчётом комиссии и 2FA.
- Автообновление из GitHub Releases.
- Вход по ключу аккаунта (`golden_key`), ключ хранится только на вашем компьютере.

## Скачать
[Releases](https://github.com/ivasantai/funpay-lots/releases):
| Система | Файл |
|---|---|
| Windows 10/11 x64 | `FunPayLots.exe` |
| macOS 11+ на Apple Silicon (M1–M4) | `FunPayLots-macos-arm64.zip` |
| macOS 11+ на Intel | `FunPayLots-macos-x86_64.zip` |
| Linux x86_64 | `FunPayLots-linux-x86_64.tar.gz` |

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
