from flask import Flask, request, jsonify
import swisseph as swe
import math
import os

app = Flask(__name__)

# -------------------- EPHEMERIS PATH --------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EPHE_PATH = os.path.join(BASE_DIR, "ephe")
swe.set_ephe_path(EPHE_PATH)

# -------------------- Utility --------------------

SIGN_NAMES = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]

def wrap360(x):
    return x % 360.0

def sign_of(lon):
    return SIGN_NAMES[int(lon // 30)]

def whole_sign_house(lon, asc):
    asc_sign = int(asc // 30)
    body_sign = int(lon // 30)
    return ((body_sign - asc_sign + 12) % 12) + 1

# -------------------- Planet Calculation --------------------

PLANETS = {
    "sun": swe.SUN,
    "moon": swe.MOON,
    "mercury": swe.MERCURY,
    "venus": swe.VENUS,
    "mars": swe.MARS,
    "jupiter": swe.JUPITER,
    "saturn": swe.SATURN
}

def compute_planet_longitudes(jd_ut):
    planets = {}

    for name, p_id in PLANETS.items():
        result, flag = swe.calc_ut(jd_ut, p_id)
        lon = wrap360(result[0])

        planets[name] = {
            "longitude": lon,
            "sign": sign_of(lon),
            "degreeInSign": lon % 30
        }

    return planets

# -------------------- Ascendant & Houses --------------------

def compute_ascendant_and_houses(jd_ut, lat, lon):
    cusps, ascmc = swe.houses(jd_ut, lat, lon, b'W')

    asc_lon = wrap360(ascmc[0])

    houses = []
    for h in range(12):
        cusp_value = wrap360(cusps[h])
        houses.append({
            "house": h + 1,
            "cuspLongitude": cusp_value,
            "sign": sign_of(cusp_value)
        })

    return asc_lon, houses

# -------------------- ROOT ROUTE (fix for 404) --------------------

@app.get("/")
def home():
    return jsonify({"status": "Astrology API is running!"})

# -------------------- API ROUTE --------------------

@app.post("/chart/natal")
def chart_natal():

    data = request.json

    date = data["date"]
    time = data["time"]
    lat = float(data["lat"])
    lon = float(data["lon"])
    tz_offset = float(data["timezoneOffsetMinutes"])

    year, month, day = map(int, date.split("-"))
    hour_local = float(time.split(":")[0]) + float(time.split(":")[1]) / 60
    hour_ut = hour_local - (tz_offset / 60)

    jd_ut = swe.julday(year, month, day, hour_ut)

    planets = compute_planet_longitudes(jd_ut)
    asc_lon, houses = compute_ascendant_and_houses(jd_ut, lat, lon)

    ascendant = {
        "longitude": asc_lon,
        "sign": sign_of(asc_lon),
        "degreeInSign": asc_lon % 30
    }

    for name, p in planets.items():
        p["house"] = whole_sign_house(p["longitude"], asc_lon)

    return jsonify({
        "ascendant": ascendant,
        "houses": houses,
        "planets": planets
    })

# -------------------- PRODUCTION ENTRYPOINT --------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 4000))
    app.run(host="0.0.0.0", port=port)
