from ressources.setup import *

turn_ON(Carrier)
citoctrl.open()
cito_address = "/dev/ttyUSB0"
citoctrl = cb.CitoBase(host_mode=1, host_addr=cito_address)

plasma = 30
print(f"Current plasma = {citoctrl.get_power_setpoint_watts()[1]} Watt")
citoctrl.set_power_setpoint_watts(plasma)  # set the rf power
print(f"Current plasma = {citoctrl.get_power_setpoint_watts()[1]} Watt")
citoctrl.set_rf_on()
citoctrl.set_rf_off()
