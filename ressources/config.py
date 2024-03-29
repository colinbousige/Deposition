import ressources.citobase as cb

# # # # # # # # # # # # # # # # # # # # # # # #
# Define relays attribution
# # # # # # # # # # # # # # # # # # # # # # # #

relays = {
    "TEB": (4,'NC'),# Normally Closed
    "H2" : (3,'NC'),# Normally Closed
    "Ar" : (2,'NO') # Normally Opened
}


# # # # # # # # # # # # # # # # # # # # # # # #
# Connection to Cito Plus plasma RF generator
# # # # # # # # # # # # # # # # # # # # # # # #

# If connected by Ethernet
# cito_address = "169.254.1.1"
# host_mode = 0 # Ethernet

# If connected by RS232 -> USB
cito_address = "/dev/ttyUSB0"
host_mode = 1 # Serial

citoctrl = cb.CitoBase(host_mode = host_mode, 
                       host_addr = cito_address)