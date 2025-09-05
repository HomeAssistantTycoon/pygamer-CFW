import os
import shutil
import hashlib
import sys
import re
import json

QSPI_DIR = "qspi_slots"
INTERNAL_FLASH_FILE = "internal_flash.uf2"
MAX_SLOTS = 4

def extract_uf2_title(path):
    """Try to extract a title from a UF2 file, fallback to None if not found."""
    try:
        with open(path, "rb") as f:
            data = f.read(64 * 1024)  # scan first 64 KB
        text = data.decode("utf-8", errors="ignore")

        # look for "name":"GameName"
        match = re.search(r'"name"\s*:\s*"([^"]+)"', text)
        if match:
            return match.group(1)

        # look for "title":"GameName"
        match = re.search(r'"title"\s*:\s*"([^"]+)"', text)
        if match:
            return match.group(1)

    except Exception:
        pass
    return None

class GameSlot:
    def __init__(self, index, filename):
        self.index = index
        self.filename = filename
        self.size = os.path.getsize(filename) if (filename and os.path.exists(filename)) else 0
        self.name = "Empty"

        if self.size > 0:
            ext = os.path.splitext(filename)[1].lower()
            base = os.path.basename(filename)
            if ext == ".uf2":
                title = extract_uf2_title(filename)
                if title:
                    self.name = f"{title} (UF2)"
                else:
                    self.name = f"{base} (UF2)"
            elif ext == ".bin":
                self.name = f"{base} (BIN)"
            else:
                self.name = base

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
                self.slots.append(GameSlot(i, ""))

    def show_menu(self):
        print("=== Game Loader Menu ===")
        for slot in self.slots:
            print(f"{slot.index}: {slot.name} ({slot.size} bytes)")
        print("========================")

    def load_game(self, slot_index):
        if slot_index < 0 or slot_index >= MAX_SLOTS:
            print("Invalid slot index!")
            return False

        slot = self.slots[slot_index]
        if slot.size == 0:
            print(f"Slot {slot_index} is empty!")
            return False

        shutil.copyfile(slot.filename, INTERNAL_FLASH_FILE)
        print(f"Loaded '{slot.name}' to {INTERNAL_FLASH_FILE}")
        return self.verify_internal_flash(slot.filename)

    def verify_internal_flash(self, source_file):
        def checksum(path):
            with open(path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        return checksum(source_file) == checksum(INTERNAL_FLASH_FILE)

if __name__ == "__main__":
    loader = Loader()
    loader.show_menu()

    choice = "0"
    if len(sys.argv) > 1:
        choice = sys.argv[1]

    if choice == "all":
        print("\nRunning loop test of all slots...\n")
        for i in range(MAX_SLOTS):
            print(f"--- Testing slot {i} ---")
            ok = loader.load_game(i)
            print("Verification successful!" if ok else "Verification failed!")
            print()
    else:
        try:
            idx = int(choice)
            ok = loader.load_game(idx)
            print("Verification successful!" if ok else "Verification failed or empty slot.")
        except ValueError:
            print("Invalid argument, must be 0–3 or 'all'")
