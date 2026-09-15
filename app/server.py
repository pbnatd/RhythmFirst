from __future__ import annotations

import json
import mimetypes
import os
import sys
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app.analysis import TempoDetectionError, detect_bpm
from app.audio import AudioProcessingError, fit_drums_to_duration, mix_tracks, prepare_drums
from app.music import STYLES, public_styles, render_accompaniment


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIR = PROJECT_ROOT / "public"
OUTPUT_DIR = PROJECT_ROOT / "runtime" / "outputs"
MAX_UPLOAD_BYTES = 40 * 1024 * 1024


def validate_options(query: dict[str, list[str]]) -> tuple[int, int, str]:
    try:
        bpm = int(query.get("bpm", ["100"])[0])
        bars = int(query.get("bars", ["8"])[0])
    except ValueError as exc:
        raise ValueError("BPM и число тактов должны быть целыми числами") from exc
    style = query.get("style", ["indie"])[0]

    if not 70 <= bpm <= 160:
        raise ValueError("BPM должен быть от 70 до 160")
    if bars not in {8, 16, 32}:
        raise ValueError("Поддерживаются результаты на 8, 16 или 32 такта")
    if style not in STYLES:
        raise ValueError("Неизвестный стиль")
    return bpm, bars, style


def extension_for(content_type: str) -> str:
    normalized = content_type.split(";", 1)[0].strip().lower()
    return {
        "audio/webm": ".webm",
        "audio/ogg": ".ogg",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/mp4": ".m4a",
        "audio/mpeg": ".mp3",
    }.get(normalized, ".audio")


class RhythmFirstHandler(BaseHTTPRequestHandler):
    server_version = "RhythmFirst/0.2"

    def _json(self, status: int, payload: dict[str, object] | list[object]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, path: Path, *, cache: bool = False) -> None:
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=3600" if cache else "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._json(HTTPStatus.OK, {"status": "ok", "product": "Rhythm First"})
            return
        if parsed.path == "/api/styles":
            self._json(HTTPStatus.OK, public_styles())
            return
        if parsed.path == "/":
            self._serve_file(PUBLIC_DIR / "index.html")
            return
        if parsed.path in {"/styles.css", "/app.js"}:
            self._serve_file(PUBLIC_DIR / parsed.path.removeprefix("/"), cache=True)
            return
        if parsed.path.startswith("/outputs/"):
            relative = Path(parsed.path.removeprefix("/outputs/"))
            candidate = (OUTPUT_DIR / relative).resolve()
            if OUTPUT_DIR.resolve() not in candidate.parents:
                self.send_error(HTTPStatus.FORBIDDEN)
                return
            self._serve_file(candidate)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path not in {"/api/analyze", "/api/render"}:
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0:
                raise ValueError("Сначала запишите или загрузите барабанную партию")
            if content_length > MAX_UPLOAD_BYTES:
                raise ValueError("Файл слишком большой: максимум 40 МБ")

            audio = self.rfile.read(content_length)
            session_id = uuid.uuid4().hex
            session_dir = OUTPUT_DIR / session_id
            session_dir.mkdir(parents=True, exist_ok=False)

            extension = extension_for(self.headers.get("Content-Type", ""))
            source_path = session_dir / f"source{extension}"
            source_path.write_bytes(audio)
            prepared_path = session_dir / "drums-original.wav"
            prepare_drums(source_path, prepared_path)

            if parsed.path == "/api/analyze":
                analysis = detect_bpm(prepared_path)
                estimated_bars = max(1, round(float(analysis["duration"]) * int(analysis["bpm"]) / 240.0))
                self._json(
                    HTTPStatus.OK,
                    {
                        **analysis,
                        "estimated_bars": estimated_bars,
                        "note": "BPM — подсказка. Проверьте темп на слух перед генерацией.",
                    },
                )
                return

            bpm, bars, style = validate_options(parse_qs(parsed.query))

            result = render_accompaniment(bpm, bars, style, session_dir)
            drums_path = session_dir / "drums.wav"
            extension_result = fit_drums_to_duration(prepared_path, drums_path, float(result["duration"]))
            mix_path = session_dir / "mix.mp3"
            mix_tracks(
                drums_path,
                Path(result["bass_path"]),
                Path(result["keys_path"]),
                mix_path,
                float(result["duration"]),
            )

            base = f"/outputs/{session_id}"
            self._json(
                HTTPStatus.CREATED,
                {
                    "id": session_id,
                    "bpm": bpm,
                    "bars": bars,
                    "duration": round(float(result["duration"]), 2),
                    "style": result["style"],
                    "style_name": result["style_name"],
                    "key": result["key"],
                    "drums_extension": extension_result,
                    "mix_url": f"{base}/mix.mp3",
                    "stems": {
                        "drums": f"{base}/drums.wav",
                        "drums_original": f"{base}/drums-original.wav",
                        "bass": f"{base}/bass.wav",
                        "keys": f"{base}/keys.wav",
                    },
                },
            )
        except TempoDetectionError as exc:
            self._json(HTTPStatus.UNPROCESSABLE_ENTITY, {"error": str(exc)})
        except ValueError as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except AudioProcessingError as exc:
            self._json(HTTPStatus.UNPROCESSABLE_ENTITY, {"error": f"Не удалось обработать аудио: {exc}"})
        except Exception as exc:  # fail loud at the API boundary
            print(f"unexpected render failure: {exc!r}", file=sys.stderr)
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Внутренняя ошибка обработки"})

    def log_message(self, format_string: str, *args: object) -> None:
        print(f"[{self.log_date_time_string()}] {format_string % args}")


def main() -> None:
    port = int(os.environ.get("RHYTHM_FIRST_PORT", "8000"))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("0.0.0.0", port), RhythmFirstHandler)
    print(f"Rhythm First is running at http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
