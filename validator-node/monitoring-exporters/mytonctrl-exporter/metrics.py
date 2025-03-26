# Version 0.7.1

import subprocess
import re
import os
from datetime import datetime
from prometheus_client import Gauge, Info, generate_latest
from prometheus_client.core import CollectorRegistry
from http.server import BaseHTTPRequestHandler, HTTPServer

# Create registry and define base common label names in one place
registry = CollectorRegistry()
BASE_LABELS = ['validator_adnl', 'node_adnl', 'pool_address']

# Helper functions to set metrics without duplicating labels
def set_gauge_metric(metric, value, labels):
    """Sets gauge metric value with base labels."""
    metric.labels(**labels).set(value)

def set_info_metric(metric, info, labels):
    """Sets info metric by merging info with base labels."""
    combined = info.copy()
    combined.update(labels)
    metric.info(combined)

# Define metrics with base labels (they will receive custom values later)
validator_index_metric = Gauge('myton_validator_index', 'Index of the local validator', BASE_LABELS, registry=registry)
online_validators_metric = Gauge('myton_online_validators', 'Number of online validators', BASE_LABELS, registry=registry)
all_validators_metric = Gauge('myton_all_validators', 'Total number of validators', BASE_LABELS, registry=registry)
local_wallet_balance_metric = Gauge('myton_local_validator_wallet_balance', 'Balance of the local validator wallet', BASE_LABELS, registry=registry)

mytoncore_status_metric = Info('myton_mytoncore_status', 'Mytoncore status', registry=registry)
mytoncore_uptime_metric = Gauge('mytoncore_uptime', 'Mytoncore uptime in seconds', BASE_LABELS, registry=registry)
local_validator_status_metric = Info('myton_local_validator_status', 'Local validator status', registry=registry)
local_validator_uptime_metric = Gauge('myton_local_validator_uptime', 'Local validator uptime in seconds', BASE_LABELS, registry=registry)
local_validator_out_of_sync_metric = Gauge('myton_local_validator_out_of_sync', 'Local validator out of sync in seconds', BASE_LABELS, registry=registry)
local_validator_last_state_serialization_metric = Gauge('myton_local_validator_last_state_serialization', 'Blocks since last state serialization', BASE_LABELS, registry=registry)
local_validator_database_size_metric = Gauge('myton_local_validator_database_size', 'Local validator database size in GB', BASE_LABELS, registry=registry)
version_mytonctrl_metric = Info('myton_version_mytonctrl', 'MyTonCtrl version', registry=registry)
version_validator_metric = Info('myton_version_validator', 'Validator version', registry=registry)
network_info_metric = Info('myton_network_info', 'TON network name', registry=registry)
election_status_info_metric = Info('myton_election_status', 'Validator election status', registry=registry)
local_adnl_address_info_metric = Info('myton_local_adnl_address', 'Local validator ADNL address', registry=registry)
public_adnl_address_info_metric = Info('myton_public_adnl_address', 'Public node ADNL address', registry=registry)
wallet_address_info_metric = Info('myton_wallet_address', 'Local validator wallet address', registry=registry)

configurator_address_metric = Info('myton_configurator_address', 'Configurator address', registry=registry)
elector_address_metric = Info('myton_elector_address', 'Elector address', registry=registry)
validation_period_metric = Gauge('myton_validation_period', 'Validation period (seconds)', BASE_LABELS, registry=registry)
duration_of_elections_metric = Gauge('myton_duration_of_elections', 'Duration of elections (seconds)', BASE_LABELS, registry=registry)
hold_period_metric = Gauge('myton_hold_period', 'Hold period (seconds)', BASE_LABELS, registry=registry)
minimum_stake_metric = Gauge('myton_minimum_stake', 'Minimum stake', BASE_LABELS, registry=registry)
maximum_stake_metric = Gauge('myton_maximum_stake', 'Maximum stake', BASE_LABELS, registry=registry)

network_launched_metric = Gauge('myton_network_launched', 'TON network launch timestamp (Unix)', BASE_LABELS, registry=registry)
start_validation_cycle_metric = Gauge('myton_start_validation_cycle', 'Start of validation cycle (Unix)', BASE_LABELS, registry=registry)
end_validation_cycle_metric = Gauge('myton_end_validation_cycle', 'End of validation cycle (Unix)', BASE_LABELS, registry=registry)
start_elections_metric = Gauge('myton_start_elections', 'Start of elections (Unix)', BASE_LABELS, registry=registry)
end_elections_metric = Gauge('myton_end_elections', 'End of elections (Unix)', BASE_LABELS, registry=registry)
begin_next_elections_metric = Gauge('myton_begin_next_elections', 'Beginning of next elections (Unix)', BASE_LABELS, registry=registry)

myton_shardchains_metric = Gauge('myton_shardchains', 'Number of shardchains', BASE_LABELS, registry=registry)
myton_offers_current_metric = Gauge('myton_offers_current', 'Number of active offers', BASE_LABELS, registry=registry)
myton_offers_total_metric = Gauge('myton_offers_total', 'Total number of offers', BASE_LABELS, registry=registry)
myton_complaints_current_metric = Gauge('myton_complaints_current', 'Number of active complaints', BASE_LABELS, registry=registry)
myton_complaints_total_metric = Gauge('myton_complaints_total', 'Total number of complaints', BASE_LABELS, registry=registry)

load_avg_1_metric = Gauge('myton_load_average_1', 'Load average over 1 minute', BASE_LABELS, registry=registry)
load_avg_2_metric = Gauge('myton_load_average_2', 'Load average over 5 minutes', BASE_LABELS, registry=registry)
load_avg_3_metric = Gauge('myton_load_average_3', 'Load average over 15 minutes', BASE_LABELS, registry=registry)

network_load_avg_1_metric = Gauge('myton_network_load_average_1', 'Network load average #1 (Mbit/s)', BASE_LABELS, registry=registry)
network_load_avg_2_metric = Gauge('myton_network_load_average_2', 'Network load average #2 (Mbit/s)', BASE_LABELS, registry=registry)
network_load_avg_3_metric = Gauge('myton_network_load_average_3', 'Network load average #3 (Mbit/s)', BASE_LABELS, registry=registry)

ram_usage_gb_metric = Gauge('myton_ram_usage_gb', 'RAM usage (GB)', BASE_LABELS, registry=registry)
ram_usage_percent_metric = Gauge('myton_ram_usage_percent', 'RAM usage (%)', BASE_LABELS, registry=registry)
swap_usage_gb_metric = Gauge('myton_swap_usage_gb', 'SWAP usage (GB)', BASE_LABELS, registry=registry)
swap_usage_percent_metric = Gauge('myton_swap_usage_percent', 'SWAP usage (%)', BASE_LABELS, registry=registry)

# Disk metrics include an additional 'disk' label
DISK_LABELS = ['disk'] + BASE_LABELS
disk_load_average_mbs_metric = Gauge('myton_disk_load_average_mbs', 'Disk load average (MB/s)', DISK_LABELS, registry=registry)
disk_usage_percent_metric = Gauge('myton_disk_usage_percent', 'Disk usage in percent', DISK_LABELS, registry=registry)

# Regular expression to remove ANSI escape sequences
ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')

def clean_line(line):
    """Removes ANSI escape sequences from a string."""
    return ansi_escape.sub('', line)

def parse_uptime(uptime_str):
    """Parses an uptime string (e.g., '1 hours') and converts it to seconds."""
    parts = uptime_str.split()
    if len(parts) < 2:
        return 0
    try:
        time_value = int(float(parts[0]))
    except ValueError:
        return 0
    unit = parts[1]
    if 'day' in unit:
        return time_value * 86400
    elif 'hour' in unit:
        return time_value * 3600
    elif 'minute' in unit:
        return time_value * 60
    else:
        return 0

def parse_timestamp(timestamp_str):
    """Parses a timestamp string like '27.01.2025 09:31:55 UTC' into Unix time."""
    try:
        dt = datetime.strptime(timestamp_str, '%d.%m.%Y %H:%M:%S UTC')
        return int(dt.timestamp())
    except ValueError:
        return 0

def parse_disks_load(disks_line, base_labels):
    """
    Parses a string like 'sda:[0.0, 0.0%], sdb:[1.0, 2.19%]' and sets disk metrics.
    """
    disks_split = disks_line.split('],')
    for d in disks_split:
        chunk = d.strip().rstrip(']')
        if ':' not in chunk:
            continue
        disk_name, values = chunk.split(':', 1)
        disk_name = disk_name.strip()
        values = values.strip().lstrip('[')
        try:
            speed_str, perc_str = values.split(',')
            speed_val = float(speed_str.strip())
            perc_val = float(perc_str.strip().strip('%'))
            disk_load_average_mbs_metric.labels(disk=disk_name, **base_labels).set(speed_val)
            disk_usage_percent_metric.labels(disk=disk_name, **base_labels).set(perc_val)
        except ValueError:
            continue

def get_pool_address():
    """
    Runs the command 'echo "pools_list" | mytonctrl' and returns the pool address
    from the first pool entry.
    """
    try:
        pools_output = subprocess.check_output("echo 'pools_list' | mytonctrl", shell=True, universal_newlines=True)
        pools_output = clean_line(pools_output)
        pool_address = "unknown"
        header_found = False
        for line in pools_output.splitlines():
            if header_found and line.strip() != "":
                parts = line.split()
                if len(parts) >= 5:
                    pool_address = parts[-1]
                    break
            if "Name" in line and "Address" in line:
                header_found = True
        return pool_address
    except subprocess.CalledProcessError as e:
        print(f"Error running pools_list: {e}")
        return "unknown"

def collect_metrics():
    # Execute command "echo 'status' | mytonctrl" and get output
    try:
        output = subprocess.check_output("echo 'status' | mytonctrl", shell=True, universal_newlines=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing mytonctrl: {e}")
        return

    output = clean_line(output)

    # Initialize metrics dictionary
    metrics = {
        "validator_index": 0,
        "online_validators": 0,
        "all_validators": 0,
        "local_wallet_balance": 0.0,
        "network_name": "unknown",
        "election_status": "unknown",
        "local_adnl_address": "unknown",
        "public_adnl_address": "unknown",
        "wallet_address": "unknown",
        "mytoncore_status": "unknown",
        "mytoncore_uptime": 0,
        "local_validator_status": "unknown",
        "local_validator_uptime": 0,
        "local_validator_out_of_sync": 0,
        "local_validator_last_state_serialization": 0,
        "local_validator_database_size": 0.0,
        "version_mytonctrl": "unknown",
        "version_validator": "unknown",
        "configurator_address": "unknown",
        "elector_address": "unknown",
        "validation_period": 0,
        "duration_of_elections": 0,
        "hold_period": 0,
        "minimum_stake": 0.0,
        "maximum_stake": 0.0,
        "network_launched": 0,
        "start_validation_cycle": 0,
        "end_validation_cycle": 0,
        "start_elections": 0,
        "end_elections": 0,
        "begin_next_elections": 0,
        "shardchains_count": 0,
        "offers_current": 0,
        "offers_total": 0,
        "complaints_current": 0,
        "complaints_total": 0,
        "load_avg_1": 0.0,
        "load_avg_2": 0.0,
        "load_avg_3": 0.0,
        "network_load_avg_1": 0.0,
        "network_load_avg_2": 0.0,
        "network_load_avg_3": 0.0,
        "ram_usage_gb": 0.0,
        "ram_usage_percent": 0.0,
        "swap_usage_gb": 0.0,
        "swap_usage_percent": 0.0
    }

    for line in output.splitlines():
        line = clean_line(line)

        if 'Network name:' in line:
            metrics["network_name"] = line.split(':', 1)[-1].strip()
        elif 'Number of validators:' in line:
            raw = line.split(':', 1)[-1].strip()  # e.g., '28(30)'
            try:
                metrics["online_validators"] = int(raw.split('(')[0].strip())
                metrics["all_validators"] = int(raw.split('(')[1].replace(')', '').strip())
            except (IndexError, ValueError):
                pass
        elif 'Number of shardchains:' in line:
            try:
                metrics["shardchains_count"] = int(line.split(':', 1)[-1].strip())
            except ValueError:
                pass
        elif 'Number of offers:' in line:
            raw = line.split(':', 1)[-1].strip()  # e.g., '1(1)'
            try:
                metrics["offers_current"] = int(raw.split('(')[0].strip())
                metrics["offers_total"] = int(raw.split('(')[1].replace(')', '').strip())
            except (IndexError, ValueError):
                pass
        elif 'Number of complaints:' in line:
            raw = line.split(':', 1)[-1].strip()  # e.g., '0(0)'
            try:
                metrics["complaints_current"] = int(raw.split('(')[0].strip())
                metrics["complaints_total"] = int(raw.split('(')[1].replace(')', '').strip())
            except (IndexError, ValueError):
                pass
        elif 'Election status:' in line:
            metrics["election_status"] = line.split(':', 1)[-1].strip()
        elif 'Validator index:' in line:
            try:
                metrics["validator_index"] = int(line.split(':', 1)[-1].strip())
            except ValueError:
                pass
        elif 'ADNL address of local validator:' in line:
            metrics["local_adnl_address"] = line.split(':', 1)[-1].strip()
        elif 'Public ADNL address of node:' in line:
            metrics["public_adnl_address"] = line.split(':', 1)[-1].strip()
        elif 'Local validator wallet address:' in line:
            metrics["wallet_address"] = line.split(':', 1)[-1].strip()
        elif 'Local validator wallet balance:' in line:
            try:
                metrics["local_wallet_balance"] = float(line.split(':', 1)[-1].strip())
            except ValueError:
                pass
        elif 'Load average[' in line and '],' not in line:
            try:
                la_parts = line.split(':', 1)[-1].strip().split(',')
                metrics["load_avg_1"] = float(la_parts[0].strip())
                metrics["load_avg_2"] = float(la_parts[1].strip())
                metrics["load_avg_3"] = float(la_parts[2].strip())
            except (IndexError, ValueError):
                pass
        elif 'Network load average (Mbit/s):' in line:
            try:
                nla_parts = line.split(':', 1)[-1].strip().split(',')
                metrics["network_load_avg_1"] = float(nla_parts[0].strip())
                metrics["network_load_avg_2"] = float(nla_parts[1].strip())
                metrics["network_load_avg_3"] = float(nla_parts[2].strip())
            except (IndexError, ValueError):
                pass
        elif 'Memory load:' in line:
            try:
                mem_line = line.split(':', 1)[-1].strip()
                ram_part, swap_part = mem_line.split('],')
                ram_vals = ram_part.strip().lstrip('ram:[').strip().split(',')
                swap_vals = swap_part.replace('swap:[', '').strip().split(',')
                metrics["ram_usage_gb"] = float(ram_vals[0].replace('Gb', '').strip())
                metrics["ram_usage_percent"] = float(ram_vals[1].replace('%', '').strip())
                metrics["swap_usage_gb"] = float(swap_vals[0].replace('Gb', '').strip())
                metrics["swap_usage_percent"] = float(swap_vals[1].replace('%', '').strip())
            except (IndexError, ValueError):
                pass
        elif 'Mytoncore status:' in line:
            parts = line.split(':', 1)[-1].strip().split(',')
            metrics["mytoncore_status"] = parts[0].strip()
            if len(parts) > 1:
                uptime_str = ' '.join(parts[1].strip().split()[:2])
                metrics["mytoncore_uptime"] = parse_uptime(uptime_str)
        elif 'Local validator status:' in line:
            parts = line.split(':', 1)[-1].strip().split(',')
            metrics["local_validator_status"] = parts[0].strip()
            if len(parts) > 1:
                uptime_str = ' '.join(parts[1].strip().split()[:2])
                metrics["local_validator_uptime"] = parse_uptime(uptime_str)
        elif 'Local validator out of sync:' in line:
            try:
                metrics["local_validator_out_of_sync"] = int(line.split(':', 1)[-1].strip().split()[0])
            except ValueError:
                pass
        elif 'Local validator last state serialization:' in line:
            try:
                metrics["local_validator_last_state_serialization"] = int(line.split(':', 1)[-1].strip().split()[0])
            except ValueError:
                pass
        elif 'Local validator database size:' in line:
            try:
                db_size = line.split(':', 1)[-1].strip().split()[0]
                metrics["local_validator_database_size"] = float(db_size)
            except ValueError:
                pass
        elif 'Version mytonctrl:' in line:
            metrics["version_mytonctrl"] = line.split(':', 1)[-1].strip()
        elif 'Version validator:' in line:
            metrics["version_validator"] = line.split(':', 1)[-1].strip()
        elif 'Configurator address:' in line:
            metrics["configurator_address"] = line.split(':', 1)[-1].strip()
        elif 'Elector address:' in line:
            metrics["elector_address"] = line.split(':', 1)[-1].strip()
        elif 'Validation period:' in line:
            try:
                parts = line.split(',')
                metrics["validation_period"] = int(parts[0].split(':')[-1].strip())
                duration_str = parts[1].split(':')[-1].strip().split('-')[0]
                metrics["duration_of_elections"] = int(duration_str)
                metrics["hold_period"] = int(parts[2].split(':')[-1].strip())
            except (IndexError, ValueError):
                pass
        elif 'Minimum stake:' in line and 'Maximum stake:' in line:
            try:
                parts = line.split(',')
                metrics["minimum_stake"] = float(parts[0].split(':')[-1].strip())
                metrics["maximum_stake"] = float(parts[1].split(':')[-1].strip())
            except (IndexError, ValueError):
                pass
        elif 'TON network was launched:' in line:
            ts_str = line.split(':', 1)[-1].strip()
            metrics["network_launched"] = parse_timestamp(ts_str)
        elif 'Start of the validation cycle:' in line:
            ts_str = line.split(':', 1)[-1].strip()
            metrics["start_validation_cycle"] = parse_timestamp(ts_str)
        elif 'End of the validation cycle:' in line:
            ts_str = line.split(':', 1)[-1].strip()
            metrics["end_validation_cycle"] = parse_timestamp(ts_str)
        elif 'Start of elections:' in line:
            ts_str = line.split(':', 1)[-1].strip()
            metrics["start_elections"] = parse_timestamp(ts_str)
        elif 'End of elections:' in line:
            ts_str = line.split(':', 1)[-1].strip()
            metrics["end_elections"] = parse_timestamp(ts_str)
        elif 'Beginning of the next elections:' in line:
            ts_str = line.split(':', 1)[-1].strip()
            metrics["begin_next_elections"] = parse_timestamp(ts_str)

    # Get pool_address from pools_list command
    metrics["pool_address"] = get_pool_address()

    # Define base labels dict once using collected common values
    base_labels = {
        'validator_adnl': metrics["local_adnl_address"],
        'node_adnl': metrics["public_adnl_address"],
        'pool_address': metrics["pool_address"]
    }

    # Process disk metrics if present in output
    for line in output.splitlines():
        if 'Disks load average (MB/s):' in line:
            disks_str = line.split(':', 1)[-1].strip()
            parse_disks_load(disks_str, base_labels)
            break

    # Set gauge metrics using helper function
    set_gauge_metric(validator_index_metric, metrics["validator_index"], base_labels)
    set_gauge_metric(online_validators_metric, metrics["online_validators"], base_labels)
    set_gauge_metric(all_validators_metric, metrics["all_validators"], base_labels)
    set_gauge_metric(local_wallet_balance_metric, metrics["local_wallet_balance"], base_labels)
    set_gauge_metric(mytoncore_uptime_metric, metrics["mytoncore_uptime"], base_labels)
    set_gauge_metric(local_validator_uptime_metric, metrics["local_validator_uptime"], base_labels)
    set_gauge_metric(local_validator_out_of_sync_metric, metrics["local_validator_out_of_sync"], base_labels)
    set_gauge_metric(local_validator_last_state_serialization_metric, metrics["local_validator_last_state_serialization"], base_labels)
    set_gauge_metric(local_validator_database_size_metric, metrics["local_validator_database_size"], base_labels)
    set_gauge_metric(validation_period_metric, metrics["validation_period"], base_labels)
    set_gauge_metric(duration_of_elections_metric, metrics["duration_of_elections"], base_labels)
    set_gauge_metric(hold_period_metric, metrics["hold_period"], base_labels)
    set_gauge_metric(minimum_stake_metric, metrics["minimum_stake"], base_labels)
    set_gauge_metric(maximum_stake_metric, metrics["maximum_stake"], base_labels)
    set_gauge_metric(network_launched_metric, metrics["network_launched"], base_labels)
    set_gauge_metric(start_validation_cycle_metric, metrics["start_validation_cycle"], base_labels)
    set_gauge_metric(end_validation_cycle_metric, metrics["end_validation_cycle"], base_labels)
    set_gauge_metric(start_elections_metric, metrics["start_elections"], base_labels)
    set_gauge_metric(end_elections_metric, metrics["end_elections"], base_labels)
    set_gauge_metric(begin_next_elections_metric, metrics["begin_next_elections"], base_labels)
    set_gauge_metric(myton_shardchains_metric, metrics["shardchains_count"], base_labels)
    set_gauge_metric(myton_offers_current_metric, metrics["offers_current"], base_labels)
    set_gauge_metric(myton_offers_total_metric, metrics["offers_total"], base_labels)
    set_gauge_metric(myton_complaints_current_metric, metrics["complaints_current"], base_labels)
    set_gauge_metric(myton_complaints_total_metric, metrics["complaints_total"], base_labels)
    set_gauge_metric(load_avg_1_metric, metrics["load_avg_1"], base_labels)
    set_gauge_metric(load_avg_2_metric, metrics["load_avg_2"], base_labels)
    set_gauge_metric(load_avg_3_metric, metrics["load_avg_3"], base_labels)
    set_gauge_metric(network_load_avg_1_metric, metrics["network_load_avg_1"], base_labels)
    set_gauge_metric(network_load_avg_2_metric, metrics["network_load_avg_2"], base_labels)
    set_gauge_metric(network_load_avg_3_metric, metrics["network_load_avg_3"], base_labels)
    set_gauge_metric(ram_usage_gb_metric, metrics["ram_usage_gb"], base_labels)
    set_gauge_metric(ram_usage_percent_metric, metrics["ram_usage_percent"], base_labels)
    set_gauge_metric(swap_usage_gb_metric, metrics["swap_usage_gb"], base_labels)
    set_gauge_metric(swap_usage_percent_metric, metrics["swap_usage_percent"], base_labels)

    # Set info metrics using helper function
    set_info_metric(configurator_address_metric, {'address': metrics["configurator_address"]}, base_labels)
    set_info_metric(elector_address_metric, {'address': metrics["elector_address"]}, base_labels)
    set_info_metric(network_info_metric, {'name': metrics["network_name"]}, base_labels)
    set_info_metric(election_status_info_metric, {'status': metrics["election_status"]}, base_labels)
    set_info_metric(local_adnl_address_info_metric, {'address': metrics["local_adnl_address"]}, base_labels)
    set_info_metric(public_adnl_address_info_metric, {'address': metrics["public_adnl_address"]}, base_labels)
    set_info_metric(wallet_address_info_metric, {'address': metrics["wallet_address"]}, base_labels)
    set_info_metric(mytoncore_status_metric, {'status': metrics["mytoncore_status"]}, base_labels)
    set_info_metric(local_validator_status_metric, {'status': metrics["local_validator_status"]}, base_labels)
    set_info_metric(version_mytonctrl_metric, {'version': metrics["version_mytonctrl"]}, base_labels)
    set_info_metric(version_validator_metric, {'version': metrics["version_validator"]}, base_labels)

class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/metrics':
            collect_metrics()
            self.send_response(200)
            self.send_header("Content-type", "text/plain; version=0.0.4; charset=utf-8")
            self.end_headers()
            self.wfile.write(generate_latest(registry))
        else:
            self.send_response(404)
            self.end_headers()

def run(server_class=HTTPServer, handler_class=MyHandler):
    # Port and address from environment variables or defaults
    port = int(os.getenv('MTCRL_EXPORTER_PORT', '9140'))
    bind_addr = os.getenv('MTCRL_EXPORTER_BIND_ADDR', '0.0.0.0')
    server_address = (bind_addr, port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting httpd server on {bind_addr if bind_addr else '0.0.0.0'} port {port}")
    httpd.serve_forever()

if __name__ == "__main__":
    run()
