# ************************************************************************* #
#                                                                           #
#                                                      :::      ::::::::    #
#  simulation.py                                     :+:      :+:    :+:    #
#                                                  +:+ +:+         +:+      #
#  By: asulon <asulon@student.42nice.fr>         +#+  +:+       +#+         #
#                                              +#+#+#+#+#+   +#+            #
#  Created: 2026/07/29 16:04:40 by asulon          #+#    #+#               #
#  Updated: 2026/07/29 16:15:52 by asulon          ###   ########.fr        #
#                                                                           #
# ************************************************************************* #

import pygame
import sys
from utils import (validate_map, join_connection, validate_config,
                   parse_config, ConfigError)


class DroneAnim:
    def __init__(self, drone_id, start_pos, end_pos):
        self.id = drone_id
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.progress = 0.0  # 0 -> 1 sur la durée du tour

    def current_pos(self):
        x = self.start_pos[0] + (self.end_pos[0] -
                                 self.start_pos[0]) * self.progress
        y = self.start_pos[1] + (self.end_pos[1] -
                                 self.start_pos[1]) * self.progress
        return x, y


def start_simulation(filename: str):
    # --- 1. Parsing + validation (ce qu'on a fait avant) ---
    try:
        entries = parse_config(filename)
        config = validate_config(entries)
        # ou déjà fait dans validate_config selon ta version
        config = join_connection(config)
        warnings = validate_map(config)
        for warning in warnings:
            print(f"Warning: {warning}")
    except ConfigError as error:
        print(f"Error: {error}")
        sys.exit(1)

    # --- 2. Calcul de la simulation (l'algo, à part) ---
    # liste de tours, ex: [["D1-roof1", "D2-corridorA"], ...]
    turns = run_simulation(config)

    # --- 3. Affichage pygame (rejoue les tours calculés) ---

    print(config)
    render_simulation(config, turns)


def run_simulation(config):
    """
    Placeholder pour l'instant : ton algo de pathfinding viendra ici.
    Doit retourner une liste de tours, chaque tour = liste de "D<id>-<zone>".
    """
    # TODO: remplacer par ton vrai algo
    turns = [
        ["D1-junction", "D2-junction"],
        ["D1-path_a", "D2-path_b"],
        ["D1-goal", "D2-goal"],
    ]
    return turns


def to_pixel(coord, origin=(100, 100), scale=100):
    x, y = coord
    return origin[0] + x * scale, origin[1] + y * scale


def build_name_to_hub(config):
    return {hub["name"]: hub for hub in config["map"].values()}


def draw_map(screen, config, font, name_to_hub):
    colors = {"normal": (100, 100, 255), "blocked": (80, 80, 80),
              "restricted": (255, 150, 0), "priority": (0, 200, 100)}

    for hub in config["map"].values():
        pos_a = to_pixel(hub["coordinate"])
        for conn in hub["connections"]:
            neighbor = name_to_hub[conn["to"]]
            pos_b = to_pixel(neighbor["coordinate"])
            pygame.draw.line(screen, (150, 150, 150), pos_a, pos_b, 2)

    for hub in config["map"].values():
        pos = to_pixel(hub["coordinate"])
        pygame.draw.circle(screen, colors[hub["type"]], pos, 20)
        label = font.render(hub["name"], True, (255, 255, 255))
        screen.blit(label, (pos[0] - 20, pos[1] + 25))


def draw_drones(screen, font, drone_positions):
    for drone_id, pos in drone_positions.items():
        pygame.draw.circle(screen, (255, 0, 0), (int(pos[0]), int(pos[1])), 10)
        label = font.render(drone_id, True, (255, 255, 0))
        screen.blit(label, (pos[0] - 10, pos[1] - 30))


def render_simulation(config, turns):
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Fly-in Drones")
    font = pygame.font.SysFont(None, 20)
    clock = pygame.time.Clock()
    name_to_hub = build_name_to_hub(config)

    # position pixel actuelle de chaque drone, initialisée sur start_hub
    start_hub = config["map"]["start_hub"]
    start_pos = to_pixel(start_hub["coordinate"])
    drone_positions = {
        f"D{i+1}": start_pos for i in range(config["nb_drones"])}

    turn_index = 0
    # avancement de l'interpolation dans le tour courant (0 -> 1)
    progress = 0.0
    turn_duration = 800      # durée d'un tour en millisecondes
    current_moves = {}       # {drone_id: (pos_depart, pos_arrivee)}

    running = True
    while running:
        dt = clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # démarrer un nouveau tour si besoin
        if not current_moves and turn_index < len(turns):
            for move in turns[turn_index]:
                drone_id, zone_name = move.split("-", 1)
                start = drone_positions[drone_id]
                end = to_pixel(name_to_hub[zone_name]["coordinate"])
                current_moves[drone_id] = (start, end)
            progress = 0.0

        # avancer l'interpolation du tour en cours
        if current_moves:
            progress += dt / turn_duration
            if progress >= 1.0:
                progress = 1.0

            for drone_id, (start, end) in current_moves.items():
                x = start[0] + (end[0] - start[0]) * progress
                y = start[1] + (end[1] - start[1]) * progress
                drone_positions[drone_id] = (x, y)

            if progress >= 1.0:
                current_moves = {}
                turn_index += 1

        # dessin
        screen.fill((30, 30, 30))
        draw_map(screen, config, font, name_to_hub)
        draw_drones(screen, font, drone_positions)
        pygame.display.flip()

        if turn_index >= len(turns) and not current_moves:
            running = False  # simulation terminée, laisse la fenêtre encore un peu si tu veux

    pygame.quit()
