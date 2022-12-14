#!/usr/bin/env python3

import pyhid_usb_relay

relayboard = pyhid_usb_relay.find()
for i in range(4):
    relayboard[i+1] = False

