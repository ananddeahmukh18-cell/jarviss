"""JARVIS — Main entry point. Rich terminal UI with voice support."""
from __future__ import annotations
import sys, threading, time
from queue import Empty, Queue

from rich import box
from rich.align import Align
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from assistant import JarvisAssistant
from config import JARVIS_NAME, MODEL, VOICE_ENABLED
from voice_engine import VoiceEngine

console = Console()

BANNER = r"""
     ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
     ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
     ██║███████║██████╔╝██║   ██║██║███████╗
██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
 ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
"""

TOOL_ICONS = {
    "list_files":"📁","move_file":"📦","copy_file":"📋","delete_file":"🗑 ",
    "create_folder":"📂","rename_file":"✏️ ","read_file":"📖","write_file":"📝",
    "search_files":"🔍","get_file_info":"ℹ️ ","organize_folder":"🗂 ",
    "run_command":"💻","open_application":"🚀","get_system_info":"🖥 ",
    "get_running_processes":"⚙️ ","kill_process":"💀","take_screenshot":"📸",
    "type_text":"⌨️ ","get_clipboard":"📋","set_clipboard":"📋",
    "web_search":"🌐","fetch_url":"🔗","get_weather":"🌤 ","get_ip_info":"🌍",
}

def _banner():
    console.print()
    console.print(Panel(
        Align.center(Text(BANNER.strip(), style="bold cyan") +
                     Text("\n  Just A Rather Very Intelligent System", style="dim cyan")),
        border_style="cyan", padding=(1,4)))
    console.print()

def _help():
    t = Table(show_header=False, box=box.SIMPLE, padding=(0,2))
    t.add_column("Cmd",  style="bold yellow")
    t.add_column("Desc", style="dim")
    for c,d in [("/help","Show commands"),("/status","System info"),("/history","Chat history"),
                ("/clear","Clear screen"),("/reset","Reset memory"),
                ("/voice on","Enable voice"),("/voice off","Disable voice"),("/exit","Quit")]:
        t.add_row(c,d)
    console.print(Panel(t, title="[bold]Commands[/bold]", border_style="yellow"))

def _spinner(stop: threading.Event):
    frames = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    i = 0
    while not stop.is_set():
        sys.stdout.write(f"\r  \033[36m{frames[i%len(frames)]}\033[0m  \033[2mThinking …\033[0m")
        sys.stdout.flush()
        time.sleep(0.08); i += 1
    sys.stdout.write("\r" + " "*40 + "\r"); sys.stdout.flush()


class VoiceThread(threading.Thread):
    def __init__(self, voice: VoiceEngine, q: Queue):
        super().__init__(daemon=True)
        self._v, self._q = voice, q
    def run(self):
        self._v.listen_continuous(lambda t: self._q.put(("voice", t)))
    def stop(self):
        self._v.stop_continuous()


class JarvisApp:
    def __init__(self):
        _banner()
        console.print(f"  Booting [bold cyan]{JARVIS_NAME}[/bold cyan]  ·  "
                      f"[dim]model: {MODEL}[/dim]\n")
        try:
            self._brain = JarvisAssistant()
        except ValueError as e:
            console.print(f"\n[bold red]  ✘  {e}[/bold red]\n"); sys.exit(1)

        self._voice        = VoiceEngine()
        self._voice_on     = VOICE_ENABLED and (self._voice.stt_available or self._voice.tts_available)
        self._q: Queue     = Queue()
        self._vthread      = None

        if self._voice_on and self._voice.stt_available:
            self._start_voice()
            console.print("  [green]✔[/green]  Voice [bold]ACTIVE[/bold] — speak anytime\n")
        else:
            console.print("  [dim]◌  Voice off — text mode[/dim]\n")

        console.print("  Type [bold yellow]/help[/bold yellow] for commands.\n")
        console.print(Rule(style="dim cyan"))

    def _start_voice(self):
        self._vthread = VoiceThread(self._voice, self._q)
        self._vthread.start()

    def _stop_voice(self):
        if self._vthread:
            self._vthread.stop(); self._vthread = None

    def _get_input(self) -> tuple[str,str]:
        result, done = [], threading.Event()
        def _stdin():
            try:    result.append(("text", input("\n  [You] › ").strip()))
            except: result.append(("text", "/exit"))
            finally: done.set()
        threading.Thread(target=_stdin, daemon=True).start()
        while not done.is_set():
            try:
                item = self._q.get(timeout=0.2)
                if item: done.set(); result.append(item); break
            except Empty: pass
        return result[0] if result else ("text","")

    def _on_call(self, name, inputs):
        icon = TOOL_ICONS.get(name,"🔧")
        summary = ", ".join(f"{k}={repr(v)[:35]}" for k,v in inputs.items())
        console.print(f"\n  {icon}  [bold yellow]{name}[/bold yellow]  [dim]{summary}[/dim]")

    def _on_result(self, name, result):
        lines = result.splitlines()
        preview = "\n".join(lines[:2]) + (" …" if len(lines)>2 else "")
        console.print(f"     [dim green]↳ {preview}[/dim green]")

    def _show(self, text):
        console.print()
        console.print(Panel(Markdown(text),
            title=f"[bold cyan]{JARVIS_NAME}[/bold cyan]",
            border_style="cyan", padding=(0,2)))
        if self._voice_on and self._voice.tts_available:
            self._voice.speak(text.replace("**","").replace("*","").replace("`",""))

    def _cmd(self, raw: str) -> bool:
        cmd = raw.strip().lower()
        if cmd in ("/exit","/quit","/q"):
            console.print(f"\n  [cyan]{JARVIS_NAME}:[/cyan] Goodbye.\n")
            if self._voice_on: self._voice.speak("Goodbye.")
            self._stop_voice(); return False
        elif cmd == "/help":    _help()
        elif cmd == "/clear":   console.clear(); _banner()
        elif cmd == "/reset":   self._brain.reset(); console.print("  [green]✔[/green]  Memory cleared.\n")
        elif cmd == "/status":
            from tools.system_control import get_system_info
            console.print(Panel(get_system_info(), title="System Status", border_style="green"))
        elif cmd == "/history":
            h = self._brain._history
            if not h: console.print("  [dim]No history.[/dim]")
            for m in h[-10:]:
                role = m.get("role","?")
                content = m.get("content","")
                if isinstance(content, list):
                    content = " ".join(b.get("text","") for b in content
                                       if isinstance(b,dict) and b.get("type")=="text")
                col = "cyan" if role=="assistant" else "white"
                console.print(f"  [{col}]{role.upper():12}[/{col}]  {str(content)[:110]}")
        elif cmd.startswith("/voice"):
            parts = cmd.split()
            if len(parts)==2 and parts[1]=="on":
                self._voice_on = True
                if self._voice.stt_available and not self._vthread: self._start_voice()
                console.print("  [green]✔[/green]  Voice on.\n")
            elif len(parts)==2 and parts[1]=="off":
                self._voice_on = False; self._stop_voice()
                console.print("  [dim]◌  Voice off.[/dim]\n")
            else: console.print("  Usage: /voice on | /voice off\n")
        else: console.print(f"  [dim]Unknown: {cmd}  (type /help)[/dim]\n")
        return True

    def run(self):
        while True:
            try:
                console.print(f"\n  [bold white]You[/bold white] › ", end="")
                src, txt = self._get_input()
                if not txt: continue
                if src == "voice":
                    console.print(f"  [bold white]You[/bold white] › "
                                  f"[italic]{txt}[/italic]  [dim](voice)[/dim]")
                if txt.startswith("/"):
                    if not self._cmd(txt): break
                    continue
                stop = threading.Event()
                st = threading.Thread(target=_spinner, args=(stop,), daemon=True)
                st.start()
                try:
                    reply = self._brain.chat(txt, on_tool_call=self._on_call,
                                             on_tool_result=self._on_result)
                finally:
                    stop.set(); st.join()
                self._show(reply)
            except KeyboardInterrupt:
                console.print("\n\n  [dim](Ctrl+C — type /exit to quit)[/dim]")
            except Exception as e:
                import traceback
                console.print(f"\n  [bold red]Error:[/bold red] {e}")
                console.print(f"  [dim]{traceback.format_exc()}[/dim]")


if __name__ == "__main__":
    JarvisApp().run()
