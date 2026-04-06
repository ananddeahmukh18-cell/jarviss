"""
JARVIS System Control Tools
FIX: Uses config.REMOTE_MODE to bypass confirmations in bot/iPhone mode.
NEW: send_notification, get_battery_status, get_disk_space, get_network_info
"""
from __future__ import annotations
import os, platform, subprocess, sys
from datetime import datetime
from pathlib import Path
import psutil
import config   # import module so REMOTE_MODE mutations are visible

try:    import pyperclip; _CLIP = True
except: _CLIP = False
try:    import pyautogui; _GUI  = True
except: _GUI  = False


def _human(size: float) -> str:
    for u in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024: return f"{size:.1f} {u}"
        size /= 1024
    return f"{size:.1f} PB"


def _should_confirm() -> bool:
    """In REMOTE_MODE or when CONFIRM_COMMANDS=False, skip prompts."""
    return config.CONFIRM_COMMANDS and not config.REMOTE_MODE


# ── Shell commands ─────────────────────────────────────────────────

def run_command(command: str, timeout: int = 30) -> str:
    if _should_confirm():
        if input(f"\n  ⚠  Run: `{command}`? [y/N]: ").strip().lower() not in ("y", "yes"):
            return "🚫 Cancelled."
    try:
        r = subprocess.run(command, shell=True, capture_output=True,
                           text=True, timeout=timeout)
        out = []
        if r.stdout: out.append(r.stdout.strip())
        if r.stderr: out.append(f"[stderr]\n{r.stderr.strip()}")
        if r.returncode != 0: out.append(f"[exit {r.returncode}]")
        return "\n".join(out) or "✅ Done (no output)"
    except subprocess.TimeoutExpired:
        return f"⏱️ Timed out after {timeout}s"
    except Exception as e:
        return f"❌ {e}"


def open_application(app_name_or_path: str) -> str:
    system = platform.system()
    try:
        if system == "Windows":  os.startfile(app_name_or_path)
        elif system == "Darwin": subprocess.Popen(["open", app_name_or_path])
        else:                    subprocess.Popen(["xdg-open", app_name_or_path])
        return f"✅ Opened: {app_name_or_path}"
    except Exception as e:
        return f"❌ {e}"


# ── System info ────────────────────────────────────────────────────

def get_system_info() -> str:
    cpu  = psutil.cpu_percent(interval=1)
    ram  = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    bat  = psutil.sensors_battery()
    boot = datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M")
    lines = [
        "🖥️  System Status",
        f"   OS       : {platform.system()} {platform.release()} ({platform.machine()})",
        f"   Python   : {sys.version.split()[0]}",
        f"   Boot     : {boot}",
        f"   CPU      : {cpu}%  ({psutil.cpu_count()} cores)",
        f"   RAM      : {_human(ram.used)} / {_human(ram.total)}  ({ram.percent}%)",
        f"   Disk (/) : {_human(disk.used)} / {_human(disk.total)}  ({disk.percent}%)",
    ]
    if bat:
        lines.append(f"   Battery  : {bat.percent:.0f}%  {'⚡ charging' if bat.power_plugged else '🔋'}")
    procs = sorted(
        psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]),
        key=lambda p: p.info.get("cpu_percent") or 0, reverse=True
    )[:5]
    lines.append("\n   Top processes by CPU:")
    for p in procs:
        try:
            lines.append(
                f"     [{p.info['pid']:>6}]  {p.info['name']:<28}"
                f"  CPU {p.info['cpu_percent']:>5.1f}%"
                f"  RAM {p.info['memory_percent']:>4.1f}%"
            )
        except Exception:
            pass
    return "\n".join(lines)


def get_battery_status() -> str:
    """Detailed battery and power info."""
    bat = psutil.sensors_battery()
    if bat is None:
        return "🔌 No battery detected (desktop or not supported)"
    pct    = bat.percent
    plug   = bat.power_plugged
    secs   = bat.secsleft
    status = "⚡ Charging" if plug else "🔋 Discharging"

    if secs == psutil.POWER_TIME_UNLIMITED:
        time_left = "Fully charged" if plug else "Unknown"
    elif secs == psutil.POWER_TIME_UNKNOWN:
        time_left = "Calculating…"
    else:
        h, m = divmod(secs // 60, 60)
        time_left = f"{h}h {m}m remaining"

    warn = ""
    if not plug and pct < 20:
        warn = "\n   ⚠️  LOW BATTERY — please plug in!"
    elif not plug and pct < 10:
        warn = "\n   🚨 CRITICAL — plug in NOW!"

    return (f"🔋 Battery: {pct:.0f}%  {status}\n"
            f"   Time    : {time_left}"
            f"{warn}")


def get_disk_space(path: str = "/") -> str:
    """Check disk usage for any path."""
    try:
        d = psutil.disk_usage(path)
        warn = " ⚠️ LOW" if d.percent > 85 else ""
        return (f"💾 Disk: {path}\n"
                f"   Used : {_human(d.used)} / {_human(d.total)}  ({d.percent:.1f}%){warn}\n"
                f"   Free : {_human(d.free)}")
    except Exception as e:
        return f"❌ {e}"


def get_network_info() -> str:
    """Get network interfaces and connection status."""
    lines = ["🌐 Network Interfaces:"]
    for name, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family.name == "AF_INET":
                lines.append(f"   {name:<12} {addr.address}")
    # Wi-Fi SSID on Mac
    try:
        ssid = subprocess.check_output(
            ["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", "-I"],
            timeout=3, stderr=subprocess.DEVNULL
        ).decode()
        for line in ssid.splitlines():
            if " SSID:" in line:
                lines.append(f"   Wi-Fi SSID : {line.split('SSID:')[-1].strip()}")
                break
    except Exception:
        pass
    return "\n".join(lines)


def send_notification(title: str, message: str, subtitle: str = "") -> str:
    """Send a macOS native notification (shows in notification centre)."""
    if platform.system() != "Darwin":
        return "❌ Notifications only supported on macOS"
    sub_part = f'subtitle "{subtitle}"' if subtitle else ""
    script = f'display notification "{message}" with title "{title}" {sub_part}'
    try:
        subprocess.run(["osascript", "-e", script], check=True, timeout=5)
        return f"✅ Notification sent: {title}"
    except Exception as e:
        return f"❌ Notification failed: {e}"


# ── Process management ─────────────────────────────────────────────

def get_running_processes(filter_name: str = "") -> str:
    procs = []
    for p in psutil.process_iter(["pid", "name", "status", "cpu_percent", "memory_percent"]):
        try:
            if filter_name.lower() in p.info["name"].lower():
                procs.append(p.info)
        except Exception:
            pass
    if not procs:
        return f"No processes {'matching ' + repr(filter_name) if filter_name else 'found'}"
    hdr  = f"{'PID':>7}  {'Name':<32}  {'Status':<10}  {'CPU':>6}  {'RAM':>6}"
    rows = [hdr, "-" * len(hdr)]
    for p in sorted(procs, key=lambda x: x.get("cpu_percent") or 0, reverse=True)[:30]:
        rows.append(
            f"{p['pid']:>7}  {p['name']:<32}  {p['status']:<10}"
            f"  {p['cpu_percent']:>5.1f}%  {p['memory_percent']:>5.1f}%"
        )
    return "\n".join(rows)


def kill_process(pid_or_name: str) -> str:
    if not config.REMOTE_MODE:
        if input(f"\n  ⚠  Kill '{pid_or_name}'? [y/N]: ").strip().lower() not in ("y", "yes"):
            return "🚫 Cancelled."
    killed = []
    for p in psutil.process_iter(["pid", "name"]):
        try:
            if (str(p.info["pid"]) == pid_or_name
                    or p.info["name"].lower() == pid_or_name.lower()):
                p.kill()
                killed.append(f"{p.info['name']} (PID {p.info['pid']})")
        except Exception:
            pass
    return (f"✅ Killed: {', '.join(killed)}" if killed
            else f"❌ No process found: '{pid_or_name}'")


# ── Clipboard ──────────────────────────────────────────────────────

def get_clipboard() -> str:
    if not _CLIP: return "❌ pyperclip not installed"
    try:
        c = pyperclip.paste()
        return f"📋 Clipboard:\n{c}" if c else "📋 Clipboard is empty."
    except Exception as e:
        return f"❌ {e}"


def set_clipboard(text: str) -> str:
    if not _CLIP: return "❌ pyperclip not installed"
    try:
        pyperclip.copy(text)
        return f"✅ Copied to clipboard ({len(text)} chars)"
    except Exception as e:
        return f"❌ {e}"


# ── Screenshot & keyboard ──────────────────────────────────────────

def take_screenshot(save_path: str = None) -> str:
    if not _GUI: return "❌ pyautogui not installed"
    try:
        img = pyautogui.screenshot()
        if not save_path:
            save_path = str(
                Path.home() / f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            )
        img.save(save_path)
        return f"✅ Screenshot saved: {save_path}"
    except Exception as e:
        return f"❌ {e}"


def type_text(text: str) -> str:
    if not _GUI: return "❌ pyautogui not installed"
    try:
        import time
        time.sleep(1)
        pyautogui.write(text, interval=0.05)
        return f"✅ Typed {len(text)} characters"
    except Exception as e:
        return f"❌ {e}"


def press_key(key: str) -> str:
    """
    Simulate pressing a keyboard key or hotkey.
    Examples: 'enter', 'escape', 'cmd+c', 'cmd+space'
    """
    if not _GUI: return "❌ pyautogui not installed"
    try:
        if "+" in key:
            keys = [k.strip() for k in key.split("+")]
            pyautogui.hotkey(*keys)
        else:
            pyautogui.press(key)
        return f"✅ Pressed: {key}"
    except Exception as e:
        return f"❌ {e}"
