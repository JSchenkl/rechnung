# Deployment: julius.schenkl.de

## Infrastruktur

Der VPS (85.215.165.248) hat einen zentralen **Caddy Reverse Proxy** (`/opt/proxy/`),
der eingehende HTTPS-Anfragen für `julius.schenkl.de` an diesen Container weiterleitet.
TLS-Zertifikat wird automatisch von Caddy per Let's Encrypt bezogen.

Die App läuft in `/opt/julius/` auf dem VPS.

## Was das Repo liefern muss

### 1. `Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "run:app"]
```

**Wichtig:**
- Produktionsstart über `gunicorn`, nicht `python run.py`
- Port muss `5000` sein (stimmt mit Caddy-Config überein)

### 2. `docker-compose.yml`

```yaml
services:
  julius-app:
    build: .
    container_name: julius-app
    restart: unless-stopped
    env_file: ./.env
    environment:
      FLASK_ENV: production
    volumes:
      - julius-data:/app/dbdata
    expose:
      - "5000"
    networks:
      - proxy

volumes:
  julius-data:

networks:
  proxy:
    name: proxy
    external: true
```

**Wichtig:**
- `expose` statt `ports` — Port ist nur intern für Caddy sichtbar
- Volume für SQLite-Datei (damit Daten bei Neubau erhalten bleiben)

### 3. SQLite-Pfad in `.env` (Produktion)

```
DATABASE_URL=sqlite:////app/dbdata/rechnung.db
```

Absoluter Pfad nötig, damit die Datei im gemounteten Volume landet.

## Deployment-Flow (auf dem VPS)

```bash
cd /opt/julius
git pull
docker compose up -d --build
```

Bei erstem Start zusätzlich DB-Migration:

```bash
docker compose exec julius-app flask db upgrade
```

## Was der Agent NICHT anfassen soll

- `/opt/proxy/Caddyfile` — bereits konfiguriert für julius.schenkl.de
- `/opt/julius/docker-compose.override.yml` — VPS-spezifisch, nicht im Repo
- `/opt/julius/.env` — Produktions-Secrets, nicht im Repo
