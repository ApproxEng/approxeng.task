# Running as a service

Create a file `SERVICENAME.service` in `/etc/systemd/system`, making note of the location of your Python file
and the virtual environment used to run it, and replacing `SERVICENAME` with something appropriate to your particular 
application. Remember, you'll need to use absolute paths here and anywhere else such as references in scripts you then 
call.

Because we're using a virtual environment we know the script will pick up exactly the same libraries
as when we run it outside of the service. If you do not do this you might run into problems as the
user running the service isn't the same as your regular one and won't see any locally installed libraries. Use a virtual
environment, it'll make your life easier. Activate your environment and use `which python` to get the full path
to use in the system unit file:

```
[Unit]
Description=Simple systemd service.

[Service]
Type=simple
ExecStart=/home/pi/venv/bin/python /home/pi/SERVICENAME.py

[Install]
WantedBy=multi-user.target
``` 

Set permissions:

```shell script
> sudo chmod 644 /etc/systemd/system/SERVICENAME.service
```

Enable service to run on boot:

```shell script
> sudo systemctl enable SERVICENAME
Created symlink /etc/systemd/system/multi-user.target.wants/SERVICENAME.service → /etc/systemd/system/SERVICE.service.
```

See the status of the service:

```shell script
> systemctl status SERVICENAME
```

## Logging to systemd journal

Get the Python systemd bindings:

```shell script
(venv) > pip install systemd
```

Configure a logger to talk to them:

```python
from systemd.journal import JournaldLogHandler
import logging

logger = logging.getLogger(__name__)
# Create a new handler, specify the service name as identifier
handler = JournaldLogHandler(identifier='SERVICENAME')
handler.setFormatter(logging.Formatter('[%(levelname)s] %(name)s : %(message)s'))
logger.addHandler(handler)
# Set a logging level
logger.setLevel(logging.DEBUG)
```

Show logs, filtering for this service:

```shell script
> journalctl -t SERVICENAME
```

Add a `-f` to follow, showing messages as they're received.