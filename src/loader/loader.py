import os
import shutil
import hashlib
import sys

# Configuration
QSPI_DIR = "qspi_slots"
INTERNAL_FLASH_FILE = "internal_flash.uf2"  # renamed for clarity
MAX_SLOTS = 4

class GameSlot:
    def __init__(self, name, filename):
        self.name = name
        self.filename = filename
        self.size = os.path.getsize(filename) if os.path.exists(filename) else 0

class Loader:
    def __init__(self, qspi_dir=QSPI_DIR):
        self.qspi_dir = qspi_dir
        self.slots = []
        self.load_slots()

    def load_slots(self):
        self.slots = []
        for i in range(MAX_SLOTS):
            # Check for both .uf2 and .bin
            uf2_path = os.path.join(self.qspi_dir, f"slot{i}.uf2")
            bin_path = os.path.join(self.qspi_dir, f"slot{i}.bin")

            if os.path.exists(uf2_path):
                name = f"Game {i} (UF2)"
                self.slots.append(GameSlot(name, uf2_path))
            elif os.path.exists(bin_path):
                name = f"Game {i} (BIN)"
                self.slots.append(GameSlot(name, bin_path))
            else:
                self.slots.append(GameSlot("Empty", f"slot{i}"))

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
