# Запуск Rhythm First на macOS

## Обычный запуск

1. Распакуйте архив проекта.
2. Дважды нажмите `Rhythm First.command` в корне папки.
3. При первом запуске дождитесь создания окружения и установки зависимостей.
4. Браузер откроется автоматически. Окно Terminal должно оставаться открытым во время работы.
5. Чтобы остановить приложение, нажмите Control+C или закройте окно Terminal.

Launcher каждый раз выбирает свободный локальный порт. Поэтому он не откроет старую копию приложения, которая могла остаться на фиксированном порту.

## Если macOS блокирует файл

Откройте **System Settings → Privacy & Security** и нажмите **Open Anyway** для `Rhythm First.command`, затем подтвердите запуск.

## Если не найден FFmpeg

При установленном Homebrew выполните в Terminal:

```bash
brew install ffmpeg
```

Затем снова откройте `Rhythm First.command`.

## Если не найден Python

Установите Python 3.11 или новее с `python.org`, затем повторите запуск.

## Ручной запуск для диагностики

```bash
cd /путь/к/RhythmFirst
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
RHYTHM_FIRST_PORT=8000 .venv/bin/python -m app.server
```

После этого откройте `http://127.0.0.1:8000`.
