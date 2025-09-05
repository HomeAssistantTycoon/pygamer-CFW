import os
import shutil
import hashlib
import sys
import re

# Configuration
QSPI_DIR = "qspi_slots"
INTERNAL_FLASH_FILE = "internal_flash.uf2"  # renamed for clarity
MAX_SLOTS = 4

def extract_uf2_title(path):
    """
    Try to extract the game title from a MakeCode UF2 file.
    Looks for a "name":"..." field in the first 16 KB.
    Returns None if not found.
    """
    try:
        with open(path, "rb") as f:
            data = f.read(16 * 1024)  # only scan the first 16 KB
            try:
                text = data.decode("utf-8", errors="ignore")
            except UnicodeDecodeError:
                return None
            match = re.search(r'"name"\s*:\s*"([^"]+)"', text)
            if match:
                return match.group(1)
    except Exception as e:
        print(f"Error reading {path}: {e}")
    return None

class GameSlot:
    def __init__(self, index, filename):
        self.index = index
        self.filename = filename
        self.size = os.path.getsize(filename) if os.path.exists(filename) else 0
        self.name = "Empty"
        if self.size > 0:
            if filename.endswith(".uf2"):
                title = extract_uf2_title(filename)
                if title:
                    self.name = f"{title} (UF2)"
                else:
                    self.name = f"Game {index} (UF2)"
            elif filename.endswith(".bin"):
                self.name = f"Game {index} (BIN)"

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
