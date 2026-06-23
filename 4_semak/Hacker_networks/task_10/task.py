import csv
import os
import shutil
import socket
import subprocess
import sys


DEFAULT_INPUT_FILE = "domains.txt"
OUTPUT_CSV = "results.csv"
MAX_HOPS = 15
HOP_TIMEOUT = 2
SCRIPT_TIMEOUT = 90


def resolve_dns(domain: str) -> str | None:
    try:
        return socket.gethostbyname(domain)
    except socket.gaierror:
        return None


def run_traceroute(ip_address: str) -> str:
    command = [
        "tracert",
        "-h", str(MAX_HOPS),
        "-w", str(HOP_TIMEOUT * 1000),
        ip_address]

    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='cp866', timeout=SCRIPT_TIMEOUT,)

        if result.stdout.strip():
            lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            return "; ".join(lines)
        return "TRACEROUTE_FAILED_OR_TIMEOUT"

    except subprocess.TimeoutExpired:
        return "TRACEROUTE_FAILED_OR_TIMEOUT"


def main():

    print("Поехали")

    with open(DEFAULT_INPUT_FILE, "r", encoding="utf-8") as infile, \
         open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as outfile:

        writer = csv.writer(outfile, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["Domain", "IP_Address", "Traceroute_Result"])

        for line in infile:
            domain = line.strip()
            print(f"Обрабатываю: {domain}")

            ip_address = resolve_dns(domain)
            if ip_address is None:
                print("DNS не вернул IPv адрес")
                writer.writerow([domain, "DNS_FAILED", "NO_IP"])
                continue
            print(f"IP: {ip_address}")

            trace_result = run_traceroute(ip_address)
            if trace_result != "TRACEROUTE_FAILED_OR_TIMEOUT":
                print("Traceroute завершён")
            else:
                print("Traceroute превысил таймаут или завершился с ошибкой")

            writer.writerow([domain, ip_address, trace_result])
            print(domain, ip_address, trace_result)

    print(f"\nРезультаты сохранены в: {OUTPUT_CSV}")
if __name__ == "__main__":
    main()