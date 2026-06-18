# ************************************************************************* #
#                                                                           #
#                                                      :::      ::::::::    #
#  fly_in.py                                         :+:      :+:    :+:    #
#                                                  +:+ +:+         +:+      #
#  By: asulon <asulon@student.42nice.fr>         +#+  +:+       +#+         #
#                                              +#+#+#+#+#+   +#+            #
#  Created: 2026/05/21 16:39:37 by asulon          #+#    #+#               #
#  Updated: 2026/06/18 14:46:19 by asulon          ###   ########.fr        #
#                                                                           #
# ************************************************************************* #

import sys
import re
from typing import Dict, Any
import pygame


class ConfigError(Exception):
    def __init__(self, message: str) -> None:
        print(f"Configuration File Error : {message}")


def join_connection(config: Dict):
    connections = config.get("connections")
    if connections is None:
        return config

    name_to_key = {v['name']: k for k, v in config['map'].items()}

    for point in config['map'].values():
        point['connections'] = []

    for connection in connections:
        point_a, point_b = connection.split('-')

        key_a = name_to_key[point_a]
        key_b = name_to_key[point_b]

        config['map'][key_a]['connections'].append(point_b)
        config['map'][key_b]['connections'].append(point_a)

    return config


def parse_config(filename: str) -> Dict[str, str]:
    """Parse data from config file return Dict[Key: Value]"""
    config = {}
    try:
        with open(filename) as file:
            config_list = file.read().split("\n")
            hub_index = 0
            connection_index = 0
            for line in config_list:
                if line.startswith("#"):
                    continue
                splited_line = line.split(":")
                if len(splited_line[0]) > 0:
                    key_name = splited_line[0]
                    if splited_line[0].lower() == "hub":
                        key_name = f"{key_name}_{hub_index}"
                        hub_index += 1
                    if splited_line[0].lower() == "connection":
                        key_name = f"{key_name}_{connection_index}"
                        connection_index += 1

                    config.update({key_name: splited_line[1].strip()})
    except (FileNotFoundError, PermissionError) as error:
        ConfigError(f"'{error.filename}' not found")
        sys.exit(1)
    except ValueError:
        ConfigError(f"error near '{line}'")
        sys.exit(1)
    return config


def parse_hub(hub: str):
    splited_hub = hub.split(" ")

    def parse_coordinate(value: Any, key_name: str) -> tuple[int, int]:
        """Validate and parse a coordinate in strict 'x,y' format."""
        if not isinstance(value, str) or not re.fullmatch(r"\d+,\d+", value):
            raise ConfigError(f"{key_name} must be in 'x,y' format")
        x_raw, y_raw = value.split(',')
        return int(x_raw), int(y_raw)
    try:
        name = splited_hub[0]
        coordinate = parse_coordinate(
            f"{splited_hub[1]},{splited_hub[2]}", name)
    except (ValueError) as error:
        print(error)

    res = {"name": splited_hub[0],
           "coordinate": coordinate,
           "metadata": splited_hub[3]}
    return res


def validate_map(map):
    pass


def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Check config file keys and values"""

    def parse_coordinate(value: Any, key_name: str) -> tuple[int, int]:
        """Validate and parse a coordinate in strict 'x,y' format."""
        if not isinstance(value, str) or not re.fullmatch(r"\d+,\d+", value):
            raise ConfigError(f"{key_name} must be in 'x,y' format")
        x_raw, y_raw = value.split(',')
        return int(x_raw), int(y_raw)

    """Checking required keys"""
    required_key = ['nb_drones', 'start_hub',
                    'end_hub']  # Voir si hub && connection are mandatory
    for key in required_key:
        if key not in config:
            print(
                f"Error: Missing mandatory key '{key}' in configuration.")
            sys.exit(1)
    new_config: Dict = {}

    try:
        """Assign new values with the correct types to the config keys"""

        for key, value in config.items():
            if key == "nb_drones":
                new_config[key] = int(value)
            elif "hub" in key:
                new_config.setdefault("map", {}).update(
                    {key: parse_hub(value)})
            elif "connection" in key:
                new_config.setdefault("connections", []).append(value)

    except (ValueError, TypeError):
        raise ConfigError("Invalid value type in configuration.")

    """Testing invalid values"""
    if new_config["nb_drones"] < 1:
        raise ConfigError("nb_drones must be positive integer")
    # if config['WIDTH'] < 0 or config['HEIGHT'] < 0:
    #     raise ConfigError("WIDTH and HEIGHT must be positive integers.")
    # w, h = config['WIDTH'], config['HEIGHT']
    # if not (0 <= config['ENTRY'][0] <= w and 0 <= config['ENTRY'][1] <= h):
    #     raise ConfigError("Entry out of bounds")
    # if not (0 <= config['EXIT'][0] <= w and 0 <= config['EXIT'][1] <= h):
    #     raise ConfigError("Exit out of bounds")
    # if config['ENTRY'] == config['EXIT']:
    #     raise ConfigError(
    #         "ENTRY and EXIT coordinates cannot be the same.")
    # if perfect_raw not in ("TRUE", "FALSE"):
    #     raise ConfigError(
    #         "Perfect must be bool")
    # config['PERFECT'] = (perfect_raw == "TRUE")
    # print(new_config)
    return new_config


def start_simulation():
    # pygame setup
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    clock = pygame.time.Clock()
    running = True
    dt = 0

    player_pos = pygame.Vector2(
        screen.get_width() / 2, screen.get_height() / 2)

    while running:
        # poll for events
        # pygame.QUIT event means the user clicked X to close your window
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # fill the screen with a color to wipe away anything from last frame
        screen.fill("purple")

        pygame.draw.circle(screen, "red", player_pos, 40)

        keys = pygame.key.get_pressed()
        if keys[pygame.K_w]:
            player_pos.y -= 300 * dt
        if keys[pygame.K_s]:
            player_pos.y += 300 * dt
        if keys[pygame.K_a]:
            player_pos.x -= 300 * dt
        if keys[pygame.K_d]:
            player_pos.x += 300 * dt

        # flip() the display to put your work on screen
        pygame.display.flip()

        # limits FPS to 60
        # dt is delta time in seconds since last frame, used for framerate-
        # independent physics.
        dt = clock.tick(60) / 1000

    pygame.quit()


def main():
    try:
        raw_config = parse_config("./maps/easy/03_basic_capacity.txt")
        config = validate_config(raw_config)
        config = join_connection(config)

        print(config)

    except (ValueError, ConfigError):
        sys.exit(1)


if __name__ == "__main__":
    main()
