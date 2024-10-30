# PingPing

PingPing is a simple tool to measure the latency between two hosts. It is written in Python and uses the MQTT protocol to send the results to a server. PingPing runs in the background as a daemon and sends the results to the server at regular intervals.

## Installation

To install PingPing, you need to have Python 3.6 or higher installed on your system.

### 1. Clone the Repository

Clone the repository to a temporary location:

```shell
git clone https://github.com/Friedjof/PingPing.git
```

### 2. Move the Project to `/opt`

Move the project to `/opt`:

```shell
sudo mv PingPing /opt/PingPing
```

Set permissions for `/opt/PingPing`:

```shell
sudo chown -R root:root /opt/PingPing
sudo chmod -R 755 /opt/PingPing
```

### 3. Create a Virtual Environment and Install Requirements

Navigate to the project directory and create a virtual environment:

```shell
cd /opt/PingPing
python3 -m venv .venv
```

Activate the virtual environment:

```shell
source .venv/bin/activate
```

Install the required packages from `requirements.txt`:

```shell
pip install -r requirements.txt
```

### 4. Create the `.env` File

In the `/opt/PingPing` directory, create a `.env` file with the following content:

```shell
MQTT_BROKER_HOST=your-mqtt-broker-host # e.g. mqtt.eclipse.org
MQTT_BROKER_PORT=your-mqtt-broker-port # e.g. 1883
MQTT_USERNAME=your-mqtt-username       # optional
MQTT_PASSWORD=your-mqtt-password       # optional
PING_INTERVAL=your-ping-interval       # in seconds (e.g. 60)
PING_COUNT=your-ping-count             # number of pings per interval (e.g. 5), the average is calculated
PING_TARGETS=your-ping-targets         # comma-separated list of targets (e.g. 'github.com,ecosia.org')
```

### 5. Configure the systemd Service

1. In the root directory of the project, you will find the `pingping.service` file. Copy it to the systemd directory:

   ```shell
   sudo cp /opt/PingPing/pingping.service /etc/systemd/system/pingping.service
   ```

2. Reload the systemd daemon and enable the service to start on boot:

   ```shell
   sudo systemctl daemon-reload
   sudo systemctl enable pingping
   sudo systemctl start pingping
   ```

### 6. MQTT Topics

The results are sent to the following MQTT topics:
- `pingping/<ip-or-hostname>/latency`: The latency in milliseconds (average of the pings)
- `pingping/<ip-or-hostname>/packet_loss`: The packet loss in percentage
- `pingping/<ip-or-hostname>/timestamp`: The timestamp of the measurement in milliseconds since epoch
- `pingping/<ip-or-hostname>/reachable`: Whether the target is reachable or not

## Development

You can set up a mosquitto broker locally for testing purposes. The broker can be started with the following command:

1. Set up your password file:
    
   ```shell
   docker run -it --rm -v $(pwd)/mosquitto/config:/mosquitto/config eclipse-mosquitto mosquitto_passwd -c /mosquitto/config/passwordfile <username>
   ```

2. Start the broker:

   ```shell
   docker compose up -d
   ```

> **Note:** To subscribe to the topics, you can use the [MQTT Explorer](https://mqtt-explorer.com/) or the `mosquitto_sub` command.

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.
