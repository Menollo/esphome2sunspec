# esphome2sunspec

Dit project verbindt naar de ESPHome API van een host
en biedt de waarden aan via ModbusTCP als een generieke
Sunspec PV inverter.

Voor nu werkt dit voor een 1 fase Solis omvormer die is aangesloten
met een ESPHome chipje met deze code:

https://github.com/hn/ginlong-solis/blob/master/solis-modbus-inv.yaml

Ook zou de zero feed-in / dynamic power limiting implementatie
vanuit Victron GX (vanaf Venus OS 3.60) moeten werken.

## Installatie

Zet het project in /srv/esphome2sunspec:

```
cd /srv/
git clone https://github.com/Menollo/esphome2sunspec.git
```

maak een virtual environment:
```
cd /srv/esphome2sunspec/
python -m venv venv
./venv/bin/pip install -r requirements.txt
```

Maak een file .env (in /srv/esphome2sunspec/) met de voor jouw relevante settings:
(Waarbij POWER_CAPABILITY het vermogen van je omvormer is. (1000 is 1kW))

```
ESP_HOST=192.168.0.100
ESP_PORT=6053
ESP_API_PASSWORD=
ESP_API_ENCRYPTION=

MANUFACTURER=Sunspec
MODEL=ESPHome
POWER_CAPABILITY=1000
```

Kopieer de systemd files naar /etc/systemd/system
```
cp /srv/esphome2sunspec/systemd.service /etc/systemd/system/esphome2sunspec.service
cp /srv/esphome2sunspec/systemd.socket /etc/systemd/system/esphome2sunspec.socket
```

start en enable:
```
systemctl enable --now esphome2sunspec.socket
```
