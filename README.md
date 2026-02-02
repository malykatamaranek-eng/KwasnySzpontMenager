# KWASNY LOG MANAGER

Kompleksowy system zarządzania wieloma kontami z pełną automatyzacją, obsługą proxy, monitoringiem bezpieczeństwa i kalkulacją finansów.

## 🎯 Funkcje

### Moduł 1: System Proxy
- ✅ Jeden proxy na konto - pełna izolacja
- ✅ Obsługa SOCKS5 i HTTP/HTTPS proxy
- ✅ Automatyczne testowanie proxy
- ✅ Blacklisting uszkodzonych proxy
- ✅ Rotacja przy błędach

### Moduł 2: Automatyzacja Poczty Email
- ✅ Auto-detekcja dostawcy (wp.pl, onet.pl, o2.pl, tlen.pl, interia.pl)
- ✅ Automatyczne logowanie
- ✅ Śledzenie statusów kont email
- ✅ Wykrywanie błędów i problemów

### Moduł 3: Automatyzacja Facebooka
- ✅ Automatyczne logowanie do Facebook
- ✅ Reset hasła przez email
- ✅ Automatyczny reset przy złym haśle
- ✅ Wykrywanie checkpoint i 2FA

### Moduł 4: Zarządzanie Bezpieczeństwem
- ✅ Automatyczne wylogowywanie nieautoryzowanych sesji
- ✅ Automatyczne odrzucanie połączeń
- ✅ Dzienny skan bezpieczeństwa

### Moduł 5: Statystyki Finansowe
- ✅ Kalkulacja kosztów per konto
- ✅ Śledzenie przychodów
- ✅ Obliczanie zysków
- ✅ Statystyki globalne
- ✅ ROI i analiza rentowności

### Moduł 6: Panel Administracyjny
- ✅ GUI w PyQt6
- ✅ Lista kont z statusami
- ✅ Szczegóły każdego konta
- ✅ Kontrola operacji
- ✅ Real-time statistics

### Moduł 7: System Logowania
- ✅ Szczegółowe logi wszystkich operacji
- ✅ Tracking błędów i sukcesów
- ✅ Historia aktywności

### Moduł 8: Konfiguracja
- ✅ Pliki konfiguracyjne (INI, JSON, TXT)
- ✅ Łatwa konfiguracja proxy i kont
- ✅ Dostosowywalne parametry finansowe

### Moduł 9: Bezpieczeństwo i Anonimowość
- ✅ Randomizacja user-agent
- ✅ Losowe opóźnienia
- ✅ Izolacja procesów
- ✅ Separacja sieciowa przez proxy

### Moduł 10: Raportowanie
- ✅ Eksport danych finansowych
- ✅ Raporty aktywności
- ✅ Statystyki bezpieczeństwa

## 📋 Wymagania

- Python 3.10+
- Windows 10/11 lub Linux
- 4GB RAM minimum (16GB zalecane)
- Przeglądarka Chromium (instalowana automatycznie przez Playwright)

## 🚀 Instalacja

### 1. Klonowanie repozytorium

```bash
git clone https://github.com/malykatamaranek-eng/KwasnySzpontMenager.git
cd KwasnySzpontMenager
```

### 2. Instalacja zależności

```bash
pip install -r requirements.txt
```

### 3. Instalacja Playwright

```bash
playwright install chromium
```

### 4. Konfiguracja

#### Proxy
Skopiuj plik przykładowy i dodaj swoje proxy:
```bash
cp config/proxies.txt.example config/proxies.txt
# Edytuj config/proxies.txt i dodaj swoje proxy
```

Format proxy w pliku `config/proxies.txt`:
```
socks5://user:pass@ip:port
socks5://ip:port
http://user:pass@ip:port
https://ip:port
```

#### Konta
Skopiuj plik przykładowy i dodaj swoje konta:
```bash
cp config/accounts.txt.example config/accounts.txt
# Edytuj config/accounts.txt i dodaj swoje konta
```

Format kont w pliku `config/accounts.txt`:
```
email@wp.pl:haslo_email
email@onet.pl:haslo_email:haslo_facebook
```

#### Ustawienia Finansowe
Dostosuj koszty i przychody w pliku `config/financial_config.ini`:
```ini
[Financial]
proxy_cost_daily = 0.15
account_cost_total = 3.00
daily_revenue = 1.50
default_activity_percentage = 85.0
```

#### Ustawienia Systemowe
Dostosuj ustawienia w pliku `config/system_settings.ini`:
```ini
[System]
max_parallel_accounts = 5
headless_browser = true
default_facebook_password = NewSecurePass123!
```

## 💻 Użycie

### Uruchomienie GUI

```bash
python -m src.gui.admin_panel
```

### Uruchomienie CLI

```bash
python -m src.main
```

### Krok po kroku - pierwsze uruchomienie

1. **Uruchom GUI**:
   ```bash
   python -m src.gui.admin_panel
   ```

2. **Kliknij "Inicjalizuj System"** - system załaduje proxy i konta z plików konfiguracyjnych

3. **Wybierz konto z listy** - zobaczysz szczegóły konta w prawym panelu

4. **Kliknij "Przetwórz"** dla pojedynczego konta lub **"Start Wszystkich"** dla wszystkich kont

5. **Obserwuj logi** - system będzie logował się do email, Facebook, wykonywał skany bezpieczeństwa i aktualizował finanse

## 📊 Struktura projektu

```
KwasnySzpontMenager/
├── src/
│   ├── database.py              # Zarządzanie bazą danych SQLite
│   ├── main.py                  # Główny koordynator systemu
│   ├── modules/
│   │   ├── proxy_manager.py     # Zarządzanie proxy
│   │   ├── email_automation.py  # Automatyzacja email
│   │   ├── facebook_automation.py # Automatyzacja Facebook
│   │   ├── security_manager.py  # Zarządzanie bezpieczeństwem
│   │   └── financial_calculator.py # Kalkulacje finansowe
│   ├── gui/
│   │   └── admin_panel.py       # Panel administracyjny GUI
│   └── utils/
│       └── config_loader.py     # Ładowanie konfiguracji
├── config/
│   ├── proxies.txt              # Lista proxy (nie commitowane)
│   ├── accounts.txt             # Lista kont (nie commitowane)
│   ├── financial_config.ini    # Konfiguracja finansowa
│   ├── domains_mapping.json    # Mapowanie domen email
│   └── system_settings.ini     # Ustawienia systemowe
├── data/
│   └── kwasny.db                # Baza danych SQLite
├── logs/                        # Logi systemowe
├── requirements.txt             # Zależności Python
└── README.md                    # Ten plik
```

## 🔒 Bezpieczeństwo

- **Izolacja kont**: Każde konto działa w całkowitej izolacji z własnym proxy
- **Anonimowość**: Randomizacja user-agent, viewport, timing
- **Separacja sieciowa**: Każde konto ma unikalny adres IP przez proxy
- **Zero współdzielenia**: Brak współdzielonych zasobów między kontami
- **Anti-detection**: Losowe opóźnienia i human-like behavior

## 📈 Statystyki finansowe

System automatycznie śledzi:
- Koszty proxy
- Koszty konta (amortyzacja)
- Koszty email (amortyzacja)
- Koszty operacyjne
- Przychody dzienne
- Zyski per konto
- ROI i rentowność

### Formuła zysku

```
DZIENNY_ZYSK = (DZIENNY_PRZYCHÓD × AKTYWNOŚĆ%) - DZIENNY_KOSZT

DZIENNY_KOSZT = 
  PROXY_DZIENNIE + 
  (KOSZT_KONTA / 30) +
  (KOSZT_EMAIL / 30) + 
  KOSZT_OPERACYJNY

ŁĄCZNY_ZYSK = Σ(DZIENNY_ZYSK × DNI_AKTYWNOŚCI)
```

## 🐛 Debugowanie

### Tryb bez GUI (verbose output)
```bash
python -m src.main
```

### Przeglądarka w trybie widocznym
Edytuj `config/system_settings.ini`:
```ini
headless_browser = false
```

### Sprawdzanie logów
```bash
# Logi są zapisywane w bazie danych
# Zobacz je w GUI lub:
sqlite3 data/kwasny.db "SELECT * FROM logs ORDER BY timestamp DESC LIMIT 20"
```

## ⚠️ Uwagi

1. **Bezpieczeństwo danych**: Pliki `config/accounts.txt` i `config/proxies.txt` są w `.gitignore` - nigdy nie commituj wrażliwych danych!

2. **Proxy**: System wymaga działających proxy. Testuj proxy przed użyciem.

3. **Rate limiting**: System respektuje limity platform - nie nadużywaj.

4. **Zgodność z TOS**: Upewnij się, że używasz systemu zgodnie z regulaminami platform.

5. **Backup**: Regularnie twórz backup bazy danych `data/kwasny.db`.

## 🔧 Rozwiązywanie problemów

### Problem: "Playwright not installed"
```bash
playwright install chromium
```

### Problem: "No proxies available"
1. Sprawdź plik `config/proxies.txt`
2. Upewnij się, że proxy działają
3. Kliknij "Inicjalizuj System" w GUI

### Problem: "Account not found"
1. Sprawdź plik `config/accounts.txt`
2. Kliknij "Inicjalizuj System" w GUI
3. Sprawdź bazę danych

### Problem: Timeout podczas logowania
1. Zwiększ `operation_timeout` w `config/system_settings.ini`
2. Sprawdź połączenie z internetem
3. Zweryfikuj proxy

## 📝 Licencja

Ten projekt jest własnością prywatną. Wszelkie prawa zastrzeżone.

## 👥 Autorzy

- malykatamaranek-eng

## 🙏 Podziękowania

- Playwright - automatyzacja przeglądarki
- PyQt6 - GUI framework
- SQLite - baza danych