# openSenseMap Advanced for Home Assistant

> ℹ️ **Project Home:** This integration is developed and maintained on **[Codeberg](https://codeberg.org/nichu42/opensensemap-advanced)**. If you are viewing this on GitHub, this is a read-only mirror. Please submit all issues, pull requests, and contributions directly to Codeberg.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

An advanced, feature-rich custom integration for [openSenseMap](https://opensensemap.org) in Home Assistant. This integration is built entirely from scratch with zero external dependencies, designed for power users who need finer control, reliability, and the ability to upload local sensor data.

It is developed on Codeberg and mirrored to GitHub to support HACS.

---

## ✨ Features

1. **🔍 Dynamic Sensor Discovery (Zero-Configuration)**
   * *Official:* Limited to 9 pre-defined sensor types and requires translations for non-English sensor titles.
   * *Advanced:* Automatically discovers and generates Home Assistant sensor entities for **every sensor** configured on your senseBox (e.g., CO2, UV index, noise, PM, soil moisture, battery voltage). It uses your custom sensor titles and units directly from openSenseMap.

2. **🏷️ Device Class & Unit Auto-Mapping**
   * *Advanced:* Automatically detects and maps your sensors' units and titles to standard Home Assistant device classes (e.g., Temperature, Humidity, Pressure, Wind Speed, Illuminance, PM25, PM10, PM1, CO2) for correct UI icons, history graphs, and scaling.

3. **⏱️ Customizable Update Intervals**
   * *Official:* Hardcoded to pull data once every 10 minutes.
   * *Advanced:* Set your own polling frequency (e.g., once every 60 seconds) directly in the integration's Options UI.

4. **🛡️ Offline State Caching (Fallback)**
   * *Official:* Marks all sensors as `unavailable` if the API fails or connection drops.
   * *Advanced:* Opt-in to retain the **last known valid value** during API or internet outages, keeping your history graphs and automations stable.

5. **📤 Sensor Data Upload (Exporter/Push Mode)**
   * *Official:* Read-only (Pulling data).
   * *Advanced:* Bridge your local Home Assistant sensors (Zigbee, ESPHome, RTL_433, templates, etc.) directly to your openSenseMap Box.
   * *Debounced Submissions:* All updates are batched and sent in a single consolidated HTTP POST request every 5 seconds to reduce API overhead.

---

## 📦 Installation (via HACS)

1. Open **HACS** (Home Assistant Community Store).
2. Click the three dots in the top-right corner and select **Custom repositories**.
3. Paste the URL of the GitHub mirror repository:
   `https://github.com/nichu42/opensensemap-advanced`
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
5. **openSenseMap API Key**: Required if you enabled **Push Mode** (data upload). Enter the API key obtained from your openSenseMap account.
6. **Push Sensor Mappings (JSON)**: Input a JSON map of your local Home Assistant entity IDs to their corresponding openSenseMap Sensor IDs:
   ```json
   {
     "sensor.backyard_temperature": "62f77dc305b75c001bb659ff",
     "sensor.backyard_humidity": "62f77dc305b75c001bb65a00"
   }
   ```

---

## 🧑‍💻 License

Licensed under the [GNU General Public License v3 (GPLv3)](./LICENSE). Copyright (c) 2026 nichu42 <nichu42@42bit.email> and contributors.

---

## 🌍 Data, Geocoding & Attribution

### openSenseMap API
This app utilizes the open API provided by [openSenseMap](https://opensensemap.org), an open-source platform dedicated to collecting and exploring environmental sensor data from around the globe.

* **What is openSenseMap?** Originally emerged from a research project at the University of Münster (Germany), openSenseMap has grown into one of the largest citizen-operated sensor networks in the world. It provides a free platform for schools, universities, scientists, and citizen enthusiasts to publish real-time environmental measurements—such as air quality, temperature, and humidity—and share them as Open Data.
* **Who operates it?** The platform is operated and maintained by openSenseLab gGmbH, a non-profit organization based in Münster, Germany, dedicated to promoting digital sovereignty, education, and public participation in scientific environmental monitoring.
* **Support Open Data!** openSenseMap is completely free to use and relies heavily on community contributions and donations to keep its servers running and its data accessible to all. If you love the environmental insights provided in this app, please consider supporting their project:
  * **Explore:** [opensensemap.org](https://opensensemap.org)
  * **Build:** [sensebox.de](https://sensebox.de)
  * **Donate:** [Donate via Betterplace](https://www.betterplace.org/en/projects/89947-opensensemap-org-the-free-map-for-environmental-data)

---

## ⚠️ Disclaimers

### Affiliation Disclaimer
This integration is an independent project and is not affiliated with, endorsed by, or connected to openSenseMap (openSenseLab gGmbH).

### Trademark & Logo Usage
The openSenseMap logo and icon used in this integration are property of their respective owners. They are used here under nominative fair use to identify the service this integration connects to.
