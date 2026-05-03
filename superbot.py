import time
import subprocess
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(r"D:\SUPERBOT")
INBOX_DIR = BASE_DIR / "inbox"
OUTBOX_DIR = BASE_DIR / "outbox"
LOGS_DIR = BASE_DIR / "logs"
TASKS_DIR = BASE_DIR / "tasks"
BACKUP_DIR = BASE_DIR / "backup"
CONTEXT_DIR = BASE_DIR / "context"

INBOX = INBOX_DIR / "ukol.txt"
OUTBOX = OUTBOX_DIR / "vysledek.txt"
LOGFILE = LOGS_DIR / "superbot.log"
VIEWER = BASE_DIR / "viewer.py"

for folder in [INBOX_DIR, OUTBOX_DIR, LOGS_DIR, TASKS_DIR, BACKUP_DIR, CONTEXT_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} {msg}"
    print(msg)
    with open(LOGFILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def write_task(text):
    INBOX.write_text(text, encoding="utf-8")

def clear_result():
    OUTBOX.write_text("", encoding="utf-8")

def read_result():
    if not OUTBOX.exists():
        return ""
    return OUTBOX.read_text(encoding="utf-8", errors="ignore")

def make_claude_task(user_goal):
    return f"""
ÚKOL PRO CLAUDE CODE:

{user_goal}

PRAVIDLA:
- Pracuj v adresáři D:\\SUPERBOT.
- Nezobrazuj žádné API klíče ani tokeny.
- Pokud budeš měnit soubory, nejdřív vytvoř zálohu do D:\\SUPERBOT\\backup.
- Všechny důležité kroky vypisuj průběžně.
- Výsledek zapiš do D:\\SUPERBOT\\outbox\\vysledek.txt.
- Na konec výsledku napiš HOTOVO.

HOME ASSISTANT LOVELACE WORKFLOW:
- Tokeny a API klíče nikdy nevypisuj ani necituj ze souboru.
- Čtení Lovelace dashboardu sluč do jednoho příkazu:
  python ha_lovelace_tool.py read-all --url-path dashboard-ivca
- Ověření před změnou sluč do jednoho příkazu:
  python ha_lovelace_tool.py verify-all --url-path dashboard-ivca
- Zápisové příkazy spouštěj pouze po jednom výslovném potvrzení uživatelem:
  python ha_lovelace_tool.py update --url-path dashboard-ivca
  python ha_lovelace_tool.py update-marks --url-path dashboard-ivca
- Před každým zápisem musí existovat záloha; zápisové příkazy v ha_lovelace_tool.py ji musí vytvořit před uložením.
- Po zápisu vždy spusť kontrolu:
  python ha_lovelace_tool.py post-check --url-path dashboard-ivca
- Nikdy nemaž dashboard.
- Nikdy neměň víc než jednu cílovou kartu, pokud to uživatel výslovně nezadá.
""".strip()

def start_viewer():
    if not VIEWER.exists():
        log(f"CHYBA: viewer.py neexistuje: {VIEWER}")
        return False

    log(f"Spouštím viewer: {VIEWER}")

    subprocess.Popen(
        [sys.executable, str(VIEWER)],
        cwd=str(BASE_DIR),
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )

    log("Viewer spuštěn v samostatném okně.")
    return True

def run_task(user_goal):
    log(f"Zadaný úkol: {user_goal}")

    task = make_claude_task(user_goal)

    clear_result()
    log("Outbox vymazán.")

    write_task(task)
    log(f"Úkol zapsán do: {INBOX}")

    if not start_viewer():
        return

    log("Čekám na výsledek z Claude / vieweru...")

    last = ""
    start = time.time()
    timeout = 900

    while True:
        time.sleep(3)

        result = read_result()

        if result and result != last:
            print("")
            print("PRŮBĚŽNÝ VÝSLEDEK:")
            print(result)
            print("")
            last = result

            upper = result.upper()
            if "HOTOVO" in upper or "CHYBA" in upper or "ERROR" in upper:
                log("Úkol dokončen.")
                break

        if time.time() - start > timeout:
            log("Časový limit vypršel.")
            break

def main():
    print("=" * 60)
    print("SUPERBOT KNÍŽA")
    print("Piš úkol a stiskni ENTER")
    print("[konec] = exit")
    print("=" * 60)

    log("SUPERBOT START")

    while True:
        print("")
        print("V?ce??dkov? re?im:")
        print("[ENTER] dal?? ??dek")
        print("[prd] = odeslat")
        print("[konec] = exit")
        print("")

        lines = []

        while True:
            line = input("> ")

            if line.strip().lower() in ["prd", "odeslat"]:
                break

            if line.strip().lower() in ["konec", "exit", "quit"]:
                user_goal = "konec"
                break

            lines.append(line)

        if "user_goal" not in locals() or user_goal != "konec":
            user_goal = "\n".join(lines).strip()

        if user_goal.lower() in ["konec", "exit", "quit"]:
            log("SUPERBOT UKONČEN")
            break

        if not user_goal:
            continue

        run_task(user_goal)

if __name__ == "__main__":
    main()
