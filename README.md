# <p align="center">SchulwareAPI</p>
<p align="center">
  <img src="./assets/icon.svg" width="200" alt="SchulwareAPI, an unofficial schulNetz API">
</p>
<p align="center">
  <strong>Unofficial schulNetz API for Swiss schools: grades, absences, timetable and more as JSON.</strong>
</p>
<p align="center">
  <a href="https://github.com/PianoNic/SchulwareAPI"><img src="https://badgetrack.pianonic.ch/badge?tag=schulware-api&label=visits&color=243aae&style=flat" alt="visits"/></a>
  <a href="https://github.com/PianoNic/SchulwareAPI/blob/main/LICENSE"><img src="https://img.shields.io/github/license/PianoNic/SchulwareAPI?color=243aae"/></a>
  <a href="https://github.com/PianoNic/SchulwareAPI/releases"><img src="https://img.shields.io/github/v/release/PianoNic/SchulwareAPI?include_prereleases&color=243aae&label=Latest%20Release"/></a>
</p>

> [!IMPORTANT]
> This project is **NOT** affiliated with, endorsed by, or connected to schulNetz or Centerboard AG in any way.

## About

SchulwareAPI is an unofficial, self-hosted REST API for schulNetz, the school portal many Swiss schools use (Kantonsschulen, Berufsfachschulen, Gymnasien). It signs students in to their school's schulNetz and returns their data as JSON. It is stateless. The Swagger docs are at `/`.

## What you can read

- Grades (Noten) with class averages, and exams (Prüfungen)
- Absences (Absenzen) and lateness
- Timetable and agenda (Stundenplan)
- Documents, semester reports (Zeugnisse) and courses
- Push notifications for new grades

## Sign-in

`GET /api/authenticate/login-method` tells how a school signs in:

- `microsoft`: Microsoft sign-in, done with `POST /api/authenticate/login`.
- `native`: schulNetz's own login form, also done with `POST /api/authenticate/login`.
- `browser`: any other login, such as a cantonal one. The user signs in in a browser started with `/api/authenticate/browser/start`, then `/api/authenticate/browser/complete` turns the code into tokens.

All other requests send the school's URL in the `X-Schulnetz-Base-Url` header.

## Self-hosting

```yaml
services:
  schulware-api:
    image: ghcr.io/pianonic/schulwareapi:latest
    # image: pianonic/schulwareapi:latest # Docker Hub
    ports:
      - "8000:8000"
    restart: unless-stopped
```

```bash
docker compose up -d
```

All settings are optional. To set any, add them under `environment:` or point `env_file:` at a copy of [`.env.example`](.env.example). Set `DOCS_ENABLED=false` to hide the Swagger docs, or `OPENAPI_ENABLED=false` to also hide `/openapi.json`.

## License

MIT. See [LICENSE](LICENSE).

---
<p align="center">Made with ❤️ by <a href="https://github.com/PianoNic">PianoNic</a></p>
