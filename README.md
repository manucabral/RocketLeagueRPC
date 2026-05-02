<p align="center">
<img width="250" alt="rpc-logo" src="https://github.com/user-attachments/assets/c5c0dc6c-3871-4d4e-8310-4019f5aec34e" />
</p>


<h1 align="center">Rocket League RPC</h1>

<p align="center">
Desktop application to show real-time Rocket League data in Discord Rich Presence using Rocket League 
Stats API.
</p>

<div align="center">
    <img src="https://img.shields.io/badge/version-0.0.2-blue" />
    <img src="https://img.shields.io/github/downloads/manucabral/RocketLeagueRPC/total" />
    <img src="https://img.shields.io/badge/code%20style-black-000000.svg" />
    <img src="https://img.shields.io/github/contributors/manucabral/RocketLeagueRPC" />
    <img src="https://img.shields.io/github/license/manucabral/RocketLeagueRPC" />
    <img src="https://img.shields.io/github/commit-activity/m/manucabral/RocketLeagueRPC" />
</div>

<div align="center">
  <img width="600" alt="demotraining" src="https://github.com/user-attachments/assets/5c8d3797-cd0b-4326-aa36-6b56fee81ad7" />
</div>

## Download

The latest release is available in the [Releases](https://github.com/manucabral/RocketLeagueRPC/releases) section.

## Features
- Live tracker and Discord connection status.
- Automatic Rich Presence updates during matches.
- Real-time match details, including arena, mode, timer, status, and score.
- Customizable presence fields.
- Preset support for saving and switching profiles.
- StatsAPI can be enabled or disabled from the desktop app.
- Local storage for settings and presets.
- Automatic Discord RPC reconnect on startup.


## Screenshots
<p align="center">
  <img width="700" alt="home_screenshot" src="https://github.com/manucabral/RocketLeagueRPC/blob/main/docs/assets/home.png?raw=true" />
  <img width="354" height="197" alt="discord-small" src="https://github.com/user-attachments/assets/626ae1e9-dfee-499e-b0db-ea81e891c920" />
  <img width="400" height="200" alt="discord-hover" src="https://github.com/user-attachments/assets/90045ccc-03e4-421f-b8f2-bcfbfd61a344" />
  <img width="365" height="196" alt="discord-replay" src="https://github.com/user-attachments/assets/3eb302dd-a9e2-4b72-9068-ce5e74e60725" />
</p>

## RoadMap
- [ ] Add map images to Rich Presence image assets.
- [ ] Add more presence fields (rank, playlist, etc.).
- [ ] Create a faster version without webview.
And more to come.

## Requirements
- Python 3.12
- Discord desktop app running
- Rocket League running (for live data)

Python dependencies:

- `pywebview`
- `rlstatsapi`
- `pytest` (tests)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```


## Contributors
People who contribute to the development, maintenance, and improvement of the application.

<a href="https://github.com/manucabral/rocketleaguerpc/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=manucabral/rocketleaguerpc" />
</a>


## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

