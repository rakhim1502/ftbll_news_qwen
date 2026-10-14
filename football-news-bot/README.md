# ⚽ Football News Bot (O'zbek tilidagi futbol yangiliklari Telegram boti)

Telegram foydalanuvchisi `/start` yuborganda, bot ishonchli RSS manbalardan
(BBC Sport, Sky Sports, The Guardian) bugungi eng muhim futbol yangiliklarini
yig'adi, saralaydi, o'zbek tilida qisqacha bayon qiladi va har biriga asl
maqola havolasini qo'shadi.

## Bosqichlar

| Bosqich | Holat | Tavsif |
|---|---|---|
| 1 — MVP | ✅ Tayyor | `/start`, RSS yig'ish (parallel + timeout), dedupe+saralash, oddiy qisqartirish, HTML format, xatoga chidamli |
| 2 — AI qisqartirish | ✅ Tayyor | `translator.py`da Gemini/Qwen chaqiruvi (fallback bilan); kalit bo'lmasa avtomatik AI'siz rejim |
| 3 — Testlar | ✅ Tayyor | `tests/` — 37 ta pytest testi (fetcher, ranker, translator, formatter + `/start`/`/help` smoke testlari) |
| 4 — Qat'iy futbol filtri | ✅ Tayyor | RSS stream'lari aralash sport bo'lsa ham, faqat futbolga oid sarlavha/tegslar qoladi (`news_fetcher.is_football`) |
| 5 — Entity-tozalash + demo | ✅ Tayyor | HTML entity qoldiqlari (`&#x27;`, `&amp;`) tugilish oldidan tozalanadi; `scripts/smoke_sources.py` real manbalarni tekshiradi |

## Tekshirilgan RSS manbalar (2026-10-14)

| Manba | URL | Tekshiruv |
|---|---|---|
| BBC Sport (Football) | https://feeds.bbci.co.uk/sport/football/rss.xml | HTTP 200, shu kungi pubDate |
| Sky Sports (Football) | https://www.skysports.com/rss/12040 | HTTP 200, shu kungi pubDate |
| The Guardian (Football) | https://www.theguardian.com/football/rss | HTTP 200, Atom, shu kungi pubDate |
| BBC Sport (Premier League) | https://feeds.bbci.co.uk/sport/football/premier-league/rss.xml | HTTP 200 |
| BBC Sport (Champions League) | https://feeds.bbci.co.uk/sport/football/champions-league/rss.xml | HTTP 200 |

> **Izoh:** Reuters va ESPN ochiq RSS bermaydi (tekshirildi: 403/404).
> Shuning uchun loyihada faqat yuqoridagi ishlayotgan manbalar ishlatiladi.
> Sanasi noma'lum yoki eskirgan (>NEWS_MAX_AGE_HOURS) xabarlar chiqarilmaydi.

## Loyiha tuzilishi

```
football-news-bot/
  app/
    main.py              # botni ishga tushirish (long polling)
    config.py            # .env sozlamalari + RSS manbalar ro'yxati
    handlers/
      start.py           # /start buyrug'i
    services/
      news_fetcher.py    # RSS'ni parallel yuklash va parse qilish
      news_ranker.py     # dedupe + muhimlik bo'yicha saralash
      translator.py      # o'zbekcha qisqartirish (MVP: AI'siz; 2-bosqich: Gemini/Qwen)
    utils/
      formatter.py       # Telegram HTML format + uzunlik chegarasi
  tests/
  scripts/
    setup.bat            # Windows: venv + o'rnatish + .env (bir marta)
    run.bat              # Windows: botni ishga tushirish
    test.bat             # Windows: testlarni ishga tushirish
    demo_run.py          # Telegram'siz butun zanjirni sinash
    smoke_sources.py     # RSS manbalar jonli tekshiruvi
  .env.example
  requirements.txt       # dev chegaralar (>=)
  requirements.lock.txt  # aniq versiyalar (==) — tavsiya etiladi
  README.md
```

## Windows + VS Code da ishga tushirish

### Tez usul (skriptlar bilan — tavsiya etiladi)

1. **Python 3.11+** o'rnatilgan bo'lsin (`python --version`). O'rnatishda
   **"Add Python to PATH"** belgisini albatta tanlang.
2. VS Code'da bu papkani oching: `File → Open Folder → football-news-bot`.
3. Terminalni oching (Ctrl+`) va bitta buyruq bilan hammasini qiling:
   ```powershell
   scripts\setup.bat
   ```
   Skript: `.venv` yaratadi, `requirements.lock.txt`dagi aniq versiyalarni
   o'rnatadi va `.env.example`dan `.env` nusxa oladi.
4. `.env` faylini oching va `BOT_TOKEN=` ga @BotFather'dan olingan tokenni yozing.
5. Botni ishga tushiring:
   ```powershell
   scripts\run.bat
   ```
6. Telegram'da botingizni ochib `/start` yuboring.

Qo'shimcha skriptlar:
- `scripts\test.bat` — barcha pytest testlarini ishga tushiradi;
- `scripts\demo_run.py` — Telegram'siz butun zanjirni sinaydi
  (`".venv\Scripts\python.exe" scripts\demo_run.py`).

To'xtatish: terminalda `Ctrl+C`.

### Qo'lda usul (skriptsiz)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.lock.txt   # aniq versiyalar (tavsiya)
# yoki: pip install -r requirements.txt  (dev chegaralar)
copy .env.example .env                  # so'ng BOT_TOKEN ni kiriting
python -m app.main
```

## requirements.txt vs requirements.lock.txt

| Fayl | Maqsad |
|---|---|
| `requirements.txt` | Ishlab chiqish uchun minimal versiya chegaralari (`>=`) |
| `requirements.lock.txt` | Aniq pinlangan versiyalar (`==`) — takrorlanadigan, xatosiz o'rnatish uchun |

## AI qisqartirishni yoqish (ixtiyoriy)

Bot kalitsiz ham ishlaydi (sarlavha+taqriz asosidagi naqshli qisqartirish).
Tabiiyroq o'zbekcha matn uchun `.env`ga bitta kalit qo'ying:

**Gemini (tavsiya etiladi):**
1. https://aistudio.google.com/apikey ga kiring → *Create API key* → kalitni oling.
2. `.env`:
   ```
   GEMINI_API_KEY=AQ.Ab8...sizning_kalitingiz
   GEMINI_MODEL=gemini-2.0-flash   # kerak bo'lsa boshqa mavjud model nomiga almashtiring
   ```

**Qwen (Alibaba DashScope):**
1. https://dashscope.console.aliyun.com da ro'yxatdan oting → *API-KEY* yarating.
2. `.env`:
   ```
   QWEN_API_KEY=sk-...sizning_kalitingiz
   QWEN_MODEL=qwen-plus
   ```

Ikkala kalit bo'lsa, birinchisi (Gemini) ishlatiladi. AI so'rovi xato bersa yoki
javob yaroqsiz bo'lsa, bot avtomatik ravishda AI'siz rejimga qaytadi — foydalanuvchi
bilmaydi ham. Modelga **faqat** RSS'dan olingan sarlavha/taqriz beriladi va sistem
prompt faktlarni to'qiqlashni qat'iyan taqiqlaydi.

Sinab ko'rish (butun zanjir, Telegram'siz):
```powershell
python scripts/demo_run.py
```

## Xavfsizlik

- Token va API kalitlari faqat `.env` orqali (kod ichida yo'q).
- `.env` Git'ga kirmaydi (`.gitignore`).
- Barcha matn/URL HTML escape qilinadi (parse_mode=HTML).
- Har bir tashqi so'rov 10 soniya timeout bilan; bitta manba ishlamasa ham davom etadi.
