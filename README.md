# Náklady řízení — web demo

Funkční kalkulátor nákladů civilního řízení v ČR. Engine převzat ze stejnojmenného modulu desktopové aplikace **OSspravce** (autor: Mgr. Pavel Tureček, OS Pardubice).

---

## Co to umí

- Tarifní odměna advokáta podle § 7 vyhlášky 177/1996 Sb.
- Sazby od 1. 1. 2025 (paušál 450 Kč/úkon) i starší (300 Kč)
- Klasické řízení / formulářové (§ 14b) / sazebník (§ 12a)
- Soudní poplatek (kalkulace)
- Cestovné + amortizace + parkovné + ztráta času
- DPH 21 % (jen pro plátce)
- Manuální / automatické procento úspěchu žalobce
- Nezastoupený účastník (§ 151 odst. 3 OSŘ)
- Generovaný text výroku k vložení do rozsudku/usnesení

---

## Pavel — jak nasadit na Streamlit Cloud

### Krok 1: Účet na GitHubu

Pokud nemáš:
1. Otevři `https://github.com`
2. Sign up (jakýkoliv e-mail funguje)
3. Potvrď e-mail

### Krok 2: Nový repository

1. V GitHubu klikni vpravo nahoře **`+`** → **New repository**
2. Repository name: `naklady-rizeni-web` (nebo cokoli)
3. **Public** (musí být — Streamlit Cloud free tier vyžaduje veřejný repo)
4. Bez `.gitignore` a bez `README` (= máme svoje)
5. **Create repository**

### Krok 3: Nahrát soubory

Nejjednodušší cestou v prohlížeči:
1. Na nově vzniklé prázdné stránce repa klikni **"uploading an existing file"**
2. Přetáhni dovnitř všechny tyto soubory:
   - `app.py`
   - `naklady_engine.py`
   - `requirements.txt`
   - `README.md` (= tento soubor)
   - **složku** `.streamlit/` se souborem `config.toml`
3. Commit message: `Initial commit`
4. **Commit changes**

> Pozor: GitHub web prohlížeč někdy nepřijme složky. Pokud nepřijme `.streamlit/config.toml`, vytvoř ho v repu ručně: **Add file** → **Create new file** → název `.streamlit/config.toml` (lomítko vytvoří složku) → vlož obsah ze souboru.

### Krok 4: Streamlit Cloud

1. Otevři `https://streamlit.io/cloud`
2. **Sign in with GitHub** (autorizuj přístup)
3. **New app** vpravo nahoře
4. Vyber svůj repo `naklady-rizeni-web`
5. Branch: `main`
6. Main file path: `app.py`
7. **Deploy!**

Za ~2 minuty máš URL typu `https://pavelturecek-naklady-rizeni-web.streamlit.app`. Tu pošli kolegům.

### Krok 5 (volitelně): Sdílet s kolegy

- URL otevřou v Safari na iPadu / v jakémkoliv prohlížeči
- Žádná instalace, žádné účty
- Mobilní layout funguje (Streamlit reaguje na šířku obrazovky)

---

## Pavel — lokální spuštění (= test než nasadíš)

```bash
pip install streamlit
streamlit run app.py
```

Otevře se prohlížeč na `http://localhost:8501`. Vyzkoušej, pak nasaď.

---

## Jak se to liší od desktop verze v OSspravce

- **Žádné spisy** — kalkulátor je samostatný, nedostává hodnoty z meta.json
- **Žádné persistování** — výpočet je v paměti, po zavření tabu pryč
- **Žádný export do Excelu** — Streamlit umí, ale pro demo zatím vynecháno
- **Žádné editovatelné sazby** — používají se DEFAULT_RATES z enginu (= aktuální vyhlášky)
- **Žádné šablony výroků/poučení** — to dělá desktop verze přes archiv

---

## Bezpečnost

- Streamlit Cloud free tier nemá autentizaci — kdokoli má URL může počítat
- Data zadaná v UI **nikam nejdou** — vše v paměti uživatele, žádné DB
- Repo na GitHubu je public — engine kód je vidět všem

Pokud chceš **privátní** verzi pro úzký kruh kolegů, je možné:
- Streamlit Cloud **Teams** plán (placené)
- Nebo deploy na vlastní VPS s reverse proxy + basic auth
- Nebo Hugging Face Spaces s passwordem

Pro demo „podívejte kolegové" stačí free tier.

---

## Tech stack

- Python 3.10+
- Streamlit ~1.30+
- Žádné jiné závislosti (pure stdlib + Streamlit)

Velikost: < 100 KB kód, < 50 MB Python prostředí. Deploy ~2 min.

---

## Pavel — pokud chceš úpravy

Engine (`naklady_engine.py`) má **stejnou výpočetní logiku** jako desktop verze. Pokud v desktop verzi opravíš sazbu / paragraf / cokoli, **musíš to opravit i tady** (= ručně zkopírovat změnu). Streamlit a desktop nejsou napojeny — žijí svým životem.

Pokud chceš jednodušší údržbu, můžeš engine vyjmout do samostatného git submodulu a oba projekty ho sdílí. Ale pro demo je separace OK.
