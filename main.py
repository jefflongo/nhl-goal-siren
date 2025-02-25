import sys
import time
from datetime import datetime, timezone
from typing import Callable, Optional

import pygame
from nhlpy import NHLClient
from nhlpy.http_client import NHLApiException

import hardware as hw

TEAM = "LAK"
SCHEDULE_POLL_INTERVAL = 3600
ON_TEAM_SCORE_DELAYS = 0, 5, 10, 30
ON_TEAM_SCORE_DELAY = ON_TEAM_SCORE_DELAYS[0]


def on_delay_changed(delay):
    global ON_TEAM_SCORE_DELAY  # pylint: disable=global-statement
    ON_TEAM_SCORE_DELAY = delay
    print(f"Delay changed to {delay} seconds")


# setup hardware
hw.hardware_init()
siren = hw.Siren()
ui = hw.CycleUI(ON_TEAM_SCORE_DELAYS, on_delay_changed)

# setup sfx
pygame.mixer.init()
pygame.mixer.music.load("goal.mp3")

# setup NHL client
client = NHLClient()


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


def monitor_game(game_id: int, handler: Callable[[], None]) -> None:
    """Monitors a live game, calling the given handler when the target team scores."""
    print(f"Observing {TEAM} game (id {game_id})...")

    try:
        info = client.game_center.boxscore(game_id)
    except NHLApiException:
        print("Failed to retrieve game", file=sys.stderr)
        return

    side = "homeTeam" if info["homeTeam"] == TEAM else "awayTeam"
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
            print(f"{TEAM} scored! Total score: {new_team_score}")
            team_score = new_team_score
            handler()

    print("Game ended")


def on_team_score():
    time.sleep(ON_TEAM_SCORE_DELAY)

    siren.enable()
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pass
    siren.disable()


while True:
    try:
        game_id = wait_for_next_game()
        monitor_game(game_id, on_team_score)
    except KeyboardInterrupt:
        break

hw.hardware_deinit()
