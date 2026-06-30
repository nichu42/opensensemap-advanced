# Copyright (c) 2026 nichu42 <nichu42@42bit.email> and contributors
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

"""Constants for the openSenseMap Advanced integration."""

import logging

DOMAIN = "opensensemap_advanced"
LOGGER = logging.getLogger(__name__)

CONF_STATION_ID = "station_id"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_RETAIN_STATE = "retain_state"
CONF_PUSH_INTERVAL = "push_interval"

DEFAULT_SCAN_INTERVAL = 60
DEFAULT_PUSH_INTERVAL = 60

# Error messages for translation mapping
ERROR_CANNOT_CONNECT = "cannot_connect"
ERROR_INVALID_STATION = "invalid_station"
ERROR_INVALID_MAPPINGS = "invalid_mappings"
