import os
import shutil
import hashlib

# Configuration
QSPI_DIR = "qspi_slots"
INTERNAL_FLASH_FILE = "internal_flash.bin"
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
            path = os.path.join(self.qspi_dir, f"slot{i}.bin")
            if os.path.exists(path):
                name = f"Game {i}"
                self.slots.append(GameSlot(name, path))
            else:
                self.slots.append(GameSlot("Empty", path))

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

        # Simulate copying to internal flash
        shutil.copyfile(slot.filename, INTERNAL_FLASH_FILE)
        print(f"Loaded '{slot.name}' to {INTERNAL_FLASH_FILE}")
        return self.verify_internal_flash(slot.filename)

    def verify_internal_flash(self, source_file):
        # Checksum comparison
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
    
    # Example: load slot 0
    loader.load_game(0)
