# <p align="center">SchulwareAPI</p>
<p align="center">
  <img src="./assets/schulwareapi_logo.png" width="200" alt="SchulwareAPI Logo">
</p>
<p align="center">
  <strong>Unified API for Schulnetz, simplifying data access with dynamic routing.</strong>
</p>
<p align="center">
  <a href="https://github.com/PianoNic/SchulwareAPI"><img src="https://badgetrack.pianonic.ch/badge?tag=schulware-api&label=visits&color=243aae&style=flat" alt="visits"/></a>
  <a href="https://github.com/PianoNic/SchulwareAPI/blob/main/LICENSE"><img src="https://img.shields.io/github/license/PianoNic/SchulwareAPI?color=243aae"/></a>
  <a href="https://github.com/PianoNic/SchulwareAPI/releases"><img src="https://img.shields.io/github/v/release/PianoNic/SchulwareAPI?include_prereleases&color=243aae&label=Latest%20Release"/></a>
  <a href="#-installation"><img src="https://img.shields.io/badge/Selfhost-Instructions-243aae.svg"/></a>
</p>

## ⚠️ Disclaimer
This project is **NOT** affiliated with, endorsed by, or connected to Schulnetz or Centerboard AG in any way. This is an independent, unofficial API wrapper that provides a unified interface to interact with their existing systems.

## ⚙️ About The Project
SchulwareAPI is a unified API designed for Schulnetz systems, simplifying data access through dynamic routing. It allows access to data via mobile REST or web scraping and includes interactive Swagger UI for automatic documentation, making API understanding easier.

## ✨ Features
- **Unified API**: Access data via mobile REST or web scraping, optimized for each endpoint.
- **Auto-Docs**: Interactive Swagger UI and `openapi.json` for easy API understanding.
- **Docker Ready**: Simple, containerized deployment.
  
## 🛠️ Compatibility
This API has been tested on:
- bbbaden
- ~kanti baden~ (Still implementing php scraper)

Schulnetz systems.

### Access the API
API will be live at:
- **Swagger Docs**: [http://localhost:8000/](http://localhost:8000/)

## 🐳 Docker & Container Registry Usage

You can run SchulwareAPI easily using Docker or pull prebuilt images from public registries.

### Docker Compose 

You can also use the provided `compose.yml` for local development or deployment. Make sure to set up your `.env` file with the required environment variables.

```sh
docker compose up -d
```

### Option 2: Run with Docker Compose (Recommended)
**1. Create a `compose.yml` file:**  
Use your favorite editor to create a `compose.yml` file and paste this into it:
```yaml
services:
  schulware-api:
    image: pianonic/schulwareapi:latest # Uses the image from Docker Hub
    # image: ghcr.io/pianonic/schulwareapi:latest # Uses the image from GitHub Container Registry
    ports:
      - "8000:8000"
    environment:
      - PYTHONUNBUFFERED=1
      - SCHULNETZ_API_BASE_URL=${SCHULNETZ_API_BASE_URL}
      - SCHULNETZ_WEB_BASE_URL=${SCHULNETZ_WEB_BASE_URL}
      - SCHULNETZ_CLIENT_ID=${SCHULNETZ_CLIENT_ID}
    env_file:
      - .env
    volumes:
      - ./db:/app/db              # Database storage
    restart: unless-stopped
    init: true  # Recommended to avoid zombie processes
    ipc: host   # Recommended for Chromium to avoid memory crashes
```

**2. Create required directory:**
```bash
mkdir db
```

**3. Start it:**
```bash
docker compose up -d
```
The API will be available at [http://localhost:8000](http://localhost:8000).

**Data Persistence:**
- `./db/` - SQLite database files

## 📜 License
This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---
<p align="center">Made with ❤️ by <a href="https://github.com/PianoNic">PianoNic</a></p>
