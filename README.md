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


## Configuratie:

Maak een file .env met de volgende settings:

```
ESP_HOST=192.168.0.100
ESP_PORT=6053
ESP_API_PASSWORD=
ESP_API_ENCRYPTION=

MANUFACTURER=Sunspec
MODEL=ESPHome
```
