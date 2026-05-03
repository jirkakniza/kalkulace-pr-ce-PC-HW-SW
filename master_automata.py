import tkinter as tk
from tkinter import scrolledtext
from datetime import datetime
from pathlib import Path

BASE = Path(r"D:\SUPERBOT\MASTER_AUTOMATA")
SYSTEM_PROMPT = (BASE / "system_prompt.txt").read_text(encoding="utf-8")

def log(text):
    log_file = BASE / "logs" / "master_automata.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {text}\n")

def run_command():
    command = input_box.get("1.0", tk.END).strip()
    if not command:
        return

    log("VSTUP: " + command)

    output_box.insert(tk.END, "\n=== MASTER AUTOMATA ===\n")
    output_box.insert(tk.END, "Přijatý příkaz:\n")
    output_box.insert(tk.END, command + "\n\n")
    output_box.insert(tk.END, "Stav:\n")
    output_box.insert(tk.END, "Systém je vytvořen.\n")
    output_box.insert(tk.END, "Bezpečnostní režim aktivní.\n")
    output_box.insert(tk.END, "CODEX připraven.\n")
    output_box.insert(tk.END, "GUARDIAN připraven.\n")
    output_box.insert(tk.END, "Logování aktivní.\n")
    output_box.insert(tk.END, "Další krok: napojení na OpenAI / Claude / Gemini API.\n")
    output_box.see(tk.END)

    log("VÝSTUP: Příkaz zpracován v základním režimu.")

root = tk.Tk()
root.title("MASTER AUTOMATA - SUPERTOPBOT AUTOMATA KNÍŽA")
root.geometry("1100x700")
root.configure(bg="#050816")

title = tk.Label(
    root,
    text="MASTER AUTOMATA\nSUPERTOPBOT AUTOMATA KNÍŽA",
    font=("Segoe UI", 24, "bold"),
    fg="#00e5ff",
    bg="#050816"
)
title.pack(pady=15)

frame = tk.Frame(root, bg="#050816")
frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

left = tk.Frame(frame, bg="#071427")
left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)

right = tk.Frame(frame, bg="#071427")
right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10)

tk.Label(left, text="VSTUP / IN", font=("Segoe UI", 16, "bold"), fg="#00e5ff", bg="#071427").pack(pady=8)
input_box = scrolledtext.ScrolledText(left, font=("Consolas", 13), bg="#020817", fg="white", insertbackground="white")
input_box.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

tk.Label(right, text="VÝSTUP / OUT", font=("Segoe UI", 16, "bold"), fg="#66ff66", bg="#071427").pack(pady=8)
output_box = scrolledtext.ScrolledText(right, font=("Consolas", 13), bg="#020817", fg="#66ff66", insertbackground="white")
output_box.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

button = tk.Button(
    root,
    text="SPUSTIT MASTER AUTOMATA",
    command=run_command,
    font=("Segoe UI", 15, "bold"),
    bg="#0078d7",
    fg="white",
    padx=30,
    pady=10
)
button.pack(pady=15)

log("MASTER AUTOMATA spuštěn.")
root.mainloop()
