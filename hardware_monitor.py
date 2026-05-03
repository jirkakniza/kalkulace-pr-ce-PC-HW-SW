import json
import time
from pathlib import Path

import psutil
import requests

URL = "http://localhost:8085/data.json"
OUT_FILE = Path(r"D:\SUPERBOT\hardware_data.json")


def walk(node):
    if isinstance(node, dict):
        yield node
        for child in node.get("Children", []) or []:
            yield from walk(child)
    elif isinstance(node, list):
        for item in node:
            yield from walk(item)


def norm(x):
    return str(x or "").strip().lower()


def find_sensor(root, text=None, typ=None, contains=None):
    text = norm(text)
    typ = norm(typ)
    contains = [norm(x) for x in (contains or [])]

    for item in walk(root):
        item_text = norm(item.get("Text"))
        item_type = norm(item.get("Type"))
        value = item.get("Value")

        if value in [None, ""]:
            continue

        if text and item_text != text:
            continue

        if typ and item_type != typ:
            continue

        if contains and not all(x in item_text for x in contains):
            continue

        return value

    return "N/A"


def collect_hardware():
    root = requests.get(URL, timeout=5).json()

    return {
        "cpu_temp": find_sensor(root, text="Core (Tctl/Tdie)", typ="Temperature"),
        "cpu_ccd1": find_sensor(root, text="CCD1 (Tdie)", typ="Temperature"),
        "cpu_ccd2": find_sensor(root, text="CCD2 (Tdie)", typ="Temperature"),
        "cpu_usage": f"{psutil.cpu_percent()} %",
        "cpu_power": find_sensor(root, text="Package", typ="Power"),

        "gpu_temp": find_sensor(root, text="GPU Core", typ="Temperature"),
        "gpu_mem": find_sensor(root, text="GPU Memory Junction", typ="Temperature"),
        "gpu_power": find_sensor(root, text="GPU Package", typ="Power"),
        "gpu_usage": find_sensor(root, text="GPU Core", typ="Load"),

        "ram_used": f"{psutil.virtual_memory().percent} %",
        "ram_temp_dimm1": find_sensor(root, text="DIMM #1", typ="Temperature"),
        "ram_temp_dimm3": find_sensor(root, text="DIMM #3", typ="Temperature"),

        "mb_temp": find_sensor(root, text="Motherboard", typ="Temperature"),
        "nvme_temp": find_sensor(root, text="Composite Temperature", typ="Temperature"),
        "hdd_temp": find_sensor(root, text="Temperature", typ="Temperature"),
    }


def main():
    while True:
        try:
            hardware_data = collect_hardware()

            OUT_FILE.write_text(
                json.dumps(hardware_data, indent=4, ensure_ascii=False),
                encoding="utf-8"
            )

            print("HARDWARE AKTUALIZOVÁN")
            print(json.dumps(hardware_data, indent=2, ensure_ascii=False))

        except Exception as e:
            print("CHYBA HARDWARE:", e)

        time.sleep(2)


if __name__ == "__main__":
    main()