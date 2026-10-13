# Production Service

This runs the RSVP app with Gunicorn under systemd, so it starts on boot and restarts if it crashes.

Install dependencies:

```bash
cd /home/pierpaolo/prj/wedding/rsvp
venv/bin/python -m pip install -r requirements.txt
```

Install and start the service:

```bash
sudo cp deploy/rsvp.service /etc/systemd/system/rsvp.service
sudo systemctl daemon-reload
sudo systemctl enable --now rsvp
```

Check status and logs:

```bash
systemctl status rsvp
journalctl -u rsvp -f
```

Restart after code changes:

```bash
sudo systemctl restart rsvp
```

The app listens on `0.0.0.0:5000`, so it should be available on the home server LAN IP, for example:

```text
http://192.168.178.202:5000/
```
