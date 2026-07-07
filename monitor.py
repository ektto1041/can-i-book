#!/usr/bin/env python3
import argparse
import os
import smtplib
import ssl
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from typing import List

import certifi
import requests
from bs4 import BeautifulSoup, Tag


DEFAULT_URL = "https://hub.hotelstory.com/MTAwMDMwMw/calendar?v_caldate=2026-10"
DEFAULT_TARGET_DATE = "2026-10-03"
DEFAULT_INTERVAL_SECONDS = 60
DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)


@dataclass
class RoomAvailability:
    name: str
    price: str


@dataclass
class Config:
    url: str
    target_date: str
    interval_seconds: int
    timeout_seconds: int
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    from_email: str
    to_email: str
    user_agent: str


def load_dotenv(path: str = ".env") -> None:
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


def require_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or value == "":
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def load_config() -> Config:
    load_dotenv()
    return Config(
        url=os.getenv("TARGET_URL", DEFAULT_URL),
        target_date=os.getenv("TARGET_DATE", DEFAULT_TARGET_DATE),
        interval_seconds=int(os.getenv("CHECK_INTERVAL_SECONDS", DEFAULT_INTERVAL_SECONDS)),
        timeout_seconds=int(os.getenv("HTTP_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)),
        smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
        smtp_port=int(os.getenv("SMTP_PORT", "465")),
        smtp_username=require_env("SMTP_USERNAME"),
        smtp_password=require_env("SMTP_PASSWORD"),
        from_email=require_env("FROM_EMAIL"),
        to_email=require_env("TO_EMAIL"),
        user_agent=os.getenv("USER_AGENT", DEFAULT_USER_AGENT),
    )


def fetch_calendar_html(config: Config) -> str:
    response = requests.get(
        config.url,
        headers={"User-Agent": config.user_agent},
        timeout=config.timeout_seconds,
    )
    response.raise_for_status()
    return response.text


def find_date_box(soup: BeautifulSoup, target_day: int) -> Tag:
    for box in soup.select("td > div.box"):
        td = box.parent
        if not isinstance(td, Tag):
            continue

        if "other" in (td.get("class") or []):
            continue

        day_span = box.select_one("div.day span")
        if day_span is None:
            continue

        day_text = day_span.get_text(strip=True)
        if day_text.isdigit() and int(day_text) == target_day:
            return box

    raise ValueError(f"Could not find calendar cell for day {target_day}")


def parse_available_rooms(html: str, target_date: str) -> List[RoomAvailability]:
    target = datetime.strptime(target_date, "%Y-%m-%d")
    soup = BeautifulSoup(html, "html.parser")
    box = find_date_box(soup, target.day)

    rooms: List[RoomAvailability] = []
    for product in box.select("div.info div.product"):
        classes = product.get("class") or []
        if "block_blank" in classes:
            continue

        name_node = product.select_one("div.name")
        cost_node = product.select_one("div.cost")
        if name_node is None:
            continue

        name = name_node.get_text(" ", strip=True)
        price = cost_node.get_text(" ", strip=True) if cost_node else ""
        rooms.append(RoomAvailability(name=name, price=price))

    return rooms


def build_email_message(config: Config, rooms: List[RoomAvailability]) -> EmailMessage:
    subject = f"[예약 감지] {config.target_date} 빈 방 {len(rooms)}개 발견"
    lines = [
        f"{config.target_date} 체크인 기준 빈 방이 감지되었습니다.",
        "",
        f"확인 URL: {config.url}",
        "",
        "가능 객실:",
    ]
    for room in rooms:
        lines.append(f"- {room.name} / {room.price}")

    lines.extend(
        [
            "",
            f"감지 시각: {datetime.now().isoformat(timespec='seconds')}",
        ]
    )

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config.from_email
    message["To"] = config.to_email
    message.set_content("\n".join(lines))
    return message


def send_email(config: Config, message: EmailMessage) -> None:
    context = ssl.create_default_context(cafile=certifi.where())
    with smtplib.SMTP_SSL(config.smtp_host, config.smtp_port, context=context) as server:
        server.login(config.smtp_username, config.smtp_password)
        server.send_message(message)


def log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def run_once(config: Config) -> None:
    html = fetch_calendar_html(config)
    rooms = parse_available_rooms(html, config.target_date)

    if not rooms:
        log(f"{config.target_date}: 빈 방 없음")
        return

    log(f"{config.target_date}: 빈 방 {len(rooms)}개 발견, 메일 발송")
    message = build_email_message(config, rooms)
    send_email(config, message)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Poll the hotel calendar and send an email when rooms open up."
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single check and exit. Recommended for Cloud Run Jobs.",
    )
    return parser.parse_args()


def run_forever(config: Config) -> None:
    log(
        "monitor start "
        f"(target_date={config.target_date}, interval={config.interval_seconds}s)"
    )
    while True:
        try:
            run_once(config)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            log(f"error: {exc}")

        time.sleep(config.interval_seconds)


def main() -> int:
    args = parse_args()

    try:
        config = load_config()
    except Exception as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    try:
        if args.once:
            run_once(config)
            return 0
        run_forever(config)
    except KeyboardInterrupt:
        log("monitor stopped")
        return 0
    except Exception as exc:
        log(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
