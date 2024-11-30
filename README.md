### Funkcje Bota ### 

Administrator :
 - Tworzenie osiągnieć oraz dodawanie im członkom discorda.
 - Każdy członek discorda moze dawać pochwały innym członkow discorda na serwerze pochwały które są podzielone na Kategorie.
 - Rangi - Według ilości Pochwał

   Komendy aktualnie działaja to:
Administrator: 
create_achievement  -Tworzy osiagniecie
give_achievement - Daje osiagniecie

Członek Discorda: 
- vouch - daje pochwale trzeba wpisac nazwe innego uzytkownika serwera discord + wpisac kategorie
- vouch_rank - Wyswietla Top20 ludz z najwieksza liczba pochwał
- vouch_count - Wyswietla ile uzytkownik ma pochwal i za co oraz ile pochwal mi brakuje do nastepnej rangi. 


Pełna instrukcja, jak zainstalować bota Discord na serwerze, korzystając z pliku `VendettaMirror.py`, 
który został pobrany z repozytorium GitHub. Instrukcja podzielona jest na trzy sekcje: 
tworzenie Arkusza Google Sheets, konfiguracja bota na Discordzie, oraz instalacja na serwerze VPS.

 Sekcja 1: Tworzenie Arkusza Google Sheet i przyznawanie dostępu
1. Stwórz Arkusz Google Sheet
   - Zaloguj się do Google Sheets i stwórz nowy arkusz o nazwie "Vouch Data".
   - Utwórz dwa arkusze w tym pliku: "Achievements" oraz "Achievements Definition".
   - W arkuszu "Achievements Definition" utwórz nagłówki kolumn: `name`, `description`.

2. Skonfiguruj dostęp do Google Sheets
   - Przejdź do [Google Cloud Console](https://console.developers.google.com/).
   - Utwórz nowy projekt, a następnie włącz Google Sheets API oraz Google Drive API.
   - Stwórz dane uwierzytelniające (credentials) jako klucz usługi (Service Account Key) i zapisz plik JSON na swoim komputerze.
   - Wejdź do arkusza Google Sheets i udostępnij go adresowi e-mail znalezionemu w pliku JSON (kończy się na `gserviceaccount.com`).

3. Skopiuj plik `discordbot.json`
   - Plik JSON z danymi uwierzytelniającymi umieść w katalogu, w którym będzie działał bot (np. w katalogu `VendettaMirror`).

### Sekcja 2: Konfiguracja Bota na Discordzie
1. Utwórz aplikację i bota
   - Wejdź na [Discord Developer Portal](https://discord.com/developers/applications).
   - Utwórz nową aplikację, nadaj jej nazwę i przejdź do zakładki "Bot".
   - Kliknij "Add Bot", aby dodać bota do aplikacji.

2. Pobierz token bota
   - W zakładce "Bot" znajdziesz opcję "Reset Token". Kliknij i skopiuj nowy token. Ten token będzie potrzebny do uruchomienia bota.
   - Stwórz plik `token_mirror.env` w katalogu `VendettaMirror` i dodaj do niego token w następujący sposób:
     
     DISCORD_BOT_TOKEN=twoj_token
    

3. Skonfiguruj uprawnienia bota
   - Przejdź do zakładki "OAuth2" > "URL Generator".
   - Zaznacz uprawnienia, które bot ma mieć na serwerze, takie jak: `applications.commands`, `bot`.
   - Skopiuj wygenerowany URL i użyj go, aby zaprosić bota na swój serwer Discord.

### Sekcja 3: Instalacja na serwerze VPS przez SSH
1. Przygotowanie środowiska serwera
   - Zaloguj się na serwerze za pomocą SSH:
     
     ssh user@ip_address
    
   - Zastąp `user` swoim nazwiskiem użytkownika, a `ip_address` adresem IP serwera.

2. Utwórz katalog na bota
   - Utwórz katalog, w którym znajdą się wszystkie pliki bota:
    
     mkdir VendettaMirror
     cd VendettaMirror
  

3. Zainstaluj zależności
   - Upewnij się, że Python 3 oraz `pip` są zainstalowane na serwerze. Jeśli nie, zainstaluj je:
  
     sudo apt update
     sudo apt install python3 python3-pip
   

4. Utwórz i aktywuj wirtualne środowisko
   - Utwórz wirtualne środowisko, aby odizolować zależności bota:
   
     python3 -m venv venv
  
   - Aktywuj wirtualne środowisko:
    
     source venv/bin/activate
 

5. Pobranie plików bota
   - Skopiuj plik `VendettaMirror.py` na serwer.
   - Użyj narzędzia takiego jak `scp` lub aplikacji FileZilla, aby przesłać plik `VendettaMirror.py` do katalogu `VendettaMirror` na serwerze.
   - Przesuń również pliki `discordbot.json` oraz `token_mirror.env` do katalogu `VendettaMirror`.

6. Instalacja zależności Python
   - Stwórz plik `requirements.txt` w katalogu `VendettaMirror` i dodaj do niego następujące zależności:
   
     discord.py
gspread
oauth2client
python-dotenv
tenacity
   
   - Upewnij się, że jesteś w aktywowanym wirtualnym środowisku, a następnie zainstaluj zależności:
  
     pip install -r requirements.txt


7. Uruchomienie bota
   - W aktywowanym wirtualnym środowisku uruchom bota:
 
     python VendettaMirror.py

   - Jeśli wszystko przebiegło pomyślnie, powinieneś zobaczyć informacje o połączeniu bota z Discordem oraz synchronizacji komend.

8. Konfiguracja automatycznego uruchamiania (opcjonalnie)
   - Aby bot uruchamiał się automatycznie przy starcie systemu, możesz stworzyć jednostkę systemd. Stwórz plik `vendettamirror.service` w `/etc/systemd/system/`:
   ini
     [Unit]
     Description=VendettaMirror Discord Bot
     After=network.target

     [Service]
     User=root
     WorkingDirectory=/root/VendettaMirror
     ExecStart=/root/VendettaMirror/venv/bin/python /root/VendettaMirror/VendettaMirror.py
     Restart=always

     [Install]
     WantedBy=multi-user.target
   
   - Zarejestruj i uruchom jednostkę:
     sh
     sudo systemctl daemon-reload
     sudo systemctl enable vendettamirror.service
     sudo systemctl start vendettamirror.service
  

### Gotowe!
Twój bot powinien być teraz zainstalowany i uruchomiony na serwerze. Możesz monitorować jego działanie za pomocą komendy:

sudo systemctl status vendettamirror.service

Jeśli potrzebujesz wprowadzić zmiany do kodu bota, możesz je przesłać na serwer i zrestartować usługę:

sudo systemctl restart vendettamirror.service


