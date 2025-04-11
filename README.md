# esphome2sunspec

Dit project verbindt naar de ESPHome API van een host
en biedt de waarden aan via ModbusTCP als een generieke
Sunspec PV inverter.

Voor nu werkt dit voor een 1 fase Solis omvormer die is aangesloten
met een ESPHome chipje met deze code:

https://github.com/hn/ginlong-solis/blob/master/solis-modbus-inv.yaml

Het doel is om Victron GX deze omvormer te laten detecteren
en uit te lezen.
En uiteindelijk ook om deze via zero feedin/ dynamic power limiting
aan te sturen.

## Instalaltie

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

Maak een file (/srv/esphome2sunspec/).env met de voor jouw relevante settings:

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
