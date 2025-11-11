# Backend deploy guide (Django + systemd + Nginx)

## Overview

This repository includes:

- `.github/workflows/deploy.yml`: GitHub Actions workflow to auto-deploy on push
- `server/deploy.sh`: Idempotent deploy script (pulls, installs, migrates, restarts)

## Assumptions

- Ubuntu/Debian server with `systemd` and `nginx`
- Python 3.10+ available as `python3`
- Repo will live at `/opt/yandextma/repo`
- Virtualenv at `/opt/yandextma/venv`
- Systemd service name `yandextma.service`

## One-time server bootstrap (run as root)

1. Create system user and directories:
   useradd -m -s /bin/bash deploy || true
   mkdir -p /opt/yandextma
   chown -R deploy:deploy /opt/yandextma

2. Install dependencies:
   apt update
   apt install -y git python3 python3-venv python3-pip nginx

3. Clone repository:
   sudo -u deploy bash -lc '
   cd /opt/yandextma
   git clone <YOUR_GITHUB_REPO_SSH_URL> repo
   '

4. Create and prime venv:
   sudo -u deploy bash -lc '
   python3 -m venv /opt/yandextma/venv
   source /opt/yandextma/venv/bin/activate
   pip install --upgrade pip
   cd /opt/yandextma/repo/server
   pip install -r requirements.txt
   '

5. Gunicorn systemd unit `/etc/systemd/system/yandextma.service`:
   [Unit]
   Description=YandexTMA Django Gunicorn
   After=network.target

   [Service]
   User=deploy
   Group=www-data
   WorkingDirectory=/opt/yandextma/repo/server
   Environment=DJANGO_SETTINGS_MODULE=core.settings
   Environment=PYTHONPATH=/opt/yandextma/repo/server
   ExecStart=/opt/yandextma/venv/bin/gunicorn core.wsgi:application --bind 127.0.0.1:8000 --workers 3 --timeout 60
   Restart=always

   [Install]
   WantedBy=multi-user.target

   systemctl daemon-reload
   systemctl enable yandextma.service
   systemctl start yandextma.service

6. Nginx site `/etc/nginx/sites-available/yandextma`:
   server {
   listen 80;
   server*name *;

   location /static/ {
   alias /opt/yandextma/repo/server/static/;
   }

   location /media/ {
   alias /opt/yandextma/repo/server/media/;
   }

   location / {
   proxy_set_header Host $host;
   proxy_set_header X-Forwarded-Proto $scheme;
   proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
   proxy_pass http://127.0.0.1:8000;
   }
   }

   ln -s /etc/nginx/sites-available/yandextma /etc/nginx/sites-enabled/yandextma
   nginx -t && systemctl reload nginx

7. Initial Django setup:
   sudo -u deploy bash -lc '
   source /opt/yandextma/venv/bin/activate
   cd /opt/yandextma/repo/server
   python manage.py migrate --noinput
   python manage.py collectstatic --noinput
   '

## GitHub Actions configuration

Add repository secrets:

- `SSH_HOST` = server IP or hostname
- `SSH_USER` = deploy
- `SSH_PORT` = 22 (or your SSH port)
- `SSH_KEY` = Private SSH key (PEM). Ensure the public key is in `/home/deploy/.ssh/authorized_keys` on server.

Optionally, configure environment on the server so the workflow can locate paths:
echo 'export APP_DIR=/opt/yandextma' >> /home/deploy/.profile
echo 'export REPO_DIR=/opt/yandextma/repo' >> /home/deploy/.profile
echo 'export VENV_DIR=/opt/yandextma/venv' >> /home/deploy/.profile
echo 'export SERVICE_NAME=yandextma' >> /home/deploy/.profile

## Manual deploy via SSH

Once bootstrapped, you can deploy manually with:
ssh deploy@<HOST> "bash -lc 'APP_DIR=/opt/yandextma /opt/yandextma/repo/server/deploy.sh main'"

## Notes

- If your Django `ALLOWED_HOSTS`, DB credentials, or env vars are needed, configure them via environment or `.env` loaded by `settings.py`. Ensure systemd unit exports them securely.
- If you use HTTPS/Domain, add certs via certbot and update Nginx server_name.
