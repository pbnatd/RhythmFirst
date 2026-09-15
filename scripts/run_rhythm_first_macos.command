#!/bin/bash

set -u

script_directory="$(cd "$(dirname "$0")" && pwd)"
project_directory="$(cd "$script_directory/.." && pwd)"
environment_python="$project_directory/.venv/bin/python"
server_pid=""

pause_on_error() {
  printf '\nRhythm First не запущен: %s\n' "$1"
  if [ -t 0 ]; then
    printf 'Нажмите Enter, чтобы закрыть окно.\n'
    read -r _
  fi
  exit 1
}

stop_server() {
  if [ -n "$server_pid" ] && kill -0 "$server_pid" 2>/dev/null; then
    kill "$server_pid" 2>/dev/null || true
    wait "$server_pid" 2>/dev/null || true
  fi
}

trap stop_server EXIT INT TERM HUP
cd "$project_directory" || pause_on_error "не удалось открыть папку проекта."

printf '\nRHYTHM FIRST · запуск\n\n'

command -v python3 >/dev/null 2>&1 || pause_on_error "не найден Python 3.11 или новее. Установите его с python.org."
python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' \
  || pause_on_error "нужен Python 3.11 или новее."
command -v ffmpeg >/dev/null 2>&1 \
  || pause_on_error "не найден FFmpeg. Установите Homebrew, затем выполните: brew install ffmpeg"
command -v ffprobe >/dev/null 2>&1 \
  || pause_on_error "не найден ffprobe. Переустановите FFmpeg командой: brew install ffmpeg"

if [ ! -x "$environment_python" ]; then
  printf 'Первый запуск: создаём окружение…\n'
  python3 -m venv "$project_directory/.venv" \
    || pause_on_error "не удалось создать окружение Python."
fi

printf 'Проверяем зависимости…\n'
"$environment_python" -m pip install --disable-pip-version-check -q -r "$project_directory/requirements.txt" \
  || pause_on_error "не удалось установить зависимости. Проверьте интернет и повторите запуск."

selected_port="$("$environment_python" - <<'PY'
import socket

with socket.socket() as candidate:
    candidate.bind(("127.0.0.1", 0))
    print(candidate.getsockname()[1])
PY
)" || pause_on_error "не удалось выбрать свободный порт."

app_url="http://127.0.0.1:$selected_port"
printf 'Запускаем приложение: %s\n' "$app_url"

PYTHONUNBUFFERED=1 RHYTHM_FIRST_PORT="$selected_port" "$environment_python" -m app.server &
server_pid=$!

server_ready=0
for _ in {1..40}; do
  if curl -fsS "$app_url/api/health" >/dev/null 2>&1; then
    server_ready=1
    break
  fi
  if ! kill -0 "$server_pid" 2>/dev/null; then
    break
  fi
  sleep 0.25
done

if [ "$server_ready" -ne 1 ]; then
  pause_on_error "сервер не ответил вовремя. Сообщение выше поможет найти причину."
fi

if [ "${RHYTHM_FIRST_LAUNCHER_SMOKE_TEST:-0}" = "1" ]; then
  printf 'Проверка launcher пройдена.\n'
  exit 0
fi

open "$app_url" || pause_on_error "не удалось открыть браузер. Откройте вручную: $app_url"
printf '\nПриложение открыто. Не закрывайте это окно, пока работаете.\n'
printf 'Для остановки нажмите Control+C.\n\n'
wait "$server_pid"
