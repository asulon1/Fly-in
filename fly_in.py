# ************************************************************************* #
#                                                                           #
#                                                      :::      ::::::::    #
#  fly_in.py                                         :+:      :+:    :+:    #
#                                                  +:+ +:+         +:+      #
#  By: asulon <asulon@student.42nice.fr>         +#+  +:+       +#+         #
#                                              +#+#+#+#+#+   +#+            #
#  Created: 2026/05/21 16:39:37 by asulon          #+#    #+#               #
#  Updated: 2026/07/28 17:25:11 by asulon          ###   ########.fr        #
#                                                                           #
# ************************************************************************* #

import sys
import re
from typing import Any, Dict, List, Tuple
from collections import deque
import pygame


VALID_ZONE_TYPES = {"normal", "blocked", "restricted", "priority"}
ZONE_NAME_RE = re.compile(r"^[^\s-]+$")
COORD_RE = re.compile(r"-?\d+,-?\d+")
METADATA_TOKEN_RE = re.compile(r"[A-Za-z_]+=[^\s\[\]]+")


class ConfigError(Exception):
    def __init__(self, message: str, line_no: int = None):
        if line_no is not None:
            message = f"line {line_no}: {message}"
        super().__init__(message)


def join_connection(config: Dict):
    connections = config.get("connections")
    if connections is None:
        return config
    name_to_key = {v['name']: k for k, v in config['map'].items()}

    for point in config['map'].values():
        point['connections'] = []

    for connection in connections:
        splited_connection = connection.split(' ', 1)
        try:
            point_a, point_b = splited_connection[0].split('-')
        except ValueError:
            raise ConfigError(f"Invalid connection format: '{connection}'")

        if point_a not in name_to_key or point_b not in name_to_key:
            raise ConfigError(
                f"Connection references unknown hub in '{connection}'")

        key_a, key_b = name_to_key[point_a], name_to_key[point_b]

        metadata = []
        if len(splited_connection) > 1 and "[" in splited_connection[1]:
            bracket_content = splited_connection[1].split(
                "[", 1)[1].strip().rstrip("]")
            metadata = bracket_content.split(" ") if bracket_content else []

        config['map'][key_a]['connections'].append(
            {"to": point_b, "metadata": metadata})
        config['map'][key_b]['connections'].append(
            {"to": point_a, "metadata": metadata})

    del config['connections']

    return config


def parse_config(filename: str) -> List[Tuple[int, str, str]]:
    """Parse le fichier, retourne une liste ordonnée de (line_no, key, value)."""
    try:
        with open(filename) as file:
            lines = file.read().split("\n")
    except (FileNotFoundError, PermissionError) as error:
        raise ConfigError(f"cannot open file: {error}")

    entries = []
    hub_index = 0
    connection_index = 0

    for line_no, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ConfigError(
                f"expected 'key: value' syntax, got '{raw_line}'", line_no)

        key, value = (part.strip() for part in line.split(":", 1))
        if not key:
            raise ConfigError("empty key", line_no)

        key_lower = key.lower()
        if key_lower == "hub":
            entries.append((line_no, f"hub_{hub_index}", value))
            hub_index += 1
        elif key_lower == "connection":
            entries.append((line_no, f"connection_{connection_index}", value))
            connection_index += 1
        else:
            entries.append((line_no, key, value))

    return entries


def parse_metadata_block(raw: str, line_no: int) -> List[str]:
    raw = raw.strip()
    if raw == "":
        return []
    if not (raw.startswith("[") and raw.endswith("]")):
        raise ConfigError(
            f"invalid metadata block '{raw}', expected '[key=value ...]'", line_no)

    content = raw[1:-1].strip()
    if content == "":
        return []

    metadata = []
    for token in content.split(" "):
        if token == "":
            continue
        if not METADATA_TOKEN_RE.fullmatch(token):
            raise ConfigError(f"invalid metadata entry '{token}'", line_no)
        metadata.append(token)
    return metadata


def metadata_to_dict(metadata: List[str]) -> Dict[str, str]:
    return dict(item.split("=", 1) for item in metadata)


def validate_positive_int(raw_value: str, field_name: str, line_no: int) -> int:
    if not re.fullmatch(r"\d+", raw_value) or int(raw_value) <= 0:
        raise ConfigError(
            f"'{field_name}' must be a positive integer, got '{raw_value}'", line_no)
    return int(raw_value)


def parse_coordinate(value: str, key_name: str, line_no: int) -> Tuple[int, int]:
    if not COORD_RE.fullmatch(value):
        raise ConfigError(
            f"coordinates for '{key_name}' must be in 'x,y' integer format", line_no)
    x_raw, y_raw = value.split(",")
    return int(x_raw), int(y_raw)


def parse_hub(raw: str, line_no: int) -> Dict[str, Any]:
    parts = raw.split(" ", 1)
    name = parts[0]
    if not name:
        raise ConfigError("hub definition is missing a name", line_no)
    if not ZONE_NAME_RE.fullmatch(name):
        raise ConfigError(
            f"invalid zone name '{name}' (dashes and spaces are forbidden)", line_no)

    remainder = parts[1] if len(parts) > 1 else ""
    coord_part, _, metadata_part = remainder.partition("[")
    coord_tokens = coord_part.split()
    if len(coord_tokens) != 2:
        raise ConfigError(
            f"hub '{name}' must have exactly 2 coordinate values", line_no)

    coordinate = parse_coordinate(
        f"{coord_tokens[0]},{coord_tokens[1]}", name, line_no)

    metadata_raw = f"[{metadata_part}" if metadata_part else ""
    metadata = parse_metadata_block(metadata_raw, line_no)
    meta_dict = metadata_to_dict(metadata)

    zone_type = meta_dict.get("zone", "normal")
    if zone_type not in VALID_ZONE_TYPES:
        raise ConfigError(
            f"invalid zone type '{zone_type}' for hub '{name}' "
            f"(must be one of {sorted(VALID_ZONE_TYPES)})", line_no)

    if "max_drones" in meta_dict:
        validate_positive_int(meta_dict["max_drones"], "max_drones", line_no)

    return {
        "name": name,
        "coordinate": coordinate,
        "metadata": metadata,
        "type": zone_type,
        "_line_no": line_no,
    }


def build_adjacency(config: Dict[str, Any]) -> Dict[str, List[str]]:
    """Construit un dict {name_zone: [name_voisin, ...]} à partir de config['map']."""
    adjacency: Dict[str, List[str]] = {}
    for hub in config["map"].values():
        adjacency[hub["name"]] = [conn["to"] for conn in hub["connections"]]
    return adjacency


def find_hub_by_role(config: Dict[str, Any], role_key: str) -> Dict[str, Any]:
    return config["map"][role_key]


def validate_map(config: Dict[str, Any]) -> List[str]:
    """Valide la cohérence structurelle du graphe. Lève ConfigError sur erreur bloquante,
    retourne une liste de warnings non bloquants."""
    warnings: List[str] = []
    adjacency = build_adjacency(config)

    start = find_hub_by_role(config, "start_hub")
    end = find_hub_by_role(config, "end_hub")

    # 1. Hubs isolés (aucune connexion déclarée)
    for hub in config["map"].values():
        if not hub["connections"]:
            warnings.append(
                f"zone '{hub['name']}' has no connections (isolated)")

    # 2. end_hub atteignable depuis start_hub (BFS)
    visited = {start["name"]}
    queue = deque([start["name"]])
    while queue:
        current = queue.popleft()
        for neighbor in adjacency.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    if end["name"] not in visited:
        raise ConfigError(
            f"end zone '{end['name']}' is not reachable from start zone '{start['name']}'"
        )

    # 3. Zones jamais atteignables depuis start (mortes, mais pas bloquant en soi)
    all_names = {hub["name"] for hub in config["map"].values()}
    unreachable = all_names - visited
    for name in unreachable:
        warnings.append(f"zone '{name}' is unreachable from start (dead zone)")

    # 4. start/end de type 'blocked' : suspect mais non explicitement interdit par le sujet
    if start["type"] == "blocked":
        warnings.append(f"start zone '{start['name']}' has type 'blocked'")
    if end["type"] == "blocked":
        warnings.append(f"end zone '{end['name']}' has type 'blocked'")

    return warnings


def validate_config(entries: List[Tuple[int, str, str]]) -> Dict[str, Any]:
    if not entries:
        raise ConfigError("configuration file is empty")

    first_line_no, first_key, _ = entries[0]
    if first_key != "nb_drones":
        raise ConfigError(
            "the first line must define 'nb_drones'", first_line_no)

    config: Dict[str, Any] = {"map": {}}
    connections_raw: List[Tuple[int, str]] = []
    seen_names: Dict[str, int] = {}
    start_hub_count = 0
    end_hub_count = 0

    for line_no, key, value in entries:
        if key == "nb_drones":
            if "nb_drones" in config:
                raise ConfigError(
                    "'nb_drones' defined more than once", line_no)
            config["nb_drones"] = validate_positive_int(
                value, "nb_drones", line_no)

        elif key == "start_hub" or key == "end_hub" or key.startswith("hub_"):
            hub = parse_hub(value, line_no)
            name = hub["name"]
            if name in seen_names:
                raise ConfigError(
                    f"duplicate zone name '{name}' (already defined at line {seen_names[name]})",
                    line_no)
            seen_names[name] = line_no
            hub["connections"] = []
            config["map"][key] = hub

            if key == "start_hub":
                start_hub_count += 1
            elif key == "end_hub":
                end_hub_count += 1

        elif key.startswith("connection_"):
            connections_raw.append((line_no, value))

        else:
            raise ConfigError(f"unknown key '{key}'", line_no)

    if "nb_drones" not in config:
        raise ConfigError("missing mandatory 'nb_drones'")
    if start_hub_count != 1:
        raise ConfigError(
            f"expected exactly one 'start_hub', found {start_hub_count}")
    if end_hub_count != 1:
        raise ConfigError(
            f"expected exactly one 'end_hub', found {end_hub_count}")

    attach_connections(config, connections_raw)
    return config


def attach_connections(config: Dict[str, Any], connections_raw: List[Tuple[int, str]]) -> None:
    name_to_key = {hub["name"]: key for key, hub in config["map"].items()}
    name_to_line = {hub["name"]: hub["_line_no"]
                    for hub in config["map"].values()}
    seen_pairs = set()

    for line_no, raw in connections_raw:
        endpoints_part, _, metadata_part = raw.partition("[")
        endpoints = endpoints_part.strip()
        if "-" not in endpoints:
            raise ConfigError(
                f"invalid connection format '{raw}', expected 'zone1-zone2'", line_no)

        point_a, point_b = (p.strip() for p in endpoints.split("-", 1))

        if point_a not in name_to_key:
            raise ConfigError(
                f"connection references unknown zone '{point_a}'", line_no)
        if point_b not in name_to_key:
            raise ConfigError(
                f"connection references unknown zone '{point_b}'", line_no)
        if point_a == point_b:
            raise ConfigError(
                f"a zone cannot be connected to itself ('{point_a}')", line_no)

        # "must link only previously defined zones" -> la zone doit apparaître avant la connexion
        if name_to_line[point_a] > line_no or name_to_line[point_b] > line_no:
            raise ConfigError(
                f"connection '{point_a}-{point_b}' references a zone defined later in the file",
                line_no)

        pair_key = frozenset((point_a, point_b))
        if pair_key in seen_pairs:
            raise ConfigError(
                f"duplicate connection '{point_a}-{point_b}'", line_no)
        seen_pairs.add(pair_key)

        metadata_raw = f"[{metadata_part}" if metadata_part else ""
        metadata = parse_metadata_block(metadata_raw, line_no)
        meta_dict = metadata_to_dict(metadata)
        if "max_link_capacity" in meta_dict:
            validate_positive_int(
                meta_dict["max_link_capacity"], "max_link_capacity", line_no)

        key_a, key_b = name_to_key[point_a], name_to_key[point_b]
        config["map"][key_a]["connections"].append(
            {"to": point_b, "metadata": metadata})
        config["map"][key_b]["connections"].append(
            {"to": point_a, "metadata": metadata})


def load_and_validate(filename: str) -> Dict[str, Any]:
    entries = parse_config(filename)
    # syntaxe, unicité, types, capacités
    config = validate_config(entries)
    warnings = validate_map(config)            # cohérence du graphe
    for warning in warnings:
        print(f"Warning: {warning}")
    return config


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
        raw_config = parse_config("./maps/easy/02_simple_fork.txt")
        config = validate_config(raw_config)
        config = join_connection(config)

        print(config)

    except (ValueError, ConfigError):
        sys.exit(1)


if __name__ == "__main__":
    main()
