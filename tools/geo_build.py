"""یک‌بار: مرز ایران، مرز استان‌ها و نام فارسی شهرها و روستاها (از Natural Earth و GeoNames، هر دو آزاد)
را در assets/geo/iran.json می‌گذارد تا سیما برای خبرهای بی‌عکس، نقشه‌ی جای رویداد را بسازد.
اجرا (روی رایانه‌های GitHub): python3 tools/geo_build.py"""
import io, json, os, re, urllib.request, zipfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "assets", "geo", "iran.json")
NE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
UA = {"User-Agent": "IranaMedia/1.0"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
        return r.read()


def rings(geom, step):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    out = []
    for p in polys:
        r = p[0]
        if len(r) < 12:
            continue
        out.append([[round(x, 3), round(y, 3)] for x, y in r[::step]])
    return out


c = json.loads(get(NE + "ne_10m_admin_0_countries.geojson"))
iran = next(f for f in c["features"] if f["properties"].get("ADM0_A3") == "IRN")
outline = rings(iran["geometry"], 3)
nb = []                                               # همسایگان (کم‌رنگ، برای جای‌یابی)
for f in c["features"]:
    if f["properties"].get("ADM0_A3") in ("IRQ", "TUR", "ARM", "AZE", "TKM", "AFG", "PAK", "KWT", "SAU", "ARE", "OMN", "QAT", "BHR", "GEO", "SYR"):
        nb += rings(f["geometry"], 6)
a1 = json.loads(get(NE + "ne_10m_admin_1_states_provinces.geojson"))
prov, prov_names = [], {}
for f in a1["features"]:
    pr = f["properties"]
    if pr.get("adm0_a3") != "IRN":
        continue
    prov += rings(f["geometry"], 4)
    fa = (pr.get("name_fa") or "").strip()
    if fa and pr.get("longitude") is not None:
        prov_names[re.sub(r"^استان\s+", "", fa)] = [round(pr["longitude"], 3), round(pr["latitude"], 3), 0]

z = zipfile.ZipFile(io.BytesIO(get("https://download.geonames.org/export/dump/IR.zip")))
places = {}
AR = re.compile(r"^[؀-ۿ‌ ]+$")
for line in z.read("IR.txt").decode("utf-8").splitlines():
    p = line.split("\t")
    if len(p) < 15 or p[6] != "P":
        continue
    pop = int(p[14] or 0)
    if pop < 2000 and p[7] not in ("PPLA", "PPLA2", "PPLC"):
        continue
    lon, lat = float(p[5]), float(p[4])
    for n in set(p[3].split(",")):
        n = n.strip().replace("ي", "ی").replace("ك", "ک")
        if not AR.match(n) or len(n) < 3:
            continue
        if n not in places or places[n][2] < pop:
            places[n] = [round(lon, 3), round(lat, 3), pop]
for n, v in prov_names.items():                       # نام استان‌ها (اگر هم‌نام شهری نیست)
    places.setdefault(n, v)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump({"source": "Natural Earth (public domain), GeoNames (CC BY 4.0)",
           "outline": outline, "provinces": prov, "neighbours": nb, "places": places},
          open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("مرز:", sum(map(len, outline)), "نقطه؛ استان‌ها:", len(prov), "؛ نام‌ها:", len(places), "؛ اندازه:", os.path.getsize(OUT) // 1024, "KB")
for k in ("آبدانان", "تهران", "زاهدان", "مهاباد", "سنندج", "ایذه", "جوانرود", "ایلام"):
    print(k, places.get(k))
