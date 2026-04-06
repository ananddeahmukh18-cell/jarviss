"""
JARVIS Master Brain — OpenRouter API
═══════════════════════════════════════════════════════
Full tool suite:
  • 🧠 Long-term memory (save/search/list/forget)
  • 👁️ Screen vision (AI-powered screenshot analysis)
  • 📁 Complete file management (11 operations)
  • 💻 System control (run commands, processes, clipboard, screenshot, notifications)
  • 🌐 Web (search, fetch, weather, IP, battery, disk, network)
  • 🔑 macOS-native notifications
  • ⌨️  Keyboard automation

Reliability features:
  • Auto model fallback on rate limit
  • Malformed tool call recovery
  • Result truncation (prevents 413 errors)
  • 10-round agentic loop cap
═══════════════════════════════════════════════════════
"""
from __future__ import annotations
import base64, json, os, re, textwrap, uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from openai import OpenAI, BadRequestError, RateLimitError

import config
from config import (
    OPENROUTER_API_KEY, OPENROUTER_BASE_URL,
    MODEL_PRIMARY, MODEL_FALLBACK, MODEL_VISION,
    JARVIS_NAME, MAX_HISTORY_TURNS, MAX_TOKENS,
)
from tools.file_manager import (
    copy_file, create_folder, delete_file, get_file_info,
    list_files, move_file, organize_folder, read_file,
    rename_file, search_files, write_file,
)
from tools.system_control import (
    get_battery_status, get_clipboard, get_disk_space,
    get_network_info, get_running_processes, get_system_info,
    kill_process, open_application, press_key, run_command,
    send_notification, set_clipboard, take_screenshot, type_text,
)
from tools.web_tools import fetch_url, get_ip_info, get_weather, web_search


# ══════════════════════════════════════════════════════════════════
#  MEMORY TOOLS — permanent JSON store at ~/.jarvis_memory.json
# ══════════════════════════════════════════════════════════════════

_MEM = Path.home() / ".jarvis_memory.json"


def _load_mem() -> dict:
    if not _MEM.exists(): return {}
    try: return json.loads(_MEM.read_text(encoding="utf-8"))
    except Exception: return {}


def _save_mem(m: dict) -> None:
    _MEM.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")


def save_memory(topic: str, fact: str) -> str:
    m = _load_mem()
    m[topic.strip().lower()] = fact.strip()
    _save_mem(m)
    return f"✅ Remembered: [{topic}] → {fact}"


def search_memory(query: str) -> str:
    m = _load_mem()
    if not m: return "📭 No memories saved yet."
    q = query.lower()
    hits = [f"[{k}] {v}" for k, v in m.items() if q in k or q in v.lower()]
    return ("📚 Found:\n" + "\n".join(hits)) if hits else f"Nothing in memory matching '{query}'."


def list_memories() -> str:
    m = _load_mem()
    if not m: return "📭 Memory is empty."
    return "📚 All memories:\n" + "\n".join(f"  [{k}] {v}" for k, v in m.items())


def forget_memory(topic: str) -> str:
    m = _load_mem()
    key = topic.strip().lower()
    if key not in m: return f"Nothing saved under '{topic}'."
    del m[key]
    _save_mem(m)
    return f"✅ Forgot: [{topic}]"


# ══════════════════════════════════════════════════════════════════
#  VISION TOOL — screenshot → AI analysis
# ══════════════════════════════════════════════════════════════════

def analyze_screen(prompt: str) -> str:
    """
    Take a screenshot and use AI vision to see + analyse the Mac screen.
    Model: meta-llama/llama-3.2-11b-vision-instruct:free (supports images, actively working)
    """
    tmp = str(Path.home() / "jarvis_vision_tmp.png")
    result = take_screenshot(save_path=tmp)
    if "❌" in result or not os.path.exists(tmp):
        return f"❌ Screenshot failed: {result}"
    try:
        with open(tmp, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        os.remove(tmp)
        client = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)
        resp = client.chat.completions.create(
            model=MODEL_VISION,
            max_tokens=800,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/png;base64,{encoded}"}}
                ]
            }],
            extra_headers={"HTTP-Referer": "https://jarvis-local.app",
                           "X-Title": "JARVIS Vision"},
        )
        return resp.choices[0].message.content or "No response from vision model."
    except Exception as e:
        if os.path.exists(tmp): os.remove(tmp)
        return f"❌ Vision error: {e}"


# ══════════════════════════════════════════════════════════════════
#  TOOL SCHEMAS (OpenAI / OpenRouter format)
# ══════════════════════════════════════════════════════════════════

TOOLS: list[dict] = [

    # ── Memory ────────────────────────────────────────────────────
    {"type":"function","function":{
        "name":"save_memory",
        "description":"Save a fact, preference, or piece of information about the user to permanent memory that persists between sessions.",
        "parameters":{"type":"object","properties":{
            "topic":{"type":"string","description":"Short key, e.g. 'user name', 'preferred browser'"},
            "fact":{"type":"string","description":"The information to store"}},"required":["topic","fact"]}}},

    {"type":"function","function":{
        "name":"search_memory",
        "description":"Search JARVIS permanent memory for facts or preferences about the user.",
        "parameters":{"type":"object","properties":{
            "query":{"type":"string"}},"required":["query"]}}},

    {"type":"function","function":{
        "name":"list_memories",
        "description":"Show ALL facts currently stored in JARVIS permanent memory.",
        "parameters":{"type":"object","properties":{}}}},

    {"type":"function","function":{
        "name":"forget_memory",
        "description":"Delete a specific memory entry by its topic key.",
        "parameters":{"type":"object","properties":{
            "topic":{"type":"string"}},"required":["topic"]}}},

    # ── Vision ────────────────────────────────────────────────────
    {"type":"function","function":{
        "name":"analyze_screen",
        "description":"Take a screenshot and use AI vision to see and describe what is on the Mac screen. Use when asked 'what do you see', 'what's on my screen', 'read the text on screen', or any visual question about screen content.",
        "parameters":{"type":"object","properties":{
            "prompt":{"type":"string","description":"What to look for, describe, or answer from the screenshot"}},"required":["prompt"]}}},

    # ── File Management ───────────────────────────────────────────
    {"type":"function","function":{
        "name":"list_files",
        "description":"List files and folders at a given path with sizes and dates.",
        "parameters":{"type":"object","properties":{
            "path":{"type":"string","description":"Directory path, e.g. ~/Desktop or ~/Downloads"},
            "show_hidden":{"type":"boolean","description":"Show hidden dot-files"}},"required":["path"]}}},

    {"type":"function","function":{
        "name":"move_file",
        "description":"Move or rename a file or directory.",
        "parameters":{"type":"object","properties":{
            "source":{"type":"string","description":"Full source path"},
            "destination":{"type":"string","description":"Full destination path"}},"required":["source","destination"]}}},

    {"type":"function","function":{
        "name":"copy_file",
        "description":"Copy a file or directory to a new location.",
        "parameters":{"type":"object","properties":{
            "source":{"type":"string"},"destination":{"type":"string"}},"required":["source","destination"]}}},

    {"type":"function","function":{
        "name":"delete_file",
        "description":"Delete a file or directory permanently.",
        "parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},

    {"type":"function","function":{
        "name":"create_folder",
        "description":"Create a new directory (creates all missing parent dirs automatically).",
        "parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},

    {"type":"function","function":{
        "name":"rename_file",
        "description":"Rename a file or folder in the same directory.",
        "parameters":{"type":"object","properties":{
            "path":{"type":"string"},"new_name":{"type":"string"}},"required":["path","new_name"]}}},

    {"type":"function","function":{
        "name":"read_file",
        "description":"Read and return the text contents of any file.",
        "parameters":{"type":"object","properties":{
            "path":{"type":"string"},"max_chars":{"type":"integer"}},"required":["path"]}}},

    {"type":"function","function":{
        "name":"write_file",
        "description":"Write or append text to a file. Creates it if it does not exist.",
        "parameters":{"type":"object","properties":{
            "path":{"type":"string"},"content":{"type":"string"},
            "append":{"type":"boolean","description":"True to append, False (default) to overwrite"}},"required":["path","content"]}}},

    {"type":"function","function":{
        "name":"search_files",
        "description":"Find files matching a glob pattern recursively, e.g. *.pdf, invoice*.xlsx, report*.docx.",
        "parameters":{"type":"object","properties":{
            "directory":{"type":"string"},"pattern":{"type":"string"},
            "recursive":{"type":"boolean"}},"required":["directory","pattern"]}}},

    {"type":"function","function":{
        "name":"get_file_info",
        "description":"Get detailed metadata: size, type, creation/modification dates of a file or folder.",
        "parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},

    {"type":"function","function":{
        "name":"organize_folder",
        "description":"Auto-sort all files in a folder into sub-folders by type: Images, Videos, Documents, Code, Archives, Audio, etc.",
        "parameters":{"type":"object","properties":{
            "directory":{"type":"string"},
            "dry_run":{"type":"boolean","description":"Preview only — no actual moves"}},"required":["directory"]}}},

    # ── System Control ────────────────────────────────────────────
    {"type":"function","function":{
        "name":"run_command",
        "description":"Run any shell/terminal command on the Mac and return its output.",
        "parameters":{"type":"object","properties":{
            "command":{"type":"string","description":"Shell command, e.g. 'ls -la' or 'git status'"},
            "timeout":{"type":"integer","description":"Max seconds to wait (default 30)"}},"required":["command"]}}},

    {"type":"function","function":{
        "name":"open_application",
        "description":"Open any Mac application or file using its default handler.",
        "parameters":{"type":"object","properties":{
            "app_name_or_path":{"type":"string","description":"App name like 'Safari', 'Calculator', or full path"}},"required":["app_name_or_path"]}}},

    {"type":"function","function":{
        "name":"get_system_info",
        "description":"Get live CPU usage, RAM, disk space, battery level, and top running processes.",
        "parameters":{"type":"object","properties":{}}}},

    {"type":"function","function":{
        "name":"get_battery_status",
        "description":"Get detailed battery percentage, charging status, and time remaining.",
        "parameters":{"type":"object","properties":{}}}},

    {"type":"function","function":{
        "name":"get_disk_space",
        "description":"Check disk usage and free space for a given path.",
        "parameters":{"type":"object","properties":{
            "path":{"type":"string","description":"Path to check, default is / (root)"}}}}},

    {"type":"function","function":{
        "name":"get_network_info",
        "description":"Get network interface IP addresses and current Wi-Fi SSID.",
        "parameters":{"type":"object","properties":{}}}},

    {"type":"function","function":{
        "name":"send_notification",
        "description":"Send a native macOS notification that appears in the notification centre.",
        "parameters":{"type":"object","properties":{
            "title":{"type":"string","description":"Notification title"},
            "message":{"type":"string","description":"Notification body text"},
            "subtitle":{"type":"string","description":"Optional subtitle line"}},"required":["title","message"]}}},

    {"type":"function","function":{
        "name":"get_running_processes",
        "description":"List currently running processes, optionally filtered by partial name.",
        "parameters":{"type":"object","properties":{
            "filter_name":{"type":"string","description":"Partial process name to filter (leave empty for all)"}}}}},

    {"type":"function","function":{
        "name":"kill_process",
        "description":"Terminate a running process by its PID number or process name.",
        "parameters":{"type":"object","properties":{
            "pid_or_name":{"type":"string"}},"required":["pid_or_name"]}}},

    {"type":"function","function":{
        "name":"take_screenshot",
        "description":"Capture a screenshot of the Mac screen and save it as a PNG file.",
        "parameters":{"type":"object","properties":{
            "save_path":{"type":"string","description":"Where to save (default: ~/screenshot_<timestamp>.png)"}}}}},

    {"type":"function","function":{
        "name":"type_text",
        "description":"Simulate keyboard typing — types the given text at the current cursor position.",
        "parameters":{"type":"object","properties":{
            "text":{"type":"string"}},"required":["text"]}}},

    {"type":"function","function":{
        "name":"press_key",
        "description":"Press a keyboard key or hotkey combo, e.g. 'enter', 'escape', 'cmd+c', 'cmd+space'.",
        "parameters":{"type":"object","properties":{
            "key":{"type":"string","description":"Key name or combo like 'cmd+c', 'ctrl+alt+delete'"}},"required":["key"]}}},

    {"type":"function","function":{
        "name":"get_clipboard",
        "description":"Read and return whatever is currently in the Mac clipboard.",
        "parameters":{"type":"object","properties":{}}}},

    {"type":"function","function":{
        "name":"set_clipboard",
        "description":"Copy any text to the Mac clipboard.",
        "parameters":{"type":"object","properties":{
            "text":{"type":"string"}},"required":["text"]}}},

    # ── Web & Internet ────────────────────────────────────────────
    {"type":"function","function":{
        "name":"web_search",
        "description":"Search the internet using DuckDuckGo and return the top results with titles, URLs, and summaries.",
        "parameters":{"type":"object","properties":{
            "query":{"type":"string"},"max_results":{"type":"integer","description":"Number of results (default 5)"}},"required":["query"]}}},

    {"type":"function","function":{
        "name":"fetch_url",
        "description":"Download and extract the text content of any web page URL.",
        "parameters":{"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}}},

    {"type":"function","function":{
        "name":"get_weather",
        "description":"Get the current weather conditions for any city or location worldwide.",
        "parameters":{"type":"object","properties":{
            "location":{"type":"string","description":"City name, e.g. 'Mumbai' or 'New York'"}},"required":["location"]}}},

    {"type":"function","function":{
        "name":"get_ip_info",
        "description":"Get the Mac's current public IP address, city, country, and ISP.",
        "parameters":{"type":"object","properties":{}}}},
]


# ── Tool dispatcher ────────────────────────────────────────────────
_DISPATCH: dict[str, Any] = {
    # Memory
    "save_memory": save_memory, "search_memory": search_memory,
    "list_memories": list_memories, "forget_memory": forget_memory,
    # Vision
    "analyze_screen": analyze_screen,
    # Files
    "list_files": list_files, "move_file": move_file, "copy_file": copy_file,
    "delete_file": delete_file, "create_folder": create_folder, "rename_file": rename_file,
    "read_file": read_file, "write_file": write_file, "search_files": search_files,
    "get_file_info": get_file_info, "organize_folder": organize_folder,
    # System
    "run_command": run_command, "open_application": open_application,
    "get_system_info": get_system_info, "get_battery_status": get_battery_status,
    "get_disk_space": get_disk_space, "get_network_info": get_network_info,
    "send_notification": send_notification,
    "get_running_processes": get_running_processes, "kill_process": kill_process,
    "take_screenshot": take_screenshot, "type_text": type_text, "press_key": press_key,
    "get_clipboard": get_clipboard, "set_clipboard": set_clipboard,
    # Web
    "web_search": web_search, "fetch_url": fetch_url,
    "get_weather": get_weather, "get_ip_info": get_ip_info,
}

_RESULT_MAX = 3000


def _run_tool(name: str, args: str | dict) -> str:
    fn = _DISPATCH.get(name)
    if fn is None:
        return f"❌ Unknown tool: {name}"
    try:
        inputs: dict = json.loads(args) if isinstance(args, str) else (args or {})
    except Exception:
        inputs = {}
    try:
        result = str(fn(**inputs))
        if len(result) > _RESULT_MAX:
            result = result[:_RESULT_MAX] + f"\n… [truncated — {len(result)} chars total]"
        return result
    except TypeError as e:
        return f"❌ Wrong args for '{name}': {e}"
    except Exception as e:
        return f"❌ Tool '{name}' error: {e}"


# ── Malformed call recovery ────────────────────────────────────────
_BAD_RE = re.compile(r"<function=(\w+)\s*(\{.*?\})\s*</function>", re.DOTALL)


def _recover_malformed(text: str) -> list[dict]:
    calls = []
    for m in _BAD_RE.finditer(text):
        name, raw = m.group(1), m.group(2).strip()
        for attempt in (raw, re.sub(r",\s*}", "}", raw)):
            try:
                json.loads(attempt)
                calls.append({
                    "id": f"fb_{uuid.uuid4().hex[:8]}",
                    "name": name,
                    "arguments": attempt,
                })
                break
            except json.JSONDecodeError:
                continue
    return calls


# ── System prompt ──────────────────────────────────────────────────
_SYSTEM = textwrap.dedent(f"""
    You are {JARVIS_NAME}, an elite AI personal assistant — intelligent, efficient,
    and loyal, inspired by Iron Man's JARVIS. You have comprehensive access to the
    user's Mac through a full suite of tools.

    YOUR CAPABILITIES:
    • 🧠 Permanent memory — remember facts about the user across sessions
    • 👁️ Screen vision — see and analyse what's on the Mac screen
    • 📁 Full file management — create, move, copy, delete, read, write, organise
    • 💻 System control — run terminal commands, manage apps and processes
    • 🔔 Mac notifications — send native alerts to the notification centre
    • 🌐 Internet — web search, fetch pages, weather, network info
    • ⌨️  Keyboard — type text, press hotkeys

    RULES (follow strictly):
    1. ALWAYS use tools to actually perform tasks — never just describe how to do them.
    2. Expand ~ to the real home path before every file operation.
    3. Multi-step tasks: execute each step with tools sequentially.
    4. Use save_memory to remember important user facts across sessions.
    5. Use search_memory at conversation start to recall relevant context.
    6. For "what's on my screen" or any visual query, use analyze_screen.
    7. If a path is unknown, use list_files or search_files first.
    8. Be concise, warm, and professional — like a trusted assistant.

    Current datetime : {{DT}}
    User home dir    : {{HOME}}
    Mode             : {{MODE}}
""").strip()


# ══════════════════════════════════════════════════════════════════
#  JARVIS ASSISTANT CLASS
# ══════════════════════════════════════════════════════════════════

class JarvisAssistant:
    """
    The JARVIS master brain.
    OpenRouter free tier — no daily limit.
    Auto model fallback + malformed call recovery.
    """

    def __init__(self) -> None:
        if not OPENROUTER_API_KEY:
            raise ValueError(
                "OPENROUTER_API_KEY not set!\n"
                "It should be pre-filled in config.py — check that file."
            )
        self._client = OpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,
        )
        self._history: list[dict] = []
        self._model = MODEL_PRIMARY

    def _system(self) -> str:
        mode = "Remote / iPhone (Telegram)" if config.REMOTE_MODE else "Terminal"
        return (_SYSTEM
                .replace("{DT}",   datetime.now().strftime("%A %d %B %Y  %H:%M"))
                .replace("{HOME}", os.path.expanduser("~"))
                .replace("{MODE}", mode))

    def _trim(self) -> None:
        if len(self._history) > MAX_HISTORY_TURNS * 2:
            self._history = self._history[-(MAX_HISTORY_TURNS * 2):]

    def _call_api(self, messages: list[dict]) -> Any:
        """Call primary model, fall back to secondary on rate limit."""
        alt = MODEL_FALLBACK if self._model == MODEL_PRIMARY else MODEL_PRIMARY
        last_err = None
        for model in [self._model, alt]:
            try:
                resp = self._client.chat.completions.create(
                    model=model,
                    max_tokens=MAX_TOKENS,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    temperature=0,        # deterministic → cleaner tool calls
                    extra_headers={
                        "HTTP-Referer": "https://jarvis-local.app",
                        "X-Title": "JARVIS Personal Assistant",
                    },
                )
                self._model = model
                return resp
            except RateLimitError as e:
                last_err = e
                continue
            except BadRequestError:
                raise
        raise last_err or RuntimeError("Both models failed")

    def _execute_calls(
        self, calls: list[dict], on_call, on_result
    ) -> list[dict]:
        results = []
        for tc in calls:
            name = tc["name"]
            args = tc.get("arguments", "{}")
            inputs: dict = {}
            try:
                inputs = json.loads(args) if isinstance(args, str) else (args or {})
            except Exception:
                pass
            if on_call:
                on_call(name, inputs)
            result = _run_tool(name, args)
            if on_result:
                on_result(name, result)
            results.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result,
            })
        return results

    def chat(
        self,
        user_message: str,
        on_tool_call=None,
        on_tool_result=None,
    ) -> str:
        """
        Send a user message, run tool calls in a loop,
        and return the final text response.
        """
        self._history.append({"role": "user", "content": user_message})
        self._trim()

        for _round in range(10):
            messages = [{"role": "system", "content": self._system()}] + self._history

            try:
                response = self._call_api(messages)
            except BadRequestError as e:
                # Try to recover malformed <function=...> tool calls
                calls = _recover_malformed(str(e))
                if calls:
                    self._history.append({
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {"id": c["id"], "type": "function",
                             "function": {"name": c["name"], "arguments": c["arguments"]}}
                            for c in calls
                        ],
                    })
                    self._history.extend(
                        self._execute_calls(calls, on_tool_call, on_tool_result)
                    )
                    continue
                return f"❌ API error: {e}"
            except Exception as e:
                return f"❌ Connection error: {e}"

            msg    = response.choices[0].message
            finish = response.choices[0].finish_reason

            # Save assistant message to history
            entry: dict = {"role": "assistant", "content": msg.content or ""}
            if msg.tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": tc.id, "type": "function",
                        "function": {"name": tc.function.name,
                                     "arguments": tc.function.arguments},
                    }
                    for tc in msg.tool_calls
                ]
            self._history.append(entry)

            # No tool calls → final answer
            if finish != "tool_calls" or not msg.tool_calls:
                return (msg.content or "").strip()

            # Execute tools
            calls = [
                {"id": tc.id, "name": tc.function.name, "arguments": tc.function.arguments}
                for tc in msg.tool_calls
            ]
            self._history.extend(
                self._execute_calls(calls, on_tool_call, on_tool_result)
            )

        return "⚠️ Max steps reached. Please break the task into smaller parts."

    def reset(self) -> None:
        self._history.clear()
        self._model = MODEL_PRIMARY
