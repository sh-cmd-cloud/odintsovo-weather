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
# КОДЫ ПОГОДЫ OPEN-METEO
# ============================================================

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

        # Берём несколько дней, а потом сами выбираем завтра.
        "forecast_days": 3,

        # Явно задаём единицы.
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
    }

    url = (
        "https://api.open-meteo.com/v1/forecast?"
        + urlencode(params)
    )

    print("========================================")
    print("OPEN-METEO")
    print("URL:")
    print(url)
    print("========================================")

    last_error = None

    for attempt in range(1, 4):

        print(f"Попытка Open-Meteo: {attempt}/3")

        try:

            request = Request(
                url,
                headers={
                    "User-Agent": "odintsovo-weather/1.0"
                }
            )

            with urlopen(request, timeout=60) as response:

                raw = response.read().decode("utf-8")

                print(
                    f"Open-Meteo HTTP: {response.status}"
                )

                data = json.loads(raw)

                print("Open-Meteo: данные получены")

                return data

        except HTTPError as error:

            body = ""

            try:
                body = error.read().decode(
                    "utf-8",
                    errors="replace"
                )
            except Exception:
                pass

            print("!!! OPEN-METEO HTTP ERROR !!!")
            print(f"URL: {url}")
            print(f"HTTP: {error.code}")
            print(f"Причина: {error.reason}")
            print(f"Ответ сервера: {body}")

            last_error = error

        except URLError as error:

            print("!!! OPEN-METEO URL ERROR !!!")
            print(f"URL: {url}")
            print(f"Ошибка: {error}")

            last_error = error

        except Exception as error:

            print("!!! OPEN-METEO UNKNOWN ERROR !!!")
            print(f"URL: {url}")
            print(f"Ошибка: {repr(error)}")

            last_error = error

        if attempt < 3:
            print("Ждём 5 секунд и пробуем ещё раз...")
            time.sleep(5)

    raise RuntimeError(
        "Open-Meteo не ответил после 3 попыток: "
        f"{last_error}"
    )


# ============================================================
# ОТПРАВКА В TELEGRAM
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

    print("========================================")
    print("TELEGRAM")
    print("Отправляем прогноз...")
    print("========================================")

    try:

        with urlopen(request, timeout=60) as response:

            raw = response.read().decode("utf-8")

            print(
                f"Telegram HTTP: {response.status}"
            )

            result = json.loads(raw)

    except HTTPError as error:

        body = ""

        try:
            body = error.read().decode(
                "utf-8",
                errors="replace"
            )
        except Exception:
            pass

        print("!!! TELEGRAM HTTP ERROR !!!")
        print(f"HTTP: {error.code}")
        print(f"Причина: {error.reason}")
        print(f"Ответ Telegram: {body}")

        raise

    except Exception as error:

        print("!!! TELEGRAM ERROR !!!")
        print(repr(error))

        raise

    if not result.get("ok"):

        raise RuntimeError(
            f"Telegram вернул ошибку: {result}"
        )

    print("Telegram: сообщение отправлено успешно")


# ============================================================
# ФОРМИРОВАНИЕ ПРОГНОЗА
# ============================================================

def main():

    print("========================================")
    print("ОДИНЦОВО — ПОГОДА")
    print("========================================")

    now = datetime.now(MOSCOW)

    print(
        "Текущее время Москва:",
        now.strftime("%d.%m.%Y %H:%M:%S")
    )

    tomorrow = now.date() + timedelta(days=1)

    print(
        "Прогнозируемая дата:",
        tomorrow.strftime("%d.%m.%Y")
    )

    # --------------------------------------------------------
    # Получаем данные
    # --------------------------------------------------------

    data = get_forecast()

    if "hourly" not in data:
        raise RuntimeError(
            "В ответе Open-Meteo нет блока hourly"
        )

    hourly = data["hourly"]

    required_fields = [
        "time",
        "temperature_2m",
        "apparent_temperature",
        "weather_code",
        "precipitation_probability",
        "precipitation",
        "wind_speed_10m",
    ]

    for field in required_fields:

        if field not in hourly:
            raise RuntimeError(
                f"В прогнозе отсутствует поле: {field}"
            )

    # --------------------------------------------------------
    # Выбираем завтра 05:00–09:00
    # --------------------------------------------------------

    rows = []

    for i, timestamp in enumerate(hourly["time"]):

        dt = datetime.fromisoformat(timestamp)

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

    # --------------------------------------------------------
    # Проверяем, нашли ли нужные часы
    # --------------------------------------------------------

    if not rows:

        print("!!! НЕ НАЙДЕН ПРОГНОЗ !!!")
        print("Доступные первые даты:")

        for timestamp in hourly["time"][:10]:
            print(timestamp)

        raise RuntimeError(
            "Не найден прогноз на завтра "
            "05:00–09:00"
        )

    print(
        f"Найдено часов прогноза: {len(rows)}"
    )

    # --------------------------------------------------------
    # Формируем сообщение
    # --------------------------------------------------------

    date_text = tomorrow.strftime("%d.%m.%Y")

    lines = [
        f"🌦️ Погода в Одинцово на завтра, {date_text}",
        "🏃 Утро 05:00–09:00",
        "",
    ]

    for row in rows:

        condition = WEATHER_CODES.get(
            row["code"],
            "неизвестные условия"
        )

        lines.append(
            f"{row['hour']:02d}:00 — "
            f"{row['temp']:+.0f}°C "
            f"(ощущается {row['feels']:+.0f}°C), "
            f"{condition}; "
            f"осадки {row['rain_probability']}%, "
            f"{row['precipitation']:.1f} мм, "
            f"ветер {row['wind']:.0f} км/ч"
        )

    # --------------------------------------------------------
    # Короткий вывод
    # --------------------------------------------------------

    avg_temp = (
        sum(row["temp"] for row in rows)
        / len(rows)
    )

    max_rain = max(
        row["rain_probability"]
        for row in rows
    )

    total_precipitation = sum(
        row["precipitation"]
        for row in rows
    )

    if max_rain >= 70:

        comment = (
            "☔ Похоже, утром зонтик будет "
            "не лишним."
        )

    elif max_rain >= 40:

        comment = (
            "🌂 Зонтик лучше держать "
            "в режиме боевой готовности."
        )

    elif avg_temp < 0:

        comment = (
            "🥶 Утро намекает: разминка "
            "перед выходом обязательна."
        )

    elif avg_temp >= 15:

        comment = (
            "😎 Утро выглядит вполне "
            "дружелюбно."
        )

    else:

        comment = (
            "🏃 В целом утро выглядит "
            "вполне беговым."
        )

    lines.extend([
        "",
        f"🌧️ Вероятность осадков: до {max_rain}%.",
        f"💧 Осадки за период: около "
        f"{total_precipitation:.1f} мм.",
        comment,
    ])

    message = "\n".join(lines)

    print("========================================")
    print("ГОТОВОЕ СООБЩЕНИЕ:")
    print("----------------------------------------")
    print(message)
    print("========================================")

    # --------------------------------------------------------
    # Отправляем
    # --------------------------------------------------------

    send_telegram(message)

    print("========================================")
    print("ГОТОВО ✅")
    print("========================================")


# ============================================================
# ЗАПУСК
# ============================================================

if __name__ == "__main__":
    main()
