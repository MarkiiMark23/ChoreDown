# Deploying ChoreDown on a Proxmox / Ubuntu VM

This replaces the old **TaskDown** app with ChoreDown. ChoreDown serves its own static
files via WhiteNoise, so the only moving parts are: PostgreSQL → Gunicorn → (optional) Nginx.

> **Why this matters:** the most common "kids don't get added / buttons error out" symptom is
> a database whose schema is behind the code. **Always run `python manage.py migrate` on every
> deploy.** The steps below make that explicit.

---

## 1. System packages

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip postgresql nginx git
```

## 2. PostgreSQL database

```bash
sudo -u postgres psql <<'SQL'
CREATE DATABASE choredown_db;
CREATE USER choredown_user WITH PASSWORD 'change-me-strong';
ALTER ROLE choredown_user SET client_encoding TO 'utf8';
ALTER ROLE choredown_user SET default_transaction_isolation TO 'read committed';
GRANT ALL PRIVILEGES ON DATABASE choredown_db TO choredown_user;
\q
SQL
```

## 3. Get the code + virtualenv

```bash
sudo mkdir -p /opt/choredown && sudo chown $USER:$USER /opt/choredown
git clone https://github.com/MarkiiMark23/ChoreDown.git /opt/choredown
cd /opt/choredown
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 4. Environment file

```bash
cp .env.example .env
# Generate a real key:
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(50))"
nano .env
```

Minimum for a LAN deploy at `192.168.1.190` over plain HTTP:

```env
SECRET_KEY=<the generated value>
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.190
DATABASE_URL=postgresql://choredown_user:change-me-strong@localhost:5432/choredown_db
```

> The app loads `.env` automatically via `python-dotenv`. If your process manager doesn't,
> use `set -a; source .env; set +a` before running management commands.

## 5. Migrate, collect static, create your login

```bash
set -a; source .env; set +a
python manage.py migrate              # <-- creates/updates ALL tables. Do this every deploy.
python manage.py collectstatic --noinput
python manage.py createsuperuser      # your parent/admin login
```

Sanity check it boots:

```bash
gunicorn choredown.wsgi:application --bind 0.0.0.0:8000
# visit http://192.168.1.190:8000 — Ctrl+C when satisfied
```

## 6. Run it as a service (systemd + Gunicorn)

`/etc/systemd/system/choredown.service`:

```ini
[Unit]
Description=ChoreDown (Gunicorn)
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/choredown
EnvironmentFile=/opt/choredown/.env
ExecStart=/opt/choredown/venv/bin/gunicorn choredown.wsgi:application \
          --workers 3 --bind 127.0.0.1:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo chown -R www-data:www-data /opt/choredown
sudo systemctl daemon-reload
sudo systemctl enable --now choredown
sudo systemctl status choredown
```

## 7. Nginx reverse proxy (optional but recommended)

`/etc/nginx/sites-available/choredown`:

```nginx
server {
    listen 80;
    server_name 192.168.1.190;
    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/choredown /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Now browse to **http://192.168.1.190**.

## 8. Updating to a new version

```bash
cd /opt/choredown
git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate            # never skip
python manage.py collectstatic --noinput
sudo systemctl restart choredown
./scripts/post_deploy_check.sh      # verifies config, migrations, static, and that the app answers
```

The smoke test catches the usual deploy breakage (missing migrations, app not
running) in one command. Add `--with-tests` to also run the full suite first.

## 9. Turning on HTTPS later

Once you have a domain + certificate (e.g. Caddy, or Nginx + certbot), add to `.env`:

```env
BEHIND_TLS_PROXY=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
CSRF_TRUSTED_ORIGINS=https://chores.yourdomain.com
```

…then `sudo systemctl restart choredown`.

---

### Retiring the old TaskDown

The old app lives at `/home/legendarymark/TaskDown/`. Once ChoreDown is verified working,
stop/disable its service and free the port:

```bash
sudo systemctl disable --now taskdown    # or whatever its service/process is called
```

TaskDown's data is **not** compatible with ChoreDown (different schema), so this is a fresh start —
recreate your parent account and re-add kids in ChoreDown.
