import os
import shutil
import hashlib
import sys
import re
import json

# Configuration
QSPI_DIR = "qspi_slots"
INTERNAL_FLASH_FILE = "internal_flash.uf2"
MAX_SLOTS = 4

def extract_uf2_title(path):
    """
    Try multiple heuristics to extract a human-readable title from a UF2 file.
    Returns a string title or None if nothing credible is found.
    """
    try:
        size = os.path.getsize(path)
        # read up to the first 1 MiB (UF2s are typically <1MB). This is safe for CI.
        read_size = min(size, 1024 * 1024)
        with open(path, "rb") as f:
            data = f.read(read_size)
    except Exception as e:
        if os.getenv("LOADER_DEBUG"):
            print(f"DEBUG: failed to open/read {path}: {e}")
        return None

    # decode as text ignoring errors
    text = data.decode("utf-8", errors="ignore")

    # common JSON keys used for project names in MakeCode/pxt metadata
    patterns = [
        r'"name"\s*:\s*"([^"]{2,100})"',           # "name":"My Game"
        r'"projectName"\s*:\s*"([^"]{2,100})"',    # "projectName":"My Game"
        r'"title"\s*:\s*"([^"]{2,100})"',          # "title":"My Game"
        r'projectName":"([^"]{2,100})"',
        r'name":"([^"]{2,100})"'
    ]

    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            raw = m.group(1)
            # Use JSON loader to properly unescape sequences if needed
            try:
                cleaned = json.loads('"' + raw.replace('"', '\\"') + '"')
            except Exception:
                cleaned = raw
            if os.getenv("LOADER_DEBUG"):
                print(f"DEBUG: pattern match for {p!r} => {cleaned!r}")
            return cleaned

    # Try to find small JSON objects that contain "name" and parse them
    # We'll search for short {...} snippets so we don't try to parse the whole file.
    try:
        json_objs = re.findall(r'\{[^}]{0,1200}\}', text)
        for o in json_objs:
            if '"name"' in o.lower() or 'projectname' in o.lower() or '"title"' in o.lower():
                try:
                    j = json.loads(o)
                    for k in ("name", "projectName", "title"):
                        if k in j and isinstance(j[k], str) and len(j[k].strip()) > 1:
                            title = j[k].strip()
                            if os.getenv("LOADER_DEBUG"):
                                print(f"DEBUG: found JSON object title => {title!r}")
                            return title
                except Exception:
                    # parsing failed; ignore and continue
                    pass
    except Exception as e:
        if os.getenv("LOADER_DEBUG"):
            print(f"DEBUG: JSON object search error: {e}")

    # Heuristic fallback: if the UF2 contains 'makecode' or 'pxt', try to pick
    # a plausible printable substring (shortest reasonable human string).
    lower = text.lower()
    if "makecode" in lower or "pxt" in lower:
        # find candidate runs of printable characters
        candidates = re.findall(r'([A-Za-z0-9 \-\_]{4,80})', text)
        for c in candidates:
            c_strip = c.strip()
            if len(c_strip) > 3 and not c_strip.lower().startswith(("makecode", "pxt", "uf2")):
                if os.getenv("LOADER_DEBUG"):
                    print(f"DEBUG: heuristic candidate => {c_strip!r}")
                return c_strip

    # Nothing found
    if os.getenv("LOADER_DEBUG"):
        print(f"DEBUG: no title found inside {os.path.basename(path)}")
    return None


class GameSlot:
    def __init__(self, index, filename):
        self.index = index
        self.filename = filename
        self.size = os.path.getsize(filename) if (filename and os.path.exists(filename)) else 0
        self.name = "Empty"
        if self.size > 0:
            lower = filename.lower()
            if lower.endswith(".uf2"):
                title = extract_uf2_title(filename)
                if title:
                    self.name = f"{title} (UF2)"
                else:
                    # If title extraction fails, fall back to a readable default
                    self.name = f"Game {index} (UF2)"
            elif lower.endswith(".bin"):
                self.name = f"Game {index} (BIN)"
            else:
                # Unexpected extension: use basename
                self.name = os.path.basename(filename)


class Loader:
    def __init__(self, qspi_dir=QSPI_DIR):
        self.qspi_dir = qspi_dir
        self.slots = []
        self.load_slots()

    def load_slots(self):
        self.slots = []
        for i in range(MAX_SLOTS):
            uf2_path = os.path.join(self.qspi_dir, f"slot{i}.uf2")
            bin_path = os.path.join(self.qspi_dir, f"slot{i}.bin")

            if os.path.exists(uf2_path):
                self.slots.append(GameSlot(i, uf2_path))
            elif os.path.exists(bin_path):
                self.slots.append(GameSlot(i, bin_path))
            else:
                # store an empty GameSlot with no filename
                self.slots.append(GameSlot(i, ""))

    def list_games(self):
        print("Available slots:")
        for i, slot in enumerate(self.slots):
            print(f"{i}: {slot.name} ({slot.size} bytes)")

    def load_game(self, slot_index):
        if slot_index < 0 or slot_index >= MAX_SLOTS:
            print("Invalid slot index!")
            return False

        slot = self.slots[slot_index]
        if slot.size == 0:
            print(f"Slot {slot_index} is empty!")
            return False

        # Simulate copying UF2/BIN to internal flash
        shutil.copyfile(slot.filename, INTERNAL_FLASH_FILE)
        print(f"Loaded '{slot.name}' to {INTERNAL_FLASH_FILE}")
        return self.verify_internal_flash(slot.filename)

    def verify_internal_flash(self, source_file):
        def checksum(file_path):
            with open(file_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        source_hash = checksum(source_file)
        internal_hash = checksum(INTERNAL_FLASH_FILE)
        if source_hash == internal_hash:
            print("Verification successful!")
            return True
        else:
            print("Verification failed!")
            return False


if __name__ == "__main__":
    loader = Loader()
    loader.list_games()

    slot_to_load = "0"
    if len(sys.argv) > 1:
        slot_to_load = sys.argv[1]

    if slot_to_load == "all":
        print("\nRunning loop test of all slots...\n")
        for i in range(MAX_SLOTS):
            print(f"--- Testing slot {i} ---")
            loader.load_game(i)
            print()
    else:
        try:
            slot_index = int(slot_to_load)
            loader.load_game(slot_index)
        except ValueError:
            print("Invalid argument, must be 0–3 or 'all'")
