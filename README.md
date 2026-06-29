# openSenseMap Advanced for Home Assistant

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

An advanced, feature-rich custom integration for [openSenseMap](https://opensensemap.org) in Home Assistant. This is a hard fork of the official Home Assistant `opensensemap` integration, designed for power users who need finer control, reliability, and / or the ability to upload local sensor data.

It is designed to live as a standalone custom integration.

---

## ✨ Features

1. **⏱️ Customizable Update Intervals**
   * *Official:* Hardcoded to update once every 10 minutes.
   * *Advanced:* Set your own polling frequency (e.g., once every 70 seconds) directly in the integration's Options UI.

2. **🛡️ Offline State Caching (Fallback)**
   * *Official:* Marks all sensors as `unavailable` if the API fails or drops connection.
   * *Advanced:* Opt-in to retain the **last known valid value** during API or internet outages, keeping your history graphs and automations stable.

3. **📤 Sensor Data Upload (Exporter/Push Mode)**
   * *Official:* Read-only (Pulling data).
   * *Advanced:* Bridge your local Home Assistant sensors (Zigbee, ESPHome, RTL_433, templates, etc.) directly to your openSenseMap Box.
   * *Debounced Submissions:* All updates are batched and sent in a single consolidated HTTP request every 5 seconds to reduce API overhead.

---

## 📦 Installation (via HACS)

1. Open **HACS** (Home Assistant Community Store).
2. Click the three dots in the top-right corner and select **Custom repositories**.
3. Paste the URL of your Codeberg repository:
   `https://codeberg.org/nichu42/opensensemap-advanced`
4. Select **Integration** as the Category and click **Add**.
5. Find **openSenseMap Advanced** in HACS and click **Download**.
6. Restart Home Assistant.

---

## ⚙️ Configuration

### Add the Integration
1. Go to **Settings** ➡️ **Devices & Services** ➡️ **Add Integration**.
2. Search for **openSenseMap Advanced**.
3. Input your **Station ID** (Box ID) and click Submit.

### Adjust Advanced Options (Pull & Push)
Once added, click **Configure** on the integration card to adjust the settings:

1. **Enable Monitor Mode (Pull data)**: Check to create sensor entities representing the measurements reported by the station.
2. **Update Interval (seconds)**: Set how frequently Home Assistant pulls data from the openSenseMap API (default is `600` seconds / 10 minutes).
3. **Retain last known values on connection failure**: Check to prevent entities from going `unavailable` during internet or API dropouts.
4. **Enable Exporter Mode (Push data)**: Check if you want to upload local Home Assistant sensor states to your openSenseMap Box.
5. **API Key / Token (Optional)**: If your openSenseMap box requires authentication (a private/secure box), enter your API key here.
6. **Push Sensor Mappings (JSON)**: Input a JSON map of your local Home Assistant entity IDs to their corresponding openSenseMap Sensor IDs:
   ```json
   {
     "sensor.backyard_temperature": "62f77dc305b75c001bb659ff",
     "sensor.backyard_humidity": "62f77dc305b75c001bb65a00"
   }
   ```

---

## 🧑‍💻 Credits & License

* **Base Code:** This integration is derived from the official Home Assistant Core `opensensemap` component developed by `@AlCalzone` and the Home Assistant Core contributors under the Apache License 2.0.
* **License:** Licensed under the [GNU General Public License v3 (GPLv3)](./LICENSE). Modifications and extensions are copyright (c) 2026 nichu42 and contributors <nichu42@42bit.email>.
