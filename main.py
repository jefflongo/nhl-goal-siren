#!/usr/bin/python

import argparse
import configparser
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import pygame
from nhlpy import NHLClient
from nhlpy.http_client import NHLApiException

import hardware as hw

SCRIPT_DIR = Path(__file__).parent
GOAL_SFX = Path(SCRIPT_DIR, "goal.mp3")
CONFIG_FILE = Path(SCRIPT_DIR, "config.ini")

SCHEDULE_POLL_INTERVAL = 3600
ON_TEAM_SCORE_DELAYS = 0, 10, 30, 60


def validate_team(value):
    if isinstance(value, str) and len(value) == 3 and value.isalpha():
        return value
    raise argparse.ArgumentTypeError(
        "Argument must be a three-letter team name (i.e. LAK)"
    )


# parse team
parser = argparse.ArgumentParser()
parser.add_argument(
    "team", type=validate_team, help="Three-letter team name abbreviation"
)
TEAM = parser.parse_args().team.upper()

print("Starting...")

# load config
config = configparser.ConfigParser(defaults={"delay": ON_TEAM_SCORE_DELAYS[0]})
config.read(CONFIG_FILE)
on_team_score_delay = config.getint(configparser.DEFAULTSECT, "delay")


def write_delay_config(delay: int) -> None:
    config.set(configparser.DEFAULTSECT, "delay", str(delay))
    with open(CONFIG_FILE, "w", encoding="utf-8") as file:
        config.write(file)


def on_delay_changed(delay: int) -> None:
    global on_team_score_delay  # pylint: disable=global-statement

    on_team_score_delay = delay
    write_delay_config(delay)
    print(f"Delay changed to {delay} seconds")


try:
    INITIAL_DELAY_INDEX = ON_TEAM_SCORE_DELAYS.index(on_team_score_delay)
except ValueError:
    # update to the nearest valid value
    nearest = min(
        ON_TEAM_SCORE_DELAYS,
        key=lambda valid_delay: abs(on_team_score_delay - valid_delay),
    )
    INITIAL_DELAY_INDEX = ON_TEAM_SCORE_DELAYS.index(nearest)
    on_delay_changed(ON_TEAM_SCORE_DELAYS[INITIAL_DELAY_INDEX])


try:
    # setup hardware
    hw.hardware_init()
    siren = hw.Siren()
    ui = hw.CycleUI(ON_TEAM_SCORE_DELAYS, INITIAL_DELAY_INDEX, on_delay_changed)

    # setup sfx
    pygame.mixer.init()
    pygame.mixer.music.load(GOAL_SFX)

    # setup NHL client
    client = NHLClient()

except Exception as e:
    print(f"Startup failed: {e}", file=sys.stderr)
    hw.hardware_deinit()
    raise SystemExit(1) from e


def get_next_game(team: str) -> Optional[tuple[int, datetime]]:
    """
    Get the next in-progress or future game for the target team. Returns `None` if no upcoming games
    are near, otherwise returns a tuple containing the game id and date.
    """
    try:
        info = client.schedule.get_schedule_by_team_by_week(team)
    except NHLApiException:
        print("Failed to retrieve schedule", file=sys.stderr)
        return None

    schedule = list(
        map(
            lambda json: (
                json["id"],
                datetime.strptime(json["startTimeUTC"], "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=timezone.utc
                ),
            ),
            filter(lambda json: json["gameState"] != "OFF", info),
        )
    )

    if not schedule:
        # no games this week
        return None

    return min(schedule, key=lambda x: x[1])


def wait_for_next_game() -> int:
    """Waits for the next upcoming game for the target team to start, and returns its game id."""
    next_game_id = -1
    while True:
        maybe_game = get_next_game(TEAM)
        if not maybe_game:
            time.sleep(SCHEDULE_POLL_INTERVAL)
            continue

        game_id, game_time = maybe_game
        now = datetime.now(timezone.utc)

        if now > game_time:
            # game already started! get in there!
            return game_id

        if game_id != next_game_id:
            print(
                f"Scheduling next {TEAM} game (id {game_id}) for {game_time.astimezone()}"
            )
            next_game_id = game_id

        time_until_game = (game_time - now).total_seconds()
        if time_until_game > SCHEDULE_POLL_INTERVAL:
            # game is not close to starting. sleep for the prescribed interval and refresh
            # the schedule again.
            time.sleep(SCHEDULE_POLL_INTERVAL)
        else:
            # the game is starting soon. wait for it to start.
            time.sleep(time_until_game)
            return game_id


def monitor_game(game_id: int, handler: Callable[[int], None]) -> None:
    """Monitors a live game, calling the given handler when the target team scores."""
    print(f"Observing {TEAM} game (id {game_id})...")

    try:
        info = client.game_center.boxscore(game_id)
    except NHLApiException:
        print("Failed to retrieve game", file=sys.stderr)
        return

    while info["gameState"] in ("FUT", "PRE"):
        # game hasn't started yet, wait it out
        time.sleep(1)
        try:
            info = client.game_center.boxscore(game_id)
        except NHLApiException:
            # silently ignore and try again
            continue

    side = "homeTeam" if info["homeTeam"]["abbrev"] == TEAM else "awayTeam"
    team_score = info[side]["score"]

    while info["gameState"] != "OFF":
        time.sleep(1)

        try:
            info = client.game_center.boxscore(game_id)
        except NHLApiException:
            # silently ignore and try again
            continue

        new_team_score = info[side]["score"]
        if new_team_score > team_score:
            team_score = new_team_score
            handler(team_score)

    print(f"{TEAM} game ended")


def on_team_score(team_score: int) -> None:
    time.sleep(on_team_score_delay)
    print(f"{TEAM} scored! Total goals: {team_score}")

    siren.enable()
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.1)
    siren.disable()


try:
    while True:
        try:
            game_id = wait_for_next_game()
            monitor_game(game_id, on_team_score)
        except KeyboardInterrupt:
            print("Shutting down...")
            break

except Exception as e:
    print(f"Unexpected error: {e}", file=sys.stderr)
    raise SystemExit(1) from e

finally:
    hw.hardware_deinit()
