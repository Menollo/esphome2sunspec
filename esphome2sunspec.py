import os
import struct
import logging
import asyncio
import modbus_tk
import modbus_tk.defines as cst
from modbus_tk import modbus_tcp
from modbus_tk.modbus import Databank
import modbus_tk.hooks
from aioesphomeapi import APIClient
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.INFO)

def encode_string(s, length):
    s = s.encode('ascii')
    pad = b'\0' * (2 * length - len(s))
    fmt = '>{}H'.format(length)
    unpacked = struct.unpack(fmt, s + pad)
    return list(unpacked)

class SunspecServer(object):
    def __init__(self, address="0.0.0.0", port=502, slave_id=126):
        self.address = address
        self.port = port
        self.slave_id = slave_id
        self.server = None
        self.databank = Databank()
        self._setup_slaves_and_registers()
        self.esphome_services = {}
        self.esphome_client = None
        self.esphome_connected = False
        self.esphome_reconnect_task = None
        self.esphome_limit_entity_id = None
        self.loop = asyncio.get_event_loop() # Haal de huidige event loop op

    def _setup_slaves_and_registers(self):
        # Voeg de slave toe aan de databank met de slave ID
        self.databank.add_slave(self.slave_id)
        slave = self.databank.get_slave(self.slave_id)

        # Definieer een block voor de holding registers
        slave.add_block('hr', cst.HOLDING_REGISTERS, 40000, 40176 - 40000 + 100) # Vergroot het block om ESPHome registers te omvatten

        def set_regs(address, values):
            slave.set_values('hr', address, values)


        # Model 1 (mandatory)
        set_regs(40000, [0x5375, 0x6e53])  # SunSpec marker
        set_regs(40002, [1]) # Sunspec model id
        set_regs(40003, [66]) # length
        set_regs(40004, encode_string(os.getenv('MANUFACTURER', 'Sunspec'), 16)) # Manufacturer
        set_regs(40020, encode_string(os.getenv('MODEL', 'ESPHome'), 16)) # Model
        set_regs(40036, encode_string('', 8)) # Options
        set_regs(40044, encode_string('0.0.1', 8)) # Version
        set_regs(40052, encode_string('1802000000000000', 16)) # Serial
        set_regs(40068, [self.slave_id])
        set_regs(40069, [0xFFFF])

        # Model 101 (Single phase inverter) - Basiswaarden
        set_regs(40070, [101]) # SUnspec model id
        set_regs(40071, [50]) # length
        set_regs(40076, [0xFFFF]) # Scale factor current
        set_regs(40083, [0xFFFF]) # Scale factor voltage
        set_regs(40085, [0]) # Scale factor power
        set_regs(40087, [0xFFFE]) # Scale factor frequency
        set_regs(40096, [0]) # Scale factor energy
        set_regs(40108, [1]) # State = Off (1) / State = Running (4)

        # Model 120, Nameplate ratings - Basiswaarden
        power_capability = int(os.getenv('POWER_CAPABILITY'))
        set_regs(40122, [120]) # Sunspec model id
        set_regs(40123, [26]) # length
        set_regs(40124, [4]) # DER_TYP = PV
        set_regs(40125, [power_capability])
        set_regs(40126, [0]) # Scale factor
        set_regs(40127, [power_capability >> 16, power_capability & 0xFFFF]) # AC Rated Apparent Power (VARtg) - neemt 2 registers in

        # Model 123, immediate controls - Basiswaarden
        set_regs(40150, [123]) # Sunspec model id
        set_regs(40151, [24]) # length
        set_regs(40155, [0]) # WMaxLimPct
        set_regs(40157, [0]) # WMaxLimPct_RvrtTms
        set_regs(40159, [0]) # WMaxLim_Ena
        set_regs(40173, [0xFFFE]) # WMaxLimPct_SF (1 = 0.01%)

        # De ESPHome gerelateerde registers worden dynamisch bijgewerkt

        # Het einde
        set_regs(40176, [0xFFFF])

    def update_modbus_register(self, address, value):
        slave = self.databank.get_slave(self.slave_id)
        slave.set_values('hr', address, [value,])

    async def send_esphome_command(self, entity_id, value):
        try:
            self.esphome_client.number_command(entity_id, value)
            log.debug(f"ESPHome command sent to {entity_id}: {value}")
        except Exception as e:
            log.error(f"Fout bij sturen ESPHome commando naar {entity_id}: {e}")

    async def _connect_esphome_internal(self):
        self.esphome_client = APIClient(os.getenv('ESP_HOST'), os.getenv('ESP_PORT'), os.getenv('ESP_API_PASSWORD'), noise_psk=os.getenv('ESP_API_ENCRYPTION'))
        try:
            await self.esphome_client.connect(login=True)
            log.info("Verbonden met ESPHome")
            entities = await self.esphome_client.list_entities_services()
            self.esphome_limit_entity_id = [e.key for e in entities[0] if e.object_id == 'limit_output_power'][0]
            self.esphome_services = {entity.key: entity.object_id for entity in entities[0] if hasattr(entity, 'name')}
            self.esphome_client.subscribe_states(self.esphome_state_update)
            self.esphome_connected = True
            self.update_modbus_register(40108, 4) # State = Running
        except Exception as e:
            log.error(f"Fout bij verbinden met ESPHome: {e}")
            self.esphome_connected = False
            self.update_modbus_register(40108, 1) # State = Off

    async def manage_esphome_connection(self):
        while True:
            if not self.esphome_connected:
                log.info("Poging tot verbinden met ESPHome...")
                await self._connect_esphome_internal()
            await asyncio.sleep(10) # Controleer de verbinding elke 10 seconden

    def esphome_state_update(self, state):
        service_name = self.esphome_services.get(state.key)

        if service_name == 'ac_voltage':
            value = int(state.state * 10)
            self.update_modbus_register(40080, value)
        elif service_name == 'ac_current':
            value = int(state.state * 10)
            self.update_modbus_register(40072, value)
        elif service_name == 'active_power':
            value = int(state.state)
            self.update_modbus_register(40084, value)
        elif service_name == 'grid_frequency':
            value = int(state.state * 100)
            self.update_modbus_register(40086, value)
        elif service_name == 'total_energy':
            value =  struct.pack('>I', int(state.state * 1000))
            high_word, low_word = struct.unpack('>HH', value)
            self.update_modbus_register(40094, high_word)
            self.update_modbus_register(40095, low_word)
        elif service_name == 'limit_output_power':
            value = int(state.state * 100)
            if value > 10000:
                self.update_modbus_register(40159, 0)
                self.update_modbus_register(40155, 0)
            else:
                self.update_modbus_register(40159, 1)
                self.update_modbus_register(40155, value)

    def modbus_write_hook(self, args):
        server, request = args

        query = server._make_query()
        slave_id, request_pdu = query.parse_request(request)
        function_code = request_pdu[0]

        if slave_id == self.slave_id and function_code in [cst.WRITE_SINGLE_REGISTER, cst.WRITE_MULTIPLE_REGISTERS]:

            slave = self.databank.get_slave(self.slave_id)
            limit_pct = slave.get_values('hr', 40155)[0]
            limit_ena = slave.get_values('hr', 40159)[0]
            limit_change = False

            if function_code == cst.WRITE_SINGLE_REGISTER:
                (address, value) = struct.unpack(">HH", request_pdu[1:5])
                if address == 40155:
                    limit_pct = value
                    limit_change = True
                elif address == 40159:
                    limit_ena = value
                    limit_change = True
            elif function_code == cst.WRITE_MULTIPLE_REGISTERS:
                (starting_address, quantity_of_x, byte_count) = struct.unpack(">HHB", request_pdu[1:6])

                for i in range(quantity_of_x):
                    address = starting_address + i
                    if address == 40155:
                        limit_pct = struct.unpack(">H", request_pdu[6+2*i:8+2*i])[0]
                        limit_change = True
                    elif address == 40159:
                        limit_ena = struct.unpack(">H", request_pdu[6+2*i:8+2*i])[0]
                        limit_change = True


            if limit_change and self.esphome_connected:
                log.debug(f"Wijziging aan limiet: percentage: {limit_pct}, enabled: {limit_ena}")
                limit = (limit_pct / 100.0)
                if limit_ena == 0 or limit_pct >= 10000:
                    limit = 110.0

                log.info(f"Start taak om percentage van: {limit} % naar ESPHome te sturen")
                # Gebruik loop.create_task om de coroutine in de asyncio event loop te plannen
                self.loop.create_task(self.send_esphome_command(self.esphome_limit_entity_id, limit))


    def start_modbus_server(self):
        log.info(f"Starting Modbus TCP server on {self.address}:{self.port}, Slave ID: {self.slave_id}")
        try:
            self.server = modbus_tcp.TcpServer(databank=self.databank, address=self.address, port=self.port)
            modbus_tk.hooks.install_hook("modbus.Server.before_handle_request", self.modbus_write_hook)
            self.server.start()
        except Exception as e:
            log.error(f"Fout bij starten Modbus server: {e}")

async def main():
    sunspec_server = SunspecServer()
    await sunspec_server._connect_esphome_internal()
    sunspec_server.start_modbus_server()
    sunspec_server.esphome_reconnect_task = asyncio.create_task(sunspec_server.manage_esphome_connection())

    # Houd de main loop draaiende om de asyncio gebeurtenissen te verwerken
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
