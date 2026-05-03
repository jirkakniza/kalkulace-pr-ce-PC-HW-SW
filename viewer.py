import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

import subprocess
import threading
import time
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

ROOT = Path(r"D:\SUPERBOT")
INBOX = ROOT / "inbox" / "ukol.txt"
OUTBOX = ROOT / "outbox" / "vysledek.txt"
LOGS = ROOT / "logs"
LOG_FILE = LOGS / "viewer.log"

GUARDIAN_OUTBOX = Path(r"D:\AI_PROJECTS\kniza-system-guardian\outbox")
GUARDIAN_SUMMARY = GUARDIAN_OUTBOX / "home_assistant_entities_summary.txt"
GUARDIAN_IMPORTANT = GUARDIAN_OUTBOX / "home_assistant_important_entities.txt"

CLAUDE_PATH = r"C:\Users\PC\.local\bin\claude.exe"

LOGS.mkdir(parents=True, exist_ok=True)
OUTBOX.parent.mkdir(parents=True, exist_ok=True)
INBOX.parent.mkdir(parents=True, exist_ok=True)

class ViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SUPERBOT LIVE VIEWER")
        self.root.geometry("1200x720")

        self.text = ScrolledText(
            root,
            bg="black",
            fg="#00ff66",
            insertbackground="white",
            font=("Consolas", 11)
        )
        self.text.pack(fill="both", expand=True)

        self.process = None
        self.stdout_lines = []
        self.stderr_lines = []

        self.write("SUPERBOT LIVE VIEWER")
        self.write("=" * 60)
        self.write("Viewer spuštěn.")
        self.write("Režim: Claude první, při chybě fallback na GPT + Guardian data.")
        self.write("")

        self.run_claude_task()

    def write(self, message):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {message}"

        self.text.insert(tk.END, line + "\n")
        self.text.see(tk.END)

        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")

        self.root.update()

    def load_task(self):
        if not INBOX.exists():
            return ""
        return INBOX.read_text(encoding="utf-8", errors="ignore").strip()

    def load_guardian_context(self):
        parts = []

        if GUARDIAN_SUMMARY.exists():
            txt = GUARDIAN_SUMMARY.read_text(encoding="utf-8", errors="ignore")
            parts.append("=== GUARDIAN HOME ASSISTANT SUMMARY ===")
            parts.append(txt[:12000])
        else:
            parts.append("Guardian summary soubor nenalezen.")

        if GUARDIAN_IMPORTANT.exists():
            txt = GUARDIAN_IMPORTANT.read_text(encoding="utf-8", errors="ignore")
            parts.append("\n=== GUARDIAN IMPORTANT ENTITIES ===")
            parts.append(txt[:16000])
        else:
            parts.append("Guardian important entities soubor nenalezen.")

        return "\n".join(parts)

    def run_claude_task(self):
        task = self.load_task()

        if not task:
            self.write("CHYBA: Soubor s úkolem je prázdný nebo neexistuje.")
            self.write(str(INBOX))
            return

        self.write("Načten úkol:")
        self.write("-" * 60)
        for line in task.splitlines():
            self.write(line)
        self.write("-" * 60)
        self.write("")

        claude_prompt = f"""
Pracuj jako Claude Code pro lokálního Superbota.

Přečti a splň tento úkol:

{task}

Povinná pravidla:
- Pracuj v adresáři D:\\SUPERBOT.
- Nezobrazuj žádné API klíče ani tokeny.
- Pokud měníš soubory, nejdřív vytvoř zálohu do D:\\SUPERBOT\\backup.
- Všechny důležité kroky piš do stdout.
- Výsledek vždy zapiš do D:\\SUPERBOT\\outbox\\vysledek.txt.
- Na konec výsledku napiš HOTOVO.

Home Assistant Lovelace workflow:
- Čtecí příkazy sluč do jednoho bezpečného kroku:
  python ha_lovelace_tool.py read-all --url-path dashboard-ivca
- Ověřovací příkazy sluč do jednoho bezpečného kroku:
  python ha_lovelace_tool.py verify-all --url-path dashboard-ivca
- Zápis do Home Assistantu proveď jen po jednom výslovném potvrzení uživatelem:
  python ha_lovelace_tool.py update --url-path dashboard-ivca
  python ha_lovelace_tool.py update-marks --url-path dashboard-ivca
- Po zápisu vždy spusť:
  python ha_lovelace_tool.py post-check --url-path dashboard-ivca
- Nikdy nemaž dashboard.
- Nikdy neměň víc než jednu cílovou kartu, pokud to uživatel výslovně nezadá.
"""

        command = [
            CLAUDE_PATH,
            "-p",
            claude_prompt,
            "--output-format",
            "text"
        ]

        self.write("Spouštím Claude CLI:")
        self.write(" ".join(command[:2]) + " [PROMPT_SKRYT] --output-format text")
        self.write("")

        try:
            self.process = subprocess.Popen(
                command,
                cwd=str(ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace"
            )

            self.write(f"PID procesu: {self.process.pid}")

            threading.Thread(target=self.read_stdout, daemon=True).start()
            threading.Thread(target=self.read_stderr, daemon=True).start()
            threading.Thread(target=self.watchdog, daemon=True).start()

        except Exception as e:
            self.write(f"CHYBA spuštění Claude: {e}")
            self.run_gpt_fallback(task, f"Claude se nespustil: {e}")

    def read_stdout(self):
        try:
            for line in self.process.stdout:
                clean = line.rstrip()
                if clean:
                    self.stdout_lines.append(clean)
                    self.write(f"STDOUT: {clean}")
        except Exception as e:
            self.write(f"CHYBA čtení STDOUT: {e}")

    def read_stderr(self):
        try:
            for line in self.process.stderr:
                clean = line.rstrip()
                if clean:
                    self.stderr_lines.append(clean)
                    self.write(f"STDERR: {clean}")
        except Exception as e:
            self.write(f"CHYBA čtení STDERR: {e}")

    def watchdog(self):
        start = time.time()

        while True:
            if self.process.poll() is not None:
                self.write("")
                self.write(f"Proces Claude ukončen. Return code: {self.process.returncode}")

                result = ""
                if OUTBOX.exists():
                    result = OUTBOX.read_text(encoding="utf-8", errors="ignore").strip()

                combined = "\n".join(self.stdout_lines + self.stderr_lines).lower()

                if result:
                    self.write("")
                    self.write("VÝSLEDEK Z OUTBOXU:")
                    self.write("=" * 60)
                    for line in result.splitlines():
                        self.write(line)
                    break

                if self.process.returncode != 0 or "out of extra usage" in combined or "usage limit" in combined:
                    self.write("")
                    self.write("Claude selhal nebo má limit. Spouštím fallback GPT s Guardian daty.")
                    self.run_gpt_fallback(self.load_task(), combined)
                    break

                self.write("OUTBOX existuje, ale je prázdný.")
                break

            elapsed = int(time.time() - start)
            self.write(f"Claude stále běží... {elapsed} s")
            time.sleep(5)

    def run_gpt_fallback(self, task, reason):
        self.write("")
        self.write("GPT FALLBACK + GUARDIAN DATA")
        self.write("=" * 60)

        api_key = os.getenv("OPENAI_API_KEY")

        guardian_context = self.load_guardian_context()

        if not api_key:
            msg = (
                "GPT fallback nelze spustit: chybí OPENAI_API_KEY.\n\n"
                "Claude výstup / důvod:\n"
                f"{reason}\n\n"
                "Guardian data:\n"
                f"{guardian_context}\n\n"
                "HOTOVO"
            )
            OUTBOX.write_text(msg, encoding="utf-8")
            self.write("CHYBA: Chybí OPENAI_API_KEY.")
            self.write("Výsledek zapsán do outboxu jako chybový fallback.")
            return

        try:
            from openai import OpenAI

            self.write("OpenAI API klíč nalezen.")
            self.write("Načítám data z Guardianu.")
            self.write("Spouštím GPT fallback...")

            client = OpenAI(api_key=api_key)

            prompt = f"""
Jsi záložní AI pro systém SUPERBOT KNÍŽA.

Claude selhal nebo má limit.

DŮVOD SELHÁNÍ CLAUDE:
{reason}

ÚKOL:
{task}

LOKÁLNÍ DATA Z GUARDIANU / HOME ASSISTANTU:
{guardian_context}

Pravidla:
- Odpověz česky.
- Nezobrazuj API klíče ani tokeny.
- Neprováděj přímé změny v systému.
- Pracuj pouze z dodaných dat.
- Pokud data nestačí, jasně napiš, co chybí.
- Napiš praktický výsledek nebo další krok.
- Výsledek ukonči slovem HOTOVO.
"""

            response = client.responses.create(
                model="gpt-5.5",
                input=prompt
            )

            output = response.output_text.strip()
            if "HOTOVO" not in output.upper():
                output += "\n\nHOTOVO"

            OUTBOX.write_text(output, encoding="utf-8")

            self.write("")
            self.write("VÝSLEDEK GPT FALLBACKU:")
            self.write("=" * 60)
            for line in output.splitlines():
                self.write(line)

        except Exception as e:
            msg = (
                "GPT fallback selhal.\n\n"
                f"Chyba: {e}\n\n"
                "HOTOVO"
            )
            OUTBOX.write_text(msg, encoding="utf-8")
            self.write(f"CHYBA GPT fallbacku: {e}")

root = tk.Tk()
app = ViewerApp(root)
root.mainloop()
