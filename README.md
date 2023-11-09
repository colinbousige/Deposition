# Deposition

Streamlit web app to be installed on a linux computer to control an ALD-CVD setup. Relays are in a usb relay board like [this](https://www.amazon.fr/Multifonctionnel-Multiples-Protection-syst%C3%A8mes-dexploitation/dp/B0B17CWZBR/ref=sr_1_16?__mk_fr_FR=%C3%85M%C3%85%C5%BD%C3%95%C3%91&crid=25QXN08DBGO7S&keywords=relais+usb&qid=1699542126&s=electronics&sprefix=relais+usb%2Celectronics%2C78&sr=1-16).

Setup for Ubuntu 23.10:
```bash
python3 -m pip install streamlit pyserial scipy pyhid-usb-relay --break-system-packages
sudo usermod -a -G dialout $USER
sudo vi /etc/udev/rules.d/90-hidusb-relay.rules
```
then paste this:
```
# Give all users access to USB HID Relay
SUBSYSTEM=="usb", ATTRS{idVendor}=="16c0", ATTRS{idProduct}=="05df", MODE:="0660", GROUP="dialout"
```
then unplug the USB device, run this an re-plug:
```bash
sudo udevadm control --reload-rules
```

Finally, just do this:
```bash
cd Deposition/
./launch.sh
# or
streamlit run Deposition.py
```
