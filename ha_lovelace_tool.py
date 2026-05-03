import argparse
import asyncio
import copy
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
import websockets
import yaml


ROOT = Path(r"D:\SUPERBOT")
BACKUP_DIR = ROOT / "backup"
ENV_FILE = Path(r"D:\AI_PROJECTS\kniza-system-guardian\secrets\home_assistant.env")


def load_env():
    data = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if not line or line.strip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    if not data.get("HA_URL") or not data.get("HA_TOKEN"):
        raise RuntimeError("Missing HA_URL or HA_TOKEN")
    return data


def websocket_url(ha_url):
    parsed = urlparse(ha_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    netloc = parsed.netloc
    return f"{scheme}://{netloc}/api/websocket"


async def ws_call(ws, counter, msg_type, **payload):
    counter[0] += 1
    msg_id = counter[0]
    await ws.send(json.dumps({"id": msg_id, "type": msg_type, **payload}))
    while True:
        raw = await ws.recv()
        msg = json.loads(raw)
        if msg.get("id") == msg_id:
            if not msg.get("success", False):
                raise RuntimeError(f"{msg_type} failed: {msg.get('error')}")
            return msg.get("result")


async def connect():
    env = load_env()
    ws = await websockets.connect(websocket_url(env["HA_URL"]))
    first = json.loads(await ws.recv())
    if first.get("type") != "auth_required":
        raise RuntimeError(f"Unexpected websocket greeting: {first.get('type')}")
    await ws.send(json.dumps({"type": "auth", "access_token": env["HA_TOKEN"]}))
    auth = json.loads(await ws.recv())
    if auth.get("type") != "auth_ok":
        raise RuntimeError(f"Websocket auth failed: {auth.get('type')}")
    return ws, [0], env


async def list_dashboards():
    ws, counter, _ = await connect()
    async with ws:
        dashboards = await ws_call(ws, counter, "lovelace/dashboards/list")
        print(json.dumps(dashboards, ensure_ascii=False, indent=2))


async def get_config(url_path):
    ws, counter, _ = await connect()
    async with ws:
        payload = {}
        if url_path:
            payload["url_path"] = url_path
        config = await ws_call(ws, counter, "lovelace/config", **payload)
        print(json.dumps(config, ensure_ascii=False, indent=2))


async def backup_config(url_path):
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ws, counter, _ = await connect()
    async with ws:
        payload = {}
        if url_path:
            payload["url_path"] = url_path
        config = await ws_call(ws, counter, "lovelace/config", **payload)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = url_path if url_path else "default"
    out = BACKUP_DIR / f"lovelace_{suffix}_{stamp}.yaml"
    out.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(str(out))


def find_cards(node, path=None):
    if path is None:
        path = []
    found = []
    if isinstance(node, dict):
        if node.get("type") == "custom:button-card" and node.get("entity") == "sensor.time":
            found.append((path, node))
        for key, value in node.items():
            found.extend(find_cards(value, path + [key]))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(find_cards(value, path + [index]))
    return found


def replace_at_path(root, path, value):
    target = root
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value


def patched_card(old_card):
    new_card = copy.deepcopy(old_card)
    css = new_card.get("extra_styles")
    if not isinstance(css, str):
        raise RuntimeError("Target card has no extra_styles string")

    css, mark_count = re.subn(
        r"(\.mark\s*\{[^}]*?font-size:\s*)clamp\(20px,\s*2\.8vw,\s*34px\)(;[^}]*?color:\s*)#[0-9a-fA-F]{6}([^}]*?\})",
        r"\1clamp(24px, 3.36vw, 40.8px)\2#ff0000\3",
        css,
        count=1,
        flags=re.S,
    )
    css, hour_count = re.subn(
        r"(\.hour-hand\s*\{[^}]*?width:\s*)13px(;[^}]*?background:\s*)#[0-9a-fA-F]{6}([^}]*?\})",
        r"\g<1>15.6px\2#ff0000\3",
        css,
        count=1,
        flags=re.S,
    )
    css, minute_count = re.subn(
        r"(\.minute-hand\s*\{[^}]*?width:\s*)9px(;[^}]*?background:\s*)#[0-9a-fA-F]{6}([^}]*?\})",
        r"\g<1>10.8px\2#ff0000\3",
        css,
        count=1,
        flags=re.S,
    )
    if (mark_count, hour_count, minute_count) != (1, 1, 1):
        raise RuntimeError(f"CSS patch counts invalid: mark={mark_count}, hour={hour_count}, minute={minute_count}")
    new_card["extra_styles"] = css
    return new_card


def patched_marks_only_card(old_card):
    new_card = copy.deepcopy(old_card)
    css = new_card.get("extra_styles")
    if not isinstance(css, str):
        raise RuntimeError("Target card has no extra_styles string")

    mark_block = """.mark {
  position: absolute;
  font-size: clamp(30px, 4.8vw, 60px);
  font-weight: 900;
  color: #ff0000;
  line-height: 1;
  text-align: center;
}"""
    mark_12_block = """.mark-12 {
  top: 8px;
  left: 50%;
  transform: translateX(-50%);
}"""
    mark_3_block = """.mark-3 {
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
}"""
    mark_6_block = """.mark-6 {
  bottom: 8px;
  left: 50%;
  transform: translateX(-50%);
}"""
    mark_9_block = """.mark-9 {
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
}"""

    replacements = [
        (r"\.mark\s*\{[^}]*\}", mark_block),
        (r"\.mark-12\s*\{[^}]*\}", mark_12_block),
        (r"\.mark-3\s*\{[^}]*\}", mark_3_block),
        (r"\.mark-6\s*\{[^}]*\}", mark_6_block),
        (r"\.mark-9\s*\{[^}]*\}", mark_9_block),
    ]
    for pattern, replacement in replacements:
        css, count = re.subn(pattern, replacement, css, count=1, flags=re.S)
        if count != 1:
            raise RuntimeError(f"CSS block not found for pattern: {pattern}")

    new_card["extra_styles"] = css
    return new_card


async def update_card(url_path):
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ws, counter, _ = await connect()
    async with ws:
        payload = {}
        if url_path:
            payload["url_path"] = url_path
        config = await ws_call(ws, counter, "lovelace/config", **payload)
        matches = find_cards(config)
        if len(matches) != 1:
            raise RuntimeError(f"Expected exactly 1 matching card, found {len(matches)}")

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        suffix = url_path if url_path else "default"
        backup_path = BACKUP_DIR / f"lovelace_{suffix}_{stamp}.yaml"
        backup_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")

        new_config = copy.deepcopy(config)
        path, old_card = matches[0]
        replace_at_path(new_config, path, patched_card(old_card))
        yaml.safe_load(yaml.safe_dump(new_config, allow_unicode=True, sort_keys=False))

        save_payload = {"config": new_config}
        if url_path:
            save_payload["url_path"] = url_path
        await ws_call(ws, counter, "lovelace/config/save", **save_payload)
        print(json.dumps({"backup": str(backup_path), "path": path}, ensure_ascii=False))


async def update_marks_only(url_path):
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ws, counter, _ = await connect()
    async with ws:
        payload = {}
        if url_path:
            payload["url_path"] = url_path
        config = await ws_call(ws, counter, "lovelace/config", **payload)
        matches = find_cards(config)
        if len(matches) != 1:
            raise RuntimeError(f"Expected exactly 1 matching card, found {len(matches)}")

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        suffix = url_path if url_path else "default"
        backup_path = BACKUP_DIR / f"lovelace_{suffix}_marks_{stamp}.yaml"
        backup_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")

        new_config = copy.deepcopy(config)
        path, old_card = matches[0]
        replace_at_path(new_config, path, patched_marks_only_card(old_card))
        yaml.safe_load(yaml.safe_dump(new_config, allow_unicode=True, sort_keys=False))

        save_payload = {"config": new_config}
        if url_path:
            save_payload["url_path"] = url_path
        await ws_call(ws, counter, "lovelace/config/save", **save_payload)
        print(json.dumps({"backup": str(backup_path), "path": path}, ensure_ascii=False))


async def resources():
    ws, counter, _ = await connect()
    async with ws:
        result = await ws_call(ws, counter, "lovelace/resources")
        filtered = [
            item for item in result
            if "button-card" in str(item.get("url", "")).lower()
            or "button-card" in str(item.get("id", "")).lower()
        ]
        print(json.dumps(filtered, ensure_ascii=False, indent=2))


async def scan_dashboards():
    ws, counter, _ = await connect()
    async with ws:
        dashboards = await ws_call(ws, counter, "lovelace/dashboards/list")
        results = []
        for dashboard in dashboards:
            url_path = dashboard.get("url_path", "")
            payload = {}
            if url_path:
                payload["url_path"] = url_path
            try:
                config = await ws_call(ws, counter, "lovelace/config", **payload)
                matches = find_cards(config)
                if matches:
                    results.append({
                        "title": dashboard.get("title"),
                        "url_path": url_path,
                        "matches": len(matches),
                        "paths": [path for path, _ in matches],
                    })
            except Exception as exc:
                results.append({
                    "title": dashboard.get("title"),
                    "url_path": url_path,
                    "error": str(exc),
                })
        print(json.dumps(results, ensure_ascii=False, indent=2))


async def target_card(url_path):
    ws, counter, _ = await connect()
    async with ws:
        payload = {}
        if url_path:
            payload["url_path"] = url_path
        config = await ws_call(ws, counter, "lovelace/config", **payload)
        matches = find_cards(config)
        if len(matches) != 1:
            raise RuntimeError(f"Expected exactly 1 matching card, found {len(matches)}")
        path, card = matches[0]
        print(json.dumps({"path": path, "card": card}, ensure_ascii=False, indent=2))


async def verify_card(url_path):
    ws, counter, _ = await connect()
    async with ws:
        payload = {}
        if url_path:
            payload["url_path"] = url_path
        config = await ws_call(ws, counter, "lovelace/config", **payload)
        yaml.safe_load(yaml.safe_dump(config, allow_unicode=True, sort_keys=False))
        matches = find_cards(config)
        if len(matches) != 1:
            raise RuntimeError(f"Expected exactly 1 matching card, found {len(matches)}")
        path, card = matches[0]
        css = card.get("extra_styles", "")
        checks = {
            "path": path,
            "type_custom_button_card": card.get("type") == "custom:button-card",
            "entity_sensor_time": card.get("entity") == "sensor.time",
            "trigger_sensor_time": "sensor.time" in card.get("triggers_update", []),
            "trigger_jmeniny_full": "sensor.dnesni_jmeniny_full" in card.get("triggers_update", []),
            "mark_red": bool(re.search(r"\.mark\s*\{[^}]*color:\s*#ff0000", css, re.S | re.I)),
            "mark_larger": "font-size: clamp(30px, 4.8vw, 60px);" in css,
            "mark_centering": all(fragment in css for fragment in [
                "text-align: center;",
                "top: 8px;",
                "right: 14px;",
                "bottom: 8px;",
                "left: 14px;",
                "left: 50%;",
                "transform: translateX(-50%);",
                "transform: translateY(-50%);",
            ]),
            "hour_hand_red": bool(re.search(r"\.hour-hand\s*\{[^}]*background:\s*#ff0000", css, re.S | re.I)),
            "hour_hand_thicker": "width: 15.6px;" in css,
            "minute_hand_red": bool(re.search(r"\.minute-hand\s*\{[^}]*background:\s*#ff0000", css, re.S | re.I)),
            "minute_hand_thicker": "width: 10.8px;" in css,
            "digital_time_green": bool(re.search(r"\.digital-time\s*\{[^}]*color:\s*#00aa00", css, re.S | re.I)),
            "time_logic_preserved": "rotate(${hourDeg}deg)" in card.get("label", "") and "rotate(${minDeg}deg)" in card.get("label", ""),
        }
        print(json.dumps(checks, ensure_ascii=False, indent=2))


def rest_check():
    env = load_env()
    base = env["HA_URL"].rstrip("/")
    headers = {"Authorization": f"Bearer {env['HA_TOKEN']}"}
    checks = {}
    for entity in ["sensor.time", "sensor.dnesni_jmeniny_full", "update.button_card_update"]:
        response = requests.get(f"{base}/api/states/{entity}", headers=headers, timeout=10)
        checks[entity] = response.status_code if response.status_code != 200 else response.json().get("state")
    print(json.dumps(checks, ensure_ascii=False, indent=2))


def print_section(title):
    print(f"\n=== {title} ===")


async def read_all(url_path):
    print_section("dashboards")
    await list_dashboards()
    print_section("button-card resources")
    await resources()
    print_section("target card")
    await target_card(url_path)


async def verify_all(url_path):
    print_section("lovelace card verification")
    await verify_card(url_path)
    print_section("home assistant REST check")
    rest_check()


async def post_check(url_path):
    print_section("target card after write")
    await target_card(url_path)
    print_section("verification after write")
    await verify_card(url_path)
    print_section("REST check after write")
    rest_check()


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=[
        "list",
        "get",
        "backup",
        "update",
        "update-marks",
        "resources",
        "rest-check",
        "scan",
        "target-card",
        "verify",
        "read-all",
        "verify-all",
        "post-check",
    ])
    parser.add_argument("--url-path", default="")
    args = parser.parse_args()

    if args.action == "list":
        await list_dashboards()
    elif args.action == "get":
        await get_config(args.url_path)
    elif args.action == "backup":
        await backup_config(args.url_path)
    elif args.action == "update":
        await update_card(args.url_path)
    elif args.action == "update-marks":
        await update_marks_only(args.url_path)
    elif args.action == "resources":
        await resources()
    elif args.action == "scan":
        await scan_dashboards()
    elif args.action == "target-card":
        await target_card(args.url_path)
    elif args.action == "verify":
        await verify_card(args.url_path)
    elif args.action == "rest-check":
        rest_check()
    elif args.action == "read-all":
        await read_all(args.url_path)
    elif args.action == "verify-all":
        await verify_all(args.url_path)
    elif args.action == "post-check":
        await post_check(args.url_path)


if __name__ == "__main__":
    asyncio.run(main())
