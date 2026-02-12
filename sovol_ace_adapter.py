# MTConnect adapter for Sovol Ace Printer
# 2/11/2026 revised by
# Trevor Kates

import time, datetime, requests
from data_item import Event, Sample
from mtconnect_adapter import Adapter

class SovolAceAdapter:
    def __init__(self, host, port, printer_ip):
        print(f"Initializing Adapter for Printer: {printer_ip}...")
        self.adapter = Adapter((host, port))
        self.printer_ip = printer_ip
        self.query_url = (f"http://{printer_ip}:7125/printer/objects/query?"
                          "extruder&heater_bed&toolhead&print_stats&"
                          "display_status&virtual_sdcard&"
                          "filament_switch_sensor%20filament_sensor")
        self.create_mtconnect_entities()

    def create_mtconnect_entities(self):
        self.avail = Event('avail'); self.adapter.add_data_item(self.avail)
        self.bed_temp = Sample('bed_temp'); self.adapter.add_data_item(self.bed_temp)
        self.ext_temp = Sample('ext_temp'); self.adapter.add_data_item(self.ext_temp)
        self.x_pos = Sample('x_pos'); self.adapter.add_data_item(self.x_pos)
        self.y_pos = Sample('y_pos'); self.adapter.add_data_item(self.y_pos)
        self.z_pos = Sample('z_pos'); self.adapter.add_data_item(self.z_pos)
        self.execution = Event('exec'); self.adapter.add_data_item(self.execution)
        self.program = Event('prog'); self.adapter.add_data_item(self.program)
        self.fil_status = Event('fil_status'); self.adapter.add_data_item(self.fil_status)
        self.print_status = Event('print_status'); self.adapter.add_data_item(self.print_status)
        self.print_progress = Sample('print_progress'); self.adapter.add_data_item(self.print_progress)

    def poll_printer(self):
        try:
            response = requests.get(self.query_url, timeout=5)
            r = response.json()
            if 'result' not in r or 'status' not in r['result']:
                print(f"!! API Issue: {r}")
                return None
            return r['result']['status']
        except Exception as e:
            print(f"!! Network Error: {e}")
            return None

    def gather_data(self):
        print("Starting Data Loop...")
        while True:
            data = self.poll_printer()
            if data:
                self.adapter.begin_gather()
                self.avail.set_value("AVAILABLE")

                # Extracting values
                ext = data.get('extruder', {}).get('temperature', 0)
                bed = data.get('heater_bed', {}).get('temperature', 0)
                pos = data.get('toolhead', {}).get('position', [0,0,0,0])
                stats = data.get('print_stats', {})

                self.ext_temp.set_value(ext)
                self.bed_temp.set_value(bed)
                self.x_pos.set_value(pos[0]); self.y_pos.set_value(pos[1]); self.z_pos.set_value(pos[2])
                self.execution.set_value(stats.get('state', 'standby').upper())
                self.program.set_value(stats.get('filename', 'NONE'))

                prog = data.get('virtual_sdcard', {}).get('progress', 0)
                self.print_progress.set_value(round(prog * 100, 1))
                self.print_status.set_value(data.get('display_status', {}).get('message', 'Idle'))

                fil = data.get('filament_switch_sensor filament_sensor', {}).get('filament_detected', False)
                self.fil_status.set_value("LOADED" if fil else "OUT")

                self.adapter.complete_gather()
                print(f"{datetime.datetime.now()}: Status Synced | Ext: {ext}C | Bed: {bed}C")
            else:
                print(f"{datetime.datetime.now()}: No valid data from printer...")
            time.sleep(1)

if __name__ == "__main__":
    sovol_adapter = SovolAceAdapter('127.0.0.1', 7878, '192.168.1.56')
    sovol_adapter.adapter.start()
    sovol_adapter.gather_data()