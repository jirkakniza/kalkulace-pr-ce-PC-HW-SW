import base64
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from openai import OpenAI

OUT_FILE = Path(r"D:\SUPERBOT\vision_result.json")
LOG_FILE = Path(r"D:\SUPERBOT\vision_module.log")

SUPPORTED = [".png", ".jpg", ".jpeg", ".webp"]


def log(text):
    LOG_FILE.write_text(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {text}\n",
        encoding="utf-8"
    )


def image_to_data_url(path: Path):
    suffix = path.suffix.lower()

    if suffix == ".png":
        mime = "image/png"
    elif suffix in [".jpg", ".jpeg"]:
        mime = "image/jpeg"
    elif suffix == ".webp":
        mime = "image/webp"
    else:
        raise ValueError("Nepodporovaný formát obrázku.")

    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def analyze_image(image_path, user_prompt=None):
    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(f"Soubor neexistuje: {path}")

    if path.suffix.lower() not in SUPPORTED:
        raise ValueError("Podporuji pouze PNG, JPG, JPEG a WEBP.")

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Chybí OPENAI_API_KEY v prostředí Windows.")

    client = OpenAI(api_key=api_key)

    prompt = user_prompt or (
        "Analyzuj tento obrázek velmi prakticky a česky. "
        "Popiš, co na něm vidíš. Pokud je to screenshot programu, "
        "najdi chyby, navrhni opravy a napiš další doporučený krok. "
        "Odpověz pouze česky."
    )

    data_url = image_to_data_url(path)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "Jsi VISION modul systému MASTER AUTOMATA. "
                    "Vždy odpovídej pouze česky. "
                    "Analyzuješ obrázky, screenshoty, GUI, grafy, dashboardy, "
                    "fotografie, technické snímky a návrhy designu."
                )
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}}
                ]
            }
        ],
        temperature=0.2
    )

    answer = response.choices[0].message.content.strip()

    result = {
        "status": "OK",
        "image": str(path),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model": "gpt-4o",
        "answer": answer
    }

    OUT_FILE.write_text(
        json.dumps(result, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )

    log("Vision analýza dokončena.")
    return result


def main():
    if len(sys.argv) < 2:
        print("Použití:")
        print(r'python D:\SUPERBOT\vision_module.py "C:\cesta\obrazek.png"')
        return

    image_path = sys.argv[1]
    prompt = " ".join(sys.argv[2:]).strip() if len(sys.argv) > 2 else None

    try:
        result = analyze_image(image_path, prompt)
        print("VISION HOTOVO")
        print(result["answer"])
    except Exception as e:
        error = {
            "status": "CHYBA",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "error": str(e)
        }
        OUT_FILE.write_text(
            json.dumps(error, indent=4, ensure_ascii=False),
            encoding="utf-8"
        )
        print("VISION CHYBA:", e)
        log(f"CHYBA: {e}")


if __name__ == "__main__":
    main()