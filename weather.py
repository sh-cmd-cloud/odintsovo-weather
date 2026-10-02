import json
import os
import time
from datetime import datetime, timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from zoneinfo import ZoneInfo


# ============================================================
# НАСТРОЙКИ
# ============================================================

MOSCOW = ZoneInfo("Europe/Moscow")

# Одинцово
LATITUDE = 55.678
LONGITUDE = 37.277

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


# ============================================================
# ПОГОДА
# ============================================================

WEATHER_CODES = {
    0: ("☀️", "ясно"),
    1: ("🌤", "преимущественно ясно"),
    2: ("⛅", "переменная облачность"),
    3: ("☁️", "пасмурно"),

    45: ("🌫", "туман"),
    48: ("🌫", "туман с изморозью"),

    51: ("🌦", "слабая морось"),
    53: ("🌦", "морось"),
    55: ("🌧", "сильная морось"),

    56: ("🌧", "слабая ледяная морось"),
    57: ("🌧", "сильная ледяная морось"),

    61: ("🌦", "слабый дождь"),
    63: ("🌧", "дождь"),
    65: ("🌧", "сильный дождь"),

    66: ("🌧", "слабый ледяной дождь"),
    67: ("🌧", "сильный ледяной дождь"),

    71: ("🌨", "слабый снег"),
    73: ("❄️", "снег"),
    75: ("❄️", "сильный снег"),

    77: ("🌨", "снежные зёрна"),

    80: ("🌦", "слабый ливень"),
    81: ("🌧", "ливень"),
    82: ("🌧", "сильный ливень"),

    85: ("🌨", "слабый снегопад"),
    86: ("❄️", "сильный снегопад"),

    95: ("⛈", "гроза"),
    96: ("⛈", "гроза с градом"),
    99: ("⛈", "сильная гроза с градом"),
}


# ============================================================
# ПОЛУЧЕНИЕ ПРОГНОЗА
# ============================================================

def get_forecast():

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
        "forecast_days": 3,

        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
    }

    url = (
        "https://api.open-meteo.com/v1/forecast?"
        + urlencode(params)
    )

    print("Получаем прогноз Open-Meteo...")

    last_error = None

    for attempt in range(1, 4):

        try:

            request = Request(
                url,
                headers={
                    "User-Agent": "odintsovo-weather/1.0"
                }
            )

            with urlopen(request, timeout=60) as response:

                data = json.loads(
                    response.read().decode("utf-8")
                )

                print("Прогноз получен.")

                return data

        except HTTPError as error:

            print(
                f"Open-Meteo HTTP ошибка "
                f"{error.code}, попытка {attempt}/3"
            )

            last_error = error

        except URLError as error:

            print(
                f"Ошибка соединения, "
                f"попытка {attempt}/3: {error}"
            )

            last_error = error

        except Exception as error:

            print(
                f"Неизвестная ошибка, "
                f"попытка {attempt}/3: {error}"
            )

            last_error = error

        if attempt < 3:
            time.sleep(5)

    raise RuntimeError(
        f"Open-Meteo не ответил: {last_error}"
    )


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(message):

    url = (
        "https://api.telegram.org/"
        f"bot{TELEGRAM_BOT_TOKEN}/sendMessage"
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

    print("Отправляем прогноз в Telegram...")

    with urlopen(request, timeout=60) as response:

        result = json.loads(
            response.read().decode("utf-8")
        )

    if not result.get("ok"):

        raise RuntimeError(
            f"Telegram error: {result}"
        )

    print("Прогноз отправлен успешно.")


# ============================================================
# ОСНОВНАЯ ЛОГИКА
# ============================================================

def main():

    now = datetime.now(MOSCOW)

    tomorrow = (
        now.date()
        + timedelta(days=1)
    )

    print(
        "Дата прогноза:",
        tomorrow.strftime("%d.%m.%Y")
    )

    data = get_forecast()

    hourly = data["hourly"]

    rows = []

    for i, timestamp in enumerate(hourly["time"]):

        dt = datetime.fromisoformat(timestamp)

        # Только завтра 05:00–09:00
        if (
            dt.date() == tomorrow
            and 5 <= dt.hour <= 9
        ):

            rows.append({
                "hour": dt.hour,

                "temp": hourly[
                    "temperature_2m"
                ][i],

                "feels": hourly[
                    "apparent_temperature"
                ][i],

                "code": hourly[
                    "weather_code"
                ][i],

                "rain_probability": hourly[
                    "precipitation_probability"
                ][i],

                "precipitation": hourly[
                    "precipitation"
                ][i],

                "wind": hourly[
                    "wind_speed_10m"
                ][i],
            })

    if not rows:

        raise RuntimeError(
            "Не найден прогноз на завтра 05:00–09:00"
        )

    # ========================================================
    # ОБЩИЕ ПОКАЗАТЕЛИ
    # ========================================================

    min_temp = min(
        row["temp"]
        for row in rows
    )

    max_temp = max(
        row["temp"]
        for row in rows
    )

    min_feels = min(
        row["feels"]
        for row in rows
    )

    max_feels = max(
        row["feels"]
        for row in rows
    )

    max_rain = max(
        row["rain_probability"]
        for row in rows
    )

    total_precipitation = sum(
        row["precipitation"]
        for row in rows
    )

    max_wind = max(
        row["wind"]
        for row in rows
    )

    # ========================================================
    # ИКОНКА ОБЩЕЙ ПОГОДЫ
    # ========================================================

    codes = [
        row["code"]
        for row in rows
    ]

    if any(code >= 95 for code in codes):

        overall_icon = "⛈"

    elif any(
        61 <= code <= 67 or
        80 <= code <= 82
        for code in codes
    ):

        overall_icon = "🌧"

    elif any(
        71 <= code <= 77 or
        85 <= code <= 86
        for code in codes
    ):

        overall_icon = "❄️"

    elif any(
        45 <= code <= 48
        for code in codes
    ):

        overall_icon = "🌫"

    elif any(
        1 <= code <= 3
        for code in codes
    ):

        overall_icon = "⛅"

    else:

        overall_icon = "☀️"

    # ========================================================
    # ФИРМЕННЫЙ КОММЕНТАРИЙ ДЕДА-КРОССФИТЕРА
    # ========================================================

    if max_rain >= 70:

        comment = (
            "☔ Зонтик брать обязательно. "
            "Бесплатный душ от природы."
        )

    elif max_rain >= 40:

        comment = (
            "🌂 Зонтик лучше взять. "
            "Небо что-то явно замышляет."
        )

    elif max_wind >= 30:

        comment = (
            "💨 Ветер бодрый. "
            "Можно бежать, а можно сразу "
            "записать это как тренировку."
        )

    elif min_temp < 0:

        comment = (
            "🥶 Утро морозное. "
            "Разминка начинается ещё дома."
        )

    elif max_temp >= 20:

        comment = (
            "😎 Утро тёплое. "
            "Диван сегодня будет особенно убедителен."
        )

    elif max_rain == 0 and max_wind < 20:

        comment = (
            "🏃 Сухо, спокойно, без отмазок. "
            "Беговая дорожка ждёт."
        )

    else:

        comment = (
            "🏃 В целом утро вполне беговое. "
            "Отмазки не обнаружены."
        )

    # ========================================================
    # ФОРМИРУЕМ КРАСИВОЕ СООБЩЕНИЕ
    # ========================================================

    date_text = tomorrow.strftime("%d.%m")

    lines = [

        f"{overall_icon} ОДИНЦОВО • {date_text}",

        "🏃 Утро 05:00–09:00",

        "",
    ]

    # Почасовой прогноз
    for row in rows:

        icon, _ = WEATHER_CODES.get(
            row["code"],
            ("🌡", "неизвестно")
        )

        lines.append(
            f"{row['hour']:02d}:00  "
            f"{row['temp']:+.0f}° "
            f"(ощущ. {row['feels']:+.0f}°)  "
            f"{icon}  "
            f"{row['rain_probability']}%  "
            f"💨 {row['wind']:.0f}"
        )

    lines.extend([

        "",

        "🌡 "
        f"Температура: {min_temp:+.0f}…{max_temp:+.0f}°C",

        "🥶 "
        f"Ощущается: {min_feels:+.0f}…{max_feels:+.0f}°C",

        "☔ "
        f"Дождь: до {max_rain}%",

        "💧 "
        f"Осадки: {total_precipitation:.1f} мм",

        "💨 "
        f"Ветер: до {max_wind:.0f} км/ч",

        "",

        f"🥊 ДЕД-КРОССФИТЕР:",
        comment,
    ])

    message = "\n".join(lines)

    print("========================================")
    print(message)
    print("========================================")

    send_telegram(message)


# ============================================================
# ЗАПУСК
# ============================================================

if __name__ == "__main__":
    main()
