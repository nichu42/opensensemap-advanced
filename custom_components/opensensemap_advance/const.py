# Copyright (c) 2026 nichu42 and contributors <nichu42@42bit.email>
# Originally derived from Home Assistant Core (Copyright (c) The Home Assistant Authors)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# Original Home Assistant code is licensed under the Apache License 2.0.
# A copy of the Apache License 2.0 can be found in the LICENSE-APACHE file.
# Modifications made by nichu42 and contributors.

"""Constants for the openSenseMap Advanced integration."""

import logging

DOMAIN = "opensensemap_advance"

LOGGER = logging.getLogger(__name__)

CONF_STATION_ID = "station_id"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_RETAIN_STATE = "retain_state"

DEFAULT_SCAN_INTERVAL = 600

INTEGRATION_TITLE = "openSenseMap Advanced"
DEPRECATED_YAML_BREAKS_IN_VERSION = "2026.12.0"
AIR_QUALITY_DEPRECATION_BREAKS_IN_VERSION = "2027.1.0"

ERROR_CANNOT_CONNECT = "cannot_connect"
ERROR_INVALID_STATION = "invalid_station"
KNOWN_IMPORT_ABORT_REASONS = (ERROR_CANNOT_CONNECT, ERROR_INVALID_STATION)
