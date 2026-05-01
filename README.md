<p align="center">
<img width="250" alt="rpc-logo" src="https://github.com/user-attachments/assets/c5c0dc6c-3871-4d4e-8310-4019f5aec34e" />
</p>


<h1 align="center">Rocket League RPC</h1>

<p align="center">
Desktop application to show real-time Rocket League data in Discord Rich Presence using Stats API.
</p>


## Features
- Live connection status for Tracker and Discord.
- Automatic Rich Presence updates during matches.
- Real-time match view (arena, mode, timer, status, and score).
- Granular configuration of visible presence fields.
- Presence presets (list, save, load, delete).
- Reconnect with retries at startup.

## Requirements

> Python 3.12
- `pywebview`
- `rlstatsapi`

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

## Demo
<p align="center">
<img width="700"  alt="image" src="https://github.com/user-attachments/assets/634eaa2c-cf72-4158-9e0f-5b66acf981ff" />
</p>


## RoadMap
- [ ] Add map images to Rich Presence image assets.
- [ ] Add more presence fields (rank, playlist, etc.).
- [ ] Create a faster version without webview.
And more to come.

## Contributing
Contributions are welcome. Please fork the repository and submit a pull request.

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

