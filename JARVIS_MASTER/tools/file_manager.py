"""File-system operations for JARVIS."""
from __future__ import annotations
import os, shutil
from datetime import datetime
from pathlib import Path
from config import CONFIRM_DELETE, FILE_TYPE_MAP

def _expand(path: str) -> Path:
    return Path(os.path.expandvars(path)).expanduser().resolve()

def _confirm(prompt: str) -> bool:
    return input(f"\n  ⚠  {prompt} [y/N]: ").strip().lower() in ("y","yes")

def _human(size: int) -> str:
    for u in ("B","KB","MB","GB","TB"):
        if size < 1024: return f"{size:.1f} {u}"
        size //= 1024
    return f"{size} PB"

def list_files(path: str, show_hidden: bool = False) -> str:
    p = _expand(path)
    if not p.exists():  return f"❌ Path does not exist: {p}"
    if not p.is_dir():  return f"❌ Not a directory: {p}"
    entries = sorted(p.iterdir(), key=lambda e:(e.is_file(), e.name.lower()))
    lines = [f"📁  {p}\n"]
    for e in entries:
        if not show_hidden and e.name.startswith("."): continue
        try:
            s = e.stat()
            mtime = datetime.fromtimestamp(s.st_mtime).strftime("%Y-%m-%d %H:%M")
            icon  = "📂" if e.is_dir() else "📄"
            sz    = _human(s.st_size) if e.is_file() else "     "
            lines.append(f"  {icon}  {e.name:<45} {sz:>8}   {mtime}")
        except PermissionError:
            lines.append(f"  🔒  {e.name}  (permission denied)")
    lines.append(f"\n  {len(entries)} item(s)")
    return "\n".join(lines)

def move_file(source: str, destination: str) -> str:
    src, dst = _expand(source), _expand(destination)
    if not src.exists(): return f"❌ Source not found: {src}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    return f"✅ Moved: {src} → {dst}"

def copy_file(source: str, destination: str) -> str:
    src, dst = _expand(source), _expand(destination)
    if not src.exists(): return f"❌ Source not found: {src}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(str(src), str(dst)) if src.is_dir() else shutil.copy2(str(src), str(dst))
    return f"✅ Copied: {src} → {dst}"

def delete_file(path: str) -> str:
    p = _expand(path)
    if not p.exists(): return f"❌ Path not found: {p}"
    if CONFIRM_DELETE and not _confirm(f"Permanently delete '{p}'?"):
        return "🚫 Deletion cancelled."
    shutil.rmtree(str(p)) if p.is_dir() else p.unlink()
    return f"✅ Deleted: {p}"

def create_folder(path: str) -> str:
    _expand(path).mkdir(parents=True, exist_ok=True)
    return f"✅ Folder created: {_expand(path)}"

def rename_file(path: str, new_name: str) -> str:
    p = _expand(path)
    if not p.exists(): return f"❌ Path not found: {p}"
    dst = p.parent / new_name
    p.rename(dst)
    return f"✅ Renamed: {p.name} → {dst.name}"

def read_file(path: str, max_chars: int = 8000) -> str:
    p = _expand(path)
    if not p.exists(): return f"❌ File not found: {p}"
    if not p.is_file(): return f"❌ Not a file: {p}"
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
        if len(text) > max_chars:
            text = text[:max_chars] + f"\n\n… [truncated — {len(text)} chars total]"
        return text
    except Exception as e:
        return f"❌ Could not read: {e}"

def write_file(path: str, content: str, append: bool = False) -> str:
    p = _expand(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.open("a" if append else "w", encoding="utf-8").write(content)
    return f"✅ {'Appended' if append else 'Written'}: {p} ({len(content)} chars)"

def search_files(directory: str, pattern: str, recursive: bool = True) -> str:
    base = _expand(directory)
    if not base.is_dir(): return f"❌ Directory not found: {base}"
    matches = sorted(str(m) for m in (base.rglob(pattern) if recursive else base.glob(pattern)))
    return ("🔍 Found:\n" + "\n".join(f"  • {m}" for m in matches)) if matches \
        else f"🔍 No files matching '{pattern}' in {base}"

def get_file_info(path: str) -> str:
    p = _expand(path)
    if not p.exists(): return f"❌ Path not found: {p}"
    s = p.stat()
    return (f"📄  {p.name}\n   Path     : {p}\n"
            f"   Type     : {'Directory' if p.is_dir() else 'File'}\n"
            f"   Size     : {_human(s.st_size)}\n"
            f"   Created  : {datetime.fromtimestamp(s.st_ctime).strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"   Modified : {datetime.fromtimestamp(s.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"   Ext      : {p.suffix or '(none)'}")

def organize_folder(directory: str, dry_run: bool = False) -> str:
    base = _expand(directory)
    if not base.is_dir(): return f"❌ Directory not found: {base}"
    ext_map = {ext.lower(): folder for folder, exts in FILE_TYPE_MAP.items() for ext in exts}
    moved, skipped = [], []
    for item in base.iterdir():
        if item.is_dir() or item.name.startswith("."):
            skipped.append(item.name); continue
        folder = ext_map.get(item.suffix.lower(), "Others")
        dest_dir = base / folder
        dest = dest_dir / item.name
        if dest.exists():
            dest = dest_dir / f"{item.stem}_{int(datetime.now().timestamp())}{item.suffix}"
        if not dry_run:
            dest_dir.mkdir(exist_ok=True)
            shutil.move(str(item), str(dest))
        moved.append(f"  {item.name}  →  {folder}/")
    mode = "[DRY RUN] " if dry_run else ""
    lines = [f"📂 {mode}Organised '{base}':\n"]
    if moved: lines += ["  Moved:"] + moved
    if skipped: lines.append(f"\n  Skipped: {len(skipped)} dirs/hidden")
    lines.append(f"\n  Total: {len(moved)} files processed")
    return "\n".join(lines)
