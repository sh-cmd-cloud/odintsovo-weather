import json
import os
from datetime import datetime, timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


MOSCOW = ZoneInfo("Europe/Moscow")

# Координаты Одинцово
LATITUDE = 55.678
LONGITUDE = 37.277

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


WEATHER_CODES = {
    0: "ясно",
    1: "преимущественно ясно",
    2: "переменная облачность",
    3: "пасмурно",
    45: "туман",
    48: "туман с изморозью",
    51: "слабая морось",
    53: "морось",
    55: "сильная морось",
    56: "слабая ледяная морось",
    57: "сильная ледяная морось",
    61: "слабый дождь",
    63: "дождь",
    65: "сильный дождь",
    66: "слабый ледяной дождь",
    67: "сильный ледяной дождь",
    71: "слабый снег",
    73: "снег",
    75: "сильный снег",
    77: "снежные зёрна",
    80: "слабый ливень",
    81: "ливень",
    82: "сильный ливень",
    85: "слабый снегопад",
    86: "сильный снегопад",
    95: "гроза",
    96: "гроза с градом",
    99: "сильная гроза с градом",
}


def get_forecast():
    tomorrow = datetime.now(MOSCOW).date() + timedelta(days=1)

    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": (
            "temperature_2m,"
            "apparent_temperature,"
            "weather_code,"
            "precipitation_probability,"
            "precipitation,"
            "wind_speed_10m"
        ),
        "timezone": "Europe/Moscow",
        "start_date": tomorrow.isoformat(),
        "end_date": tomorrow.isoformat(),
        
    }

    url = "https://api.open-meteo.com/v1/forecast?" + urlencode(params)

    request = Request(
        url,
        headers={"User-Agent": "odintsovo-weather/1.0"},
    )

    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def send_telegram(message):
    url = (
        f"https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    payload = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
    }).encode("utf-8")

    request = Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "odintsovo-weather/1.0",
        },
        method="POST",
    )

    with urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))

    if not result.get("ok"):
        raise RuntimeError(f"Telegram error: {result}")


def main():
    data = get_forecast()

    hourly = data["hourly"]

    rows = []

    for i, timestamp in enumerate(hourly["time"]):
        dt = datetime.fromisoformat(timestamp)

        if 5 <= dt.hour <= 9:
            rows.append({
                "hour": dt.hour,
                "temp": hourly["temperature_2m"][i],
                "feels": hourly["apparent_temperature"][i],
                "code": hourly["weather_code"][i],
                "rain_probability": hourly["precipitation_probability"][i],
                "precipitation": hourly["precipitation"][i],
                "wind": hourly["wind_speed_10m"][i],
            })

    if not rows:
        raise RuntimeError("Не найден прогноз на 05:00–09:00")

    date_text = (
        datetime.now(MOSCOW).date() + timedelta(days=1)
    ).strftime("%d.%m.%Y")

    lines = [
        f"🌦️ Погода в Одинцово на завтра, {date_text}",
        "Утро 05:00–09:00",
        "",
    ]

    for row in rows:
        condition = WEATHER_CODES.get(
            row["code"],
            "неизвестные условия"
        )

        lines.append(
            f"{row['hour']:02d}:00 — "
            f"{row['temp']:+.0f}°C"
            f" (ощущается {row['feels']:+.0f}°C), "
            f"{condition}; "
            f"осадки {row['rain_probability']}%, "
            f"{row['precipitation']:.1f} мм, "
            f"ветер {row['wind']:.0f} км/ч"
        )

    avg_temp = sum(r["temp"] for r in rows) / len(rows)
    max_rain = max(r["rain_probability"] for r in rows)

    if max_rain >= 70:
        comment = "☔ Похоже, утром зонтик будет не лишним."
    elif max_rain >= 40:
        comment = "🌂 Зонтик лучше держать в режиме боевой готовности."
    elif avg_temp < 0:
        comment = "🥶 Утро намекает: разминка перед выходом обязательна."
    elif avg_temp >= 15:
        comment = "😎 Утро выглядит вполне дружелюбно."
    else:
        comment = "🏃 В целом утро выглядит вполне беговым."

    lines.extend([
        "",
        f"Коротко: вероятность осадков до {max_rain}%.",
        comment,
    ])

    send_telegram("\n".join(lines))


if __name__ == "__main__":
    main()
