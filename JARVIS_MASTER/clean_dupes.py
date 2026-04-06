import os, hashlib, shutil
from pathlib import Path

downloads = Path.home() / "Downloads"
trash = Path.home() / ".Trash"
seen_hashes = set()
count = 0

print(f"Scanning {downloads} for duplicates. This might take a minute...")

for filepath in downloads.rglob('*'):
    # Ignore folders and hidden Mac files
    if filepath.is_file() and not filepath.name.startswith('.'):
        try:
            hasher = hashlib.md5()
            with open(filepath, 'rb') as f:
                buf = f.read(65536)
                while len(buf) > 0:
                    hasher.update(buf)
                    buf = f.read(65536)
            file_hash = hasher.hexdigest()
            
            if file_hash in seen_hashes:
                # It's a duplicate! Move safely to trash
                dest = trash / filepath.name
                suffix_counter = 1
                # Prevent overwriting files already in the trash
                while dest.exists():
                    dest = trash / f"{filepath.stem}_{suffix_counter}{filepath.suffix}"
                    suffix_counter += 1
                
                shutil.move(str(filepath), str(dest))
                print(f"🗑 Moved to Trash: {filepath.name}")
                count += 1
            else:
                seen_hashes.add(file_hash)
        except Exception:
            pass

print(f"\n✅ Done! Moved {count} duplicate files to the Trash.")
