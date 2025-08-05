# <p align="center">SchulwareAPI</p>
<p align="center">
  <img src="./assets/schulwareapi_logo.png" width="200" alt="SchulwareAPI Logo">
</p>
<p align="center">
  <strong>A FastAPI wrapper for Schulnetz, providing a unified API with dynamic routing and simplified access.</strong>
</p>
<p align="center">
  <a href="https://github.com/PianoNic/SchulwareAPI"><img src="https://badgetrack.pianonic.ch/badge?tag=schulware-api&label=visits&color=243aae&style=flat" alt="visits"/></a>
  <a href="https://github.com/PianoNic/SchulwareAPI/releases"><img src="https://img.shields.io/github/v/release/PianoNic/SchulwareAPI?include_prereleases&color=243aae&label=Latest%20Release"/></a>
  <a href="#-installation"><img src="https://img.shields.io/badge/Selfhost-Instructions-243aae.svg"/></a>
</p>

## ✨ Features
- **Dynamic Routing**: Configured via `endpoints.json`.
- **Smart Headers**: Auto-applies correct headers and Authorization.
- **Env Variables**: Securely loads sensitive data.
- **Param Forwarding**: Transparently passes query parameters.
- **Auto Docs**: FastAPI provides interactive Swagger UI/ReDoc.
- **Docker Ready**: Easy containerized deployment.

## 🚀 Installation

### Prerequisites
- Python 3.15+
- Docker (optional)

### Access the API
API will be live at:
- **Interactive Docs**: [http://localhost:8000/](http://localhost:8000/)


## ⚡ Usage
The wrapper automatically handles API key injection and sets correct request headers.

**Example: Get Current User Info**
```bash
curl "http://localhost:8000/me" -H 'Accept: application/json'
```

**Example: Get Events with Dates**
```bash
curl "http://localhost:8000/me/events?min_date=2025-08-05&max_date=2025-08-06" -H 'Accept: application/json'
```

Refer to `/docs` for all proxied endpoints.

## ⚙️ Configuration (`endpoints.json`)
Defines the wrapper's routes. Minimal fields:
```json
{
  "name": "translations",
  "path": "/config/translations",
  "method": "GET",
  "url_path": "/rest/v1/config/translations",
  "query_params": ["filter"]
}
```
- **`name`**: Internal identifier.
- **`path`**: Wrapper's URL path.
- **`method`**: HTTP method.
- **`url_path`**: Upstream API's full path (determines base URL).
- **`query_params`**: List of query parameters to forward.

## 📜 License
This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---
<p align="center">Made with ❤️ by <a href="https://github.com/PianoNic">PianoNic</a></p>
