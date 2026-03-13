# Smoke Alarm Bot

A small Discord bot that joins a user's voice channel and plays a smoke alarm chirp on a fixed interval.

## Prerequisites

- Python 3.10+
- FFmpeg installed and available on PATH

## Setup

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

2. Create a .env file from the example:

```bash
copy .env.example .env
```

3. Set DISCORD_TOKEN in .env.

## Run

```bash
python src\smoke_alarm_bot.py
```

## Slash Commands

- /join: Joins your current voice channel and starts chirping.
- /leave: Stops chirping and disconnects.
- /status: Shows current connection status.
- /stats: Shows the current broke meter (you can also pass a user).
- /localstats: Shows broke meter stats for the current server.
- /globalstats: Shows broke meter stats across all servers.

## Database

- Uses SQLite at `data/smoke_alarm.db` by default.
- Tracks voice presence events for users in the bot's voice channel.
- Increments a user's broke meter by 1 for each chirp heard while they are in the channel.

## Project Structure

- `src/smoke_alarm_bot.py`: Entry point that wires and runs the bot.
- `src/smoke_alarm/config.py`: Environment/config loading and validation.
- `src/smoke_alarm/database.py`: SQLite schema and stats/leaderboard queries.
- `src/smoke_alarm/voice_tracking.py`: Chirp loop and voice presence tracking.
- `src/smoke_alarm/bot_app.py`: Discord bot setup, lifecycle events, and cog registration.
- `src/smoke_alarm/cogs/voice_cog.py`: Voice-related slash commands and voice-state listener.
- `src/smoke_alarm/cogs/stats_cog.py`: User stats slash command.
- `src/smoke_alarm/cogs/leaderboard_cog.py`: Server/global leaderboard slash commands.
