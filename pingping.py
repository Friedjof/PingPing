import os
import time
import subprocess
import random
import re
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from dotenv import load_dotenv
import paho.mqtt.client as mqtt


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] [%(levelname)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


class PingPing(mqtt.Client):
    def __init__(self):
        super().__init__(client_id=f"{''.join(random.choices('0123456789', k=5))}")
        load_dotenv()
        self.env_vars = {
            "broker_host": os.getenv("MQTT_BROKER_HOST", "localhost"),
            "broker_port": int(os.getenv("MQTT_BROKER_PORT", 1883)),
            "username": os.getenv("MQTT_USERNAME"),
            "password": os.getenv("MQTT_PASSWORD"),
            "ping_interval": int(os.getenv("PING_INTERVAL", 60)),
            "ping_count": int(os.getenv("PING_COUNT", 5)),
            "ping_targets": os.getenv("PING_TARGETS", "").split(","),
        }

        self.lock = threading.Lock()

        self.connect(self.env_vars["broker_host"], self.env_vars["broker_port"])
        if self.env_vars["username"] and self.env_vars["password"]:
            self.username_pw_set(self.env_vars["username"], self.env_vars["password"])

        self.loop_start()

    @staticmethod
    def parse_ping_output(ping_output):
        """Parses ping command output and extracts relevant information."""
        if not ping_output.strip():
            return {}  # Return empty dict if no output

        data = {}

        # Extract target and IP address
        target_ip_match = re.search(r"PING (\S+) \(([\d.]+)\)", ping_output)

        if target_ip_match:
            data["target"] = target_ip_match.group(1)
            data["ip"] = target_ip_match.group(2)

        # Extract transmitted, received packets, packet loss, and total time
        stats_match = re.search(r"(\d+) packets transmitted, (\d+) received, (\d+)% packet loss, time (\d+)ms",
                                ping_output)
        if stats_match:
            data["packets_transmitted"] = int(stats_match.group(1))
            data["packets_received"] = int(stats_match.group(2))
            data["packet_loss"] = int(stats_match.group(3))
            data["total_time"] = int(stats_match.group(4))

        # Extract RTT min/avg/max/mdev
        rtt_match = re.search(r"rtt min/avg/max/mdev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+) ms", ping_output)
        if rtt_match:
            data["rtt_min"] = float(rtt_match.group(1))
            data["rtt_avg"] = float(rtt_match.group(2))
            data["rtt_max"] = float(rtt_match.group(3))
            data["rtt_mdev"] = float(rtt_match.group(4))

        # Extract each ping's details: icmp_seq, ttl, and time
        pings = []
        ping_lines = re.findall(r"icmp_seq=(\d+) ttl=(\d+) time=([\d.]+) ms", ping_output)
        for line in ping_lines:
            ping_data = {
                "icmp_seq": int(line[0]),
                "ttl": int(line[1]),
                "time": float(line[2])
            }
            pings.append(ping_data)
        data["ping_details"] = pings

        return data

    def run_ping(self, target, pings):
        """Ping the target host and return average latency and packet loss."""
        try:
            result = subprocess.run(
                ["ping", "-c", str(pings), target],
                capture_output=True,
                text=True
            )
            output = result.stdout
            if "0 received" in output:
                return None, 100, None

            logging.debug(output)

            # Parse the ping output
            parsed_data = self.parse_ping_output(output)

            avg_latency = parsed_data.get("rtt_avg")
            packet_loss = parsed_data.get("packet_loss", 100)
            from_ip = parsed_data.get("ip")

            return avg_latency, packet_loss, from_ip
        except Exception as e:
            logging.error(f"Error pinging {target}: {e}")
            return None, 100, None

    def publish_ping_results(self, target, latency, packet_loss, from_ip=None):
        """Publish ping results to MQTT topics."""
        topic_base = f"pingping/{target}"
        reachable = latency is not None
        try:
            with self.lock:
                logging.debug(f"Publishing results for {target}: latency={latency}, packet_loss={packet_loss}, from_ip={from_ip}, reachable={reachable}")
                self.publish(f"{topic_base}/latency", -1 if not reachable else latency, qos=1)
                self.publish(f"{topic_base}/packet_loss", packet_loss, qos=1)
                self.publish(f"{topic_base}/from", from_ip, qos=1)
                self.publish(f"{topic_base}/reachable", reachable, qos=1)
        except Exception as e:
            logging.error(f"Error publishing to {topic_base}: {e}")

    def run(self):
        count_runs = 0

        try:
            while True:
                timer = time.time()
                with ThreadPoolExecutor() as executor:
                    futures = {executor.submit(self.run_ping, target, self.env_vars["ping_count"]): target for target in self.env_vars["ping_targets"]}
                    for future in as_completed(futures):
                        target = futures[future]
                        try:
                            latency, packet_loss, from_ip = future.result()
                            logging.info(f"{target}: latency={latency}, packet_loss={packet_loss}")
                            self.publish_ping_results(target, latency, packet_loss, from_ip)
                        except Exception as e:
                            logging.error(f"Error processing result for {target}: {e}")

                # Increment run count
                count_runs += 1

                logging.info(f"[{count_runs}] Finished in {time.time() - timer:.2f} seconds")

                time.sleep(0 if time.time() - timer > self.env_vars["ping_interval"] else self.env_vars["ping_interval"] - (time.time() - timer))
        except KeyboardInterrupt:
            logging.info("Exit, keyboard interrupt…")
            self.disconnect()
            self.loop_stop()
            logging.info("done.")


if __name__ == "__main__":
    PingPing().run()