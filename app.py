import os
import requests
import pathlib
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, send_from_directory
from google import genai
from flask_cors import CORS
import re
from datetime import datetime, timedelta 
import feedparser  # RSS yayınlarını işlemek için
import json  # JSON dosyası oluşturmak için
from apscheduler.schedulers.background import BackgroundScheduler  # Arka plan zamanlayıcısı için

# Çevre değişkenlerini yükleme
from dotenv import load_dotenv
load_dotenv()

# ----------------------------------------------------
# DEPREM VE İÇERİK FONKSİYONLARI (Aynı Kalıyor)
# ----------------------------------------------------

def get_article_content(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception as e:
        return "Hata: Siteye erişilemedi", ""

    title = soup.title.string.strip() if soup.title else "Başlık bulunamadı"

    texts = []
    for tag in soup.find_all(['p', 'div', 'span', 'article']):
        t = tag.get_text(separator=' ', strip=True)
        if t:
            texts.append(t)
    article_text = " ".join(texts)

    if len(article_text) < 50 and soup.body:
        article_text = soup.body.get_text(separator=' ', strip=True)

    return title, article_text


def extract_info_from_text(text):
    magnitude = None
    location = None

    mag_match = re.search(r'(\d[\.,]?\d?)\s*(?:büyüklüğünde|şiddetinde|depremi|sarsıntı)', text)
    if mag_match:
        magnitude = float(mag_match.group(1).replace(",", "."))

    location_match = re.search(
        r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+)\s*(?:\'de|\'da|\'ta|\'te|yakınlarında)?\s+(?:deprem|sarsıntı)', text
    )
    if location_match:
        location = location_match.group(1)

    return magnitude, location


def get_all_afad_earthquakes():
    AFAD_URL = "https://deprem.afad.gov.tr/last-earthquakes.html"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(AFAD_URL, headers=headers, timeout=10)
        res.raise_for_status()
        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.find("table")
    except:
        return []

    if not table:
        return []

    rows = table.find_all("tr")[1:]
    records = []

    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 7:
            try:
                buyukluk = float(cols[5].text.strip())
            except:
                buyukluk = 0.0

            sehir = cols[6].text.strip()

            records.append({
                "Büyüklük": buyukluk,
                "Şehir": sehir
            })
    return records


# ----------------------------------------------------
# GÜNDEM HABERLERİ ÇEKME FONKSİYONLARI
# ----------------------------------------------------

RESMI_RSS_URL = "https://www.bbc.com/turkce/index.xml"
Haber_Sayisi = 6
HABERLER_JSON_PATH = pathlib.Path(__file__).parent / "static" / "gundem_haberler.json"


def haberleri_cek_ve_kaydet():
    """
    Belirtilen RSS URL'sinden haberleri çeker ve uygulamanın erişebileceği
    'static' klasörüne bir JSON dosyası olarak kaydeder.
    """

    HABERLER_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Haberler çekiliyor: {RESMI_RSS_URL}")

    try:
        feed = feedparser.parse(RESMI_RSS_URL)

        haberler = []
        for i, entry in enumerate(feed.entries):
            if i >= Haber_Sayisi:
                break

            haber = {
                "baslik": entry.title,
                "link": entry.link,
                "yayim_tarihi": entry.published if hasattr(entry, 'published')
                else datetime.now().strftime('%d %m %Y %H:%M'),
                "kaynak": "TRT Haber Sondakika"
            }
            haberler.append(haber)

        with open(HABERLER_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(haberler, f, ensure_ascii=False, indent=4)

        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {len(haberler)} haber başarıyla '{HABERLER_JSON_PATH}' dosyasına kaydedildi.")

    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Haber çekme/kaydetme hatası: {e}")


def check_with_afad(magnitude, location):
    depremler = get_all_afad_earthquakes()

    if not depremler:
        return None

    if not location and magnitude:
        return None

    for d in depremler:
        yer_temiz = d["Şehir"].strip().lower()

        if magnitude and abs(d["Büyüklük"] - magnitude) <= 0.3:
            if location and location.lower() in yer_temiz:
                return f"""
### ✅ KESİN DEPREM KONTROLÜ (AFAD VERİSİ)

#### 🎯 Ana İddia
{location} civarında {magnitude} büyüklüğünde deprem iddiası.

#### ✅ Güvenilirlik Hükmü
**DOĞRULANDI**

#### 📝 Kısa Açıklama
AFAD kayıtlarında **{d['Şehir']}** bölgesinde **{d['Büyüklük']}** büyüklüğünde bir deprem kaydı **BULUNMUŞTUR**.
                """

    return None


# ------- SUNUCU AYAĞA KALKARKEN EN AZ BİR KEZ HABERLERİ ÇEK --------
try:
    haberleri_cek_ve_kaydet()
except Exception as e:
    print("İlk haber çekme hatası:", e)


# ----------------------------------------------------
# 2. FLASK UYGULAMASI VE API
# ----------------------------------------------------

# --- Konfigürasyon ---
app = Flask(__name__)
CORS(app)

# Proje kök dizini (index.html ve search_page.html burada)
BASE_DIR = pathlib.Path(__file__).parent

# --- HATA AYIKLAMA KONTROLLERİ ---
env_path = pathlib.Path('.env')
print(f"DEBUG: .env dosyasının varlığı: {env_path.exists()}")

API_KEY = os.getenv("GEMINI_API_KEY")
print(f"DEBUG: API_KEY değeri okundu: {'VAR' if API_KEY else 'YOK'}")
# --- HATA AYIKLAMA KONTROLLERİ SONU ---

if not API_KEY:
    raise ValueError("GEMINI_API_KEY çevre değişkeni ayarlanmadı. Lütfen .env dosyanızı kontrol edin.")

client = genai.Client(api_key=API_KEY)
model = 'gemini-2.5-flash'

# GÜVENİLİR KAYNAKLAR LİSTESİ
GÜVENİLİR_SİTELER = [
    "aa.com.tr (Anadolu Ajansı)",
    "resmigazete.gov.tr (Resmi Gazete)",
    "valilik siteleri",
    "meb.gov.tr (Milli Eğitim Bakanlığı)",
    "icisleri.gov.tr (İçişleri Bakanlığı)",
    "afad.gov.tr",
    "koeri.boun.edu.tr (Kandilli Rasathanesi)"
]

# ---------- ÖN YÜZ ROUTE'LARI ----------

@app.route('/')
def index():
    return send_from_directory(str(BASE_DIR), 'index.html')


@app.route('/search')
def search_page():
    return send_from_directory(str(BASE_DIR), 'search_page.html')


# ---------- STATİK DOSYA ROUTE'LARI (CSS / IMG / STATIC) ----------

@app.route('/css/<path:filename>')
def css_files(filename):
    return send_from_directory('css', filename)


@app.route('/img/<path:filename>')
def img_files(filename):
    # static/img klasöründeki dosyaları /img/... ile servis et
    return send_from_directory('static/img', filename)


@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)


# ---------- API ROUTE'LARI ----------

@app.route('/api/dogrula', methods=['POST'])
def dogrulama_islemi():
    simdiki_tarih_metni = "27 Ekim 2025"

    data = request.json
    haber_linki = data.get('link')

    if not haber_linki:
        return jsonify({"hata": "Lütfen bir haber linki girin."}), 400

    title, haber_metni = get_article_content(haber_linki)

    if title.startswith("Hata:"):
        return jsonify({"hata": title}), 500

    mag, loc = extract_info_from_text(haber_metni)

    afad_sonuc = None
    if mag or loc:
        afad_sonuc = check_with_afad(mag, loc)

        if afad_sonuc:
            return jsonify({
                "basari": True,
                "ozet_ve_dogrulama": afad_sonuc,
                "orijinal_link": haber_linki,
                "kaynak": "AFAD"
            })

    if not haber_metni:
        return jsonify({"hata": "Haber içeriği çekilemedi veya site izin vermiyor."}), 500

    anahtar_kelimeler = ", ".join(
        re.findall(r'[A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s[A-ZÇĞİÖŞÜ][a-zçğıöşü]+){0,2}', haber_metni)[:5]
    )
    if not anahtar_kelimeler:
        anahtar_kelimeler = title.split()[:5]

    guvenilir_str = ", ".join(GÜVENİLİR_SİTELER)

    prompt = f"""
    aşağıdaki haber metnini ve iddialarını analiz et.

    **ÇOK ÖNEMLİ ZAMAN BİLGİSİ:** Şu anki teyit tarihi: {simdiki_tarih_metni}. (Bu bilgiyi çıktıya ASLA yazma.)

    **YASAK ve ZORUNLULUKLAR:**
    * **TARİH YASAĞI:** Çıktının hiçbir yerinde "şu anki teyit tarihi" veya "{simdiki_tarih_metni}" ifadesini kullanma.
    * **YASAK:** Haberin tarihi güncel teyit tarihiyle aynı veya öncesinde olsa bile "henüz teyit edilemez" hükmü verme. YALNIZCA olayın gerçekleşip gerçekleşmediğini teyit et.
    * **ÖNCELİK:** Haberin içeriğine göre (Trafik kazası ise İçişleri/Valilik, Eğitim ise MEB, Genel ise AA) en uygun güvenilir kaynağı ara.

    **Hüküm İçin Adımlar:**
    1. Haberdeki ana iddiayı ve gerçekleştiği iddia edilen tarihi 1-2 cümleyle çıkar.
    2. Yukarıdaki YÖNERGEYE uyarak teyitini ara. Özellikle şu kaynakları kullan: {guvenilir_str}.
    3. Tüm analizini, net bir **GÜVENİLİLİK HÜKMÜ** ile sonlandır.

    **Çıktı Formatı:**
    Çıktın SADECE aşağıdaki gibi kopyalanabilir ve kısa olmalıdır. Markdown formatını koru.

    ### 🚨 HIZLI DOĞRULUK KONTROLÜ (GEMINI)

    #### 🎯 Ana İddia
    [Habere ait 1 cümlelik özet ve tarihi.]

    #### ✅ Güvenilirlik Hükmü
    **[BURAYA SADECE ŞUNLARDAN BİRİNİ YAZ: DOĞRULANDI / YANLIŞ / HENÜZ DOĞRULANAMADI]**

    #### 📝 Kısa Açıklama
    [Hükmünü (neden doğru veya yanlış olduğunu) destekleyen 2-3 cümlelik çok kısa bir açıklama. Açıklamada teyit tarihi bilgisini KULLANMA. Sadece teyit edildiği kaynağı (DHA, Valilik vb.) belirt.]

    Haber Metni:
    ---
    {haber_metni}
    ---
    """

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config={"temperature": 0.0}
        )

        return jsonify({
            "basari": True,
            "ozet_ve_dogrulama": response.text,
            "orijinal_link": haber_linki,
            "kaynak": "GEMINI"
        })

    except Exception as e:
        return jsonify({"hata": f"Gemini API hatası: {e}"}), 500


# ----------------------------------------------------
# GÜNDEM HABERLERİ API UÇ NOKTASI
# ----------------------------------------------------

@app.route('/api/gundem', methods=['GET'])
def gundem_haberleri():
    """
    Önceden çekilmiş ve JSON dosyasına kaydedilmiş haberleri döndürür.
    """
    try:
        with open(HABERLER_JSON_PATH, 'r', encoding='utf-8') as f:
            haberler = json.load(f)
        return jsonify(haberler)
    except FileNotFoundError:
        return jsonify({"hata": "Haber verisi bulunamadı. Lütfen app.py'nin haber çekme fonksiyonunun çalıştığından emin olun."}), 404
    except Exception as e:
        return jsonify({"hata": f"Haber verisi okunurken hata: {e}"}), 500


# ----------------------------------------------------
# ZAMANLAYICI
# ----------------------------------------------------

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(haberleri_cek_ve_kaydet, 'interval', minutes=30)
    scheduler.start()
    print("DEBUG: Arka plan haber çekme zamanlayıcısı başlatıldı (30 dakikada bir).")


if __name__ == '__main__':
    # Lokal çalıştırırken
    haberleri_cek_ve_kaydet()
    start_scheduler()
    app.run(debug=True, port=5000, use_reloader=False)
