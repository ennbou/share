# Local File Share Server

A lightweight Flask app for sharing files on your local network.

- Upload files through a drag-and-drop web UI.
- Serve downloadable files from a shared folder.
- Advertise the service on the LAN using mDNS/Bonjour.

## Project Structure

- `server.py` — Flask server and web interface.
- `uploads/` — incoming uploaded files are saved here.
- `shares/` — files in this folder are listed and downloadable.

## Requirements

- Python 3.9+
- pip

Python packages:

- `flask`
- `werkzeug`
- `zeroconf`

## Setup

From the project root:

```bash
python3 -m venv venv
source venv/bin/activate
pip install flask werkzeug zeroconf
```

## Run

```bash
python3 server.py
```

The app starts on port `8080` and prints:

- Local URL: `http://localhost:8080`
- Network URL: `http://<your-local-ip>:8080`

Open either URL in a browser.

## How It Works

- Uploading uses `POST /upload` and stores files in `uploads/`.
- Download list is served by `GET /shares` from files in `shares/`.
- Downloading a file uses `GET /shares/<filename>`.

## Notes

- Max upload size is `500 MB` (`MAX_CONTENT_LENGTH`).
- Duplicate upload names are auto-renamed (e.g. `file_1.ext`).
- `uploads/` and `shares/` are created automatically if missing.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
