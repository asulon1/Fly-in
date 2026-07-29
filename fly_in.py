# ************************************************************************* #
#                                                                           #
#                                                      :::      ::::::::    #
#  fly_in.py                                         :+:      :+:    :+:    #
#                                                  +:+ +:+         +:+      #
#  By: asulon <asulon@student.42nice.fr>         +#+  +:+       +#+         #
#                                              +#+#+#+#+#+   +#+            #
#  Created: 2026/05/21 16:39:37 by asulon          #+#    #+#               #
#  Updated: 2026/07/29 16:16:58 by asulon          ###   ########.fr        #
#                                                                           #
# ************************************************************************* #

import sys
import re
from utils import ConfigError
from simulation import start_simulation

VALID_ZONE_TYPES = {"normal", "blocked", "restricted", "priority"}
ZONE_NAME_RE = re.compile(r"^[^\s-]+$")
COORD_RE = re.compile(r"-?\d+,-?\d+")
METADATA_TOKEN_RE = re.compile(r"[A-Za-z_]+=[^\s\[\]]+")


def main():
    try:
        start_simulation("./maps/hard/03_ultimate_challenge.txt")

    except (ValueError, ConfigError):
        sys.exit(1)


if __name__ == "__main__":
    main()
