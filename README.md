# NHL Goal Siren

A program to light a siren and play a sound effect any time your favorite NHL team scores a goal. 

This program was designed for use with a Raspberry Pi which toggles the siren with a GPIO pin. It also supports a simple interface with a button and three LEDs for cycling through four preset delay settings to synchronize when a goal occurs and when the siren activates. The program can be installed as a systemd service using the provided template to make the program automatically run on boot.

## Installation

```bash
pip install -r requirements.txt
```

If setting up on Raspberry Pi:

```bash
sudo apt install -y python3-rpi-lpgio
```

To run the program automatically on boot, modify the `hockey.service` file and edit the `<>` fields with your configuration. The run the following:

```bash
sudo mv hockey.service /etc/systemd/system/
sudo systemctl enable hockey
sudo systemctl start hockey
```

Debug logs can be viewed with the following command (add it as an alias!):

```bash
journalctl -u hockey -f --no-tail
```
