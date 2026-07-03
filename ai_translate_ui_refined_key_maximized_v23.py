#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 翻译助手
Python 3.11.9
依赖: pip install openai
API Key: 首次启动弹窗输入，保存到 Windows 凭据管理器
"""

import os
import sys
import json
import ctypes
import subprocess
import ctypes.wintypes as wintypes
import threading
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import simpledialog, messagebox, ttk
from typing import Dict, Tuple, Callable, Any

APP_TITLE = "AI 翻译助手"
APP_ICON_FILE = "ai_translate_icon.ico"
MAX_CHARS = 5000
DEBOUNCE_MS = 800

BG = "#F3F7FF"
CARD = "#FFFFFF"
CARD_SOFT = "#F8FBFF"
BORDER = "#D7E2F0"
BORDER_FOCUS = "#2B74FF"
TEXT = "#172033"
INPUT_TEXT = "#2B3445"
OUTPUT_TEXT = "#253047"
PLACEHOLDER_TEXT = "#8A96A8"
MUTED = "#7A8799"
BLUE = "#1F6FFF"
BLUE_DARK = "#1558D6"
BLUE_SOFT = "#EAF2FF"
ERROR = "#D93025"
OK = "#16833A"
CREDENTIAL_TARGET = "AITranslateAssistant/openai_api_key"
CREDENTIAL_USERNAME = "openai_api_key"
STARTUP_REG_NAME = "AITranslateAssistant"
STARTUP_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"

def get_app_dir() -> Path:
    """Return the directory where the script or frozen exe is located."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


APP_DIR = get_app_dir()
CONFIG_FILE = APP_DIR / "config.json"
LEGACY_CONFIG_FILE = Path(os.environ.get("APPDATA", Path.home())) / "AITranslateAssistant" / "config.json"
LEGACY_CREDENTIAL_TARGET = "AITranslateAssistant/openai_api_key"
CREDENTIAL_PREFIX = "AITranslateAssistant"

DEFAULT_PROVIDERS: Dict[str, Dict[str, Any]] = {
    "OpenAI": {
        "base_url": "",
        "models": [
            "gpt-5.5",
            "gpt-5.5-pro",
            "gpt-5.4",
            "gpt-5.4-pro",
            "gpt-5.4-mini",
            "gpt-5.4-nano",
        ],
        "default_model": "gpt-5.4-mini",
        "display_names": {
            "gpt-5.5": "GPT-5.5 【推荐翻译】",
            "gpt-5.5-pro": "GPT-5.5 Pro",
            "gpt-5.4": "GPT-5.4",
            "gpt-5.4-pro": "GPT-5.4 Pro",
            "gpt-5.4-mini": "GPT-5.4 Mini 【推荐翻译】",
            "gpt-5.4-nano": "GPT-5.4 Nano",
        },
        "reasoning_efforts": {},
        "supports_reasoning": True,
        "endpoint": "responses",
        "env_key": "OPENAI_API_KEY",
    },
    "DeepSeek": {
        "base_url": "https://api.deepseek.com",
        "models": ["deepseek-v4-flash", "deepseek-v4-pro"],
        "default_model": "deepseek-v4-flash",
        "display_names": {
            "deepseek-v4-flash": "DeepSeek V4 Flash",
            "deepseek-v4-pro": "DeepSeek V4 Pro",
        },
        "endpoint": "chat",
        "env_key": "DEEPSEEK_API_KEY",
    },
    "Z.AI": {
        "base_url": "https://api.z.ai/api/paas/v4",
        "models": [
            "glm-5.2",
            "glm-5.1",
            "glm-5",
            "glm-5-turbo",
            "glm-4.7",
            "glm-4.7-flashx",
            "glm-4.7-flash",
            "glm-4.6",
            "glm-4.5",
            "glm-4.5-x",
            "glm-4.5-airx",
            "glm-4.5-air",
            "glm-4.5-flash",
            "glm-4-32b-0414-128k",
        ],
        "default_model": "glm-5.1",
        "display_names": {
            "glm-5.2": "GLM-5.2 【推荐翻译】",
            "glm-5.1": "GLM-5.1",
            "glm-5": "GLM-5",
            "glm-5-turbo": "GLM-5 Turbo",
            "glm-4.7": "GLM-4.7",
            "glm-4.7-flashx": "GLM-4.7 FlashX",
            "glm-4.7-flash": "GLM-4.7 Flash",
            "glm-4.6": "GLM-4.6",
            "glm-4.5": "GLM-4.5",
            "glm-4.5-x": "GLM-4.5 X",
            "glm-4.5-airx": "GLM-4.5 AirX",
            "glm-4.5-air": "GLM-4.5 Air",
            "glm-4.5-flash": "GLM-4.5 Flash",
            "glm-4-32b-0414-128k": "GLM-4 32B 128K",
        },
        "endpoint": "chat",
        "env_key": "ZAI_API_KEY",
    },
    "Custom": {
        "base_url": "",
        "models": [],
        "default_model": "",
        "display_names": {},
        "endpoint": "chat",
        "env_key": "AI_TRANSLATE_API_KEY",
    },
}

REASONING_EFFORT_LABELS = {
    "": "默认",
    "none": "none",
    "minimal": "minimal",
    "low": "low",
    "medium": "medium",
    "high": "high",
    "xhigh": "xhigh",
}
REASONING_EFFORT_VALUES = list(REASONING_EFFORT_LABELS.values())


def reasoning_label(value: str) -> str:
    return REASONING_EFFORT_LABELS.get(value.strip(), value.strip() or "默认")


def reasoning_value(label: str) -> str:
    label = label.strip()
    if label == "默认":
        return ""
    for value, text in REASONING_EFFORT_LABELS.items():
        if text == label:
            return value
    return label


def normalize_openai_model_id(provider: str, model: str) -> tuple[str, str]:
    """Convert pseudo names like gpt-5.5-xhigh to model gpt-5.5 plus reasoning effort xhigh."""
    model = model.strip()
    if provider != "OpenAI":
        return model, ""
    lower = model.lower()
    for effort in ("xhigh", "minimal", "medium", "none", "high", "low"):
        suffix = f"-{effort}"
        if lower.endswith(suffix) and len(model) > len(suffix):
            return model[: -len(suffix)], effort
    return model, ""


def enable_high_dpi() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass




def resource_path(relative_path: str) -> Path:
    """Return the path of a bundled resource for source code or PyInstaller."""
    base_path = getattr(sys, "_MEIPASS", None)
    if base_path:
        return Path(base_path) / relative_path
    return Path(__file__).resolve().parent / relative_path


def set_windows_app_id() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(STARTUP_REG_NAME)
    except Exception:
        pass

def provider_config_default() -> Dict[str, Any]:
    return {
        "provider": "OpenAI",
        "last_model": {name: data["default_model"] for name, data in DEFAULT_PROVIDERS.items()},
        "models": {name: list(data["models"]) for name, data in DEFAULT_PROVIDERS.items()},
        "model_display_names": {
            name: {model: data.get("display_names", {}).get(model, model) for model in data["models"]}
            for name, data in DEFAULT_PROVIDERS.items()
        },
        "reasoning_efforts": {
            name: dict(data.get("reasoning_efforts", {}))
            for name, data in DEFAULT_PROVIDERS.items()
        },
        "base_urls": {name: data["base_url"] for name, data in DEFAULT_PROVIDERS.items()},
    }


def refresh_current_builtin_models(cfg: Dict[str, Any]) -> None:
    """Keep built-in model lists aligned with current provider defaults, preserving user-added custom models."""
    removed_builtin_models = {
        "OpenAI": {"gpt-5-mini", "gpt-5.5-xhigh"},
        "DeepSeek": {"deepseek-chat", "deepseek-reasoner"},
        "Z.AI": set(),
    }

    for provider, data in DEFAULT_PROVIDERS.items():
        models = cfg.setdefault("models", {}).setdefault(provider, [])
        display_map = cfg.setdefault("model_display_names", {}).setdefault(provider, {})
        reasoning_map = cfg.setdefault("reasoning_efforts", {}).setdefault(provider, {})

        # Convert old pseudo OpenAI model IDs like gpt-5.5-xhigh.
        if provider == "OpenAI" and "gpt-5.5-xhigh" in models:
            models[:] = [item for item in models if item != "gpt-5.5-xhigh"]
            if "gpt-5.5" not in models:
                models.append("gpt-5.5")
            reasoning_map["gpt-5.5"] = reasoning_map.get("gpt-5.5") or "xhigh"
            if cfg.setdefault("last_model", {}).get(provider) == "gpt-5.5-xhigh":
                cfg["last_model"][provider] = "gpt-5.5"

        for old_model in removed_builtin_models.get(provider, set()):
            if old_model in models:
                models[:] = [item for item in models if item != old_model]
            display_map.pop(old_model, None)
            reasoning_map.pop(old_model, None)
            if cfg.setdefault("last_model", {}).get(provider) == old_model:
                cfg["last_model"][provider] = data["default_model"]

        # Put current built-in models first, then append user custom models.
        builtin = list(data.get("models", []))
        custom = [m for m in models if m and m not in builtin]
        models[:] = builtin + custom

        for model in builtin:
            display_map[model] = data.get("display_names", {}).get(model, model)
            reasoning_map.setdefault(model, data.get("reasoning_efforts", {}).get(model, ""))

        current = cfg.setdefault("last_model", {}).get(provider, "")
        if current not in models:
            cfg["last_model"][provider] = data["default_model"]


def load_config() -> Dict[str, Any]:
    cfg = provider_config_default()
    config_source = CONFIG_FILE

    # Prefer the portable config next to the app.
    # If the old AppData config exists, load it once for smooth migration.
    if not config_source.exists() and LEGACY_CONFIG_FILE.exists():
        config_source = LEGACY_CONFIG_FILE

    try:
        if config_source.exists():
            user_cfg = json.loads(config_source.read_text(encoding="utf-8"))
            if isinstance(user_cfg, dict):
                for key in ("provider", "last_model", "models", "model_display_names", "reasoning_efforts", "base_urls"):
                    if key in user_cfg:
                        if isinstance(cfg.get(key), dict) and isinstance(user_cfg[key], dict):
                            cfg[key].update(user_cfg[key])
                        else:
                            cfg[key] = user_cfg[key]
    except Exception:
        pass

    for name, data in DEFAULT_PROVIDERS.items():
        cfg.setdefault("models", {}).setdefault(name, [])
        cfg.setdefault("model_display_names", {}).setdefault(name, {})
        cfg.setdefault("reasoning_efforts", {}).setdefault(name, {})
        cfg.setdefault("base_urls", {}).setdefault(name, data["base_url"])
        cfg.setdefault("last_model", {}).setdefault(name, data["default_model"])
        for model in data["models"]:
            if model and model not in cfg["models"][name]:
                cfg["models"][name].append(model)
            if model and model not in cfg["model_display_names"][name]:
                cfg["model_display_names"][name][model] = data.get("display_names", {}).get(model, model)
            if model and model not in cfg["reasoning_efforts"][name]:
                effort = data.get("reasoning_efforts", {}).get(model, "")
                if effort:
                    cfg["reasoning_efforts"][name][model] = effort
        for model in list(cfg["models"][name]):
            if model and model not in cfg["model_display_names"][name]:
                cfg["model_display_names"][name][model] = model
            if model and model not in cfg["reasoning_efforts"][name]:
                cfg["reasoning_efforts"][name][model] = ""

    refresh_current_builtin_models(cfg)

    if cfg.get("provider") not in DEFAULT_PROVIDERS:
        cfg["provider"] = "OpenAI"
    return cfg


def save_config(cfg: Dict[str, Any]) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def credential_target(provider: str) -> str:
    safe_provider = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in provider)
    return f"{CREDENTIAL_PREFIX}/{safe_provider}/api_key"


class WindowsCredentialError(RuntimeError):
    pass


def read_windows_credential(target: str) -> str:
    if sys.platform != "win32":
        return ""

    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)

    class FILETIME(ctypes.Structure):
        _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]

    class CREDENTIAL_ATTRIBUTEW(ctypes.Structure):
        _fields_ = [
            ("Keyword", wintypes.LPWSTR),
            ("Flags", wintypes.DWORD),
            ("ValueSize", wintypes.DWORD),
            ("Value", ctypes.POINTER(ctypes.c_ubyte)),
        ]

    class CREDENTIALW(ctypes.Structure):
        pass

    PCREDENTIALW = ctypes.POINTER(CREDENTIALW)
    CREDENTIALW._fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.POINTER(CREDENTIAL_ATTRIBUTEW)),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]

    CredReadW = advapi32.CredReadW
    CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(PCREDENTIALW)]
    CredReadW.restype = wintypes.BOOL
    CredFree = advapi32.CredFree
    CredFree.argtypes = [ctypes.c_void_p]
    CredFree.restype = None

    CRED_TYPE_GENERIC = 1
    ERROR_NOT_FOUND = 1168
    credential = PCREDENTIALW()
    ok = CredReadW(target, CRED_TYPE_GENERIC, 0, ctypes.byref(credential))
    if not ok:
        err = ctypes.get_last_error()
        if err == ERROR_NOT_FOUND:
            return ""
        raise WindowsCredentialError(f"读取 Windows 凭据失败，错误码: {err}")

    try:
        blob = ctypes.string_at(credential.contents.CredentialBlob, credential.contents.CredentialBlobSize)
        return blob.decode("utf-16-le").strip()
    finally:
        CredFree(credential)


def write_windows_credential(target: str, username: str, secret: str) -> None:
    if sys.platform != "win32":
        raise WindowsCredentialError("当前系统不是 Windows")

    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)

    class FILETIME(ctypes.Structure):
        _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]

    class CREDENTIAL_ATTRIBUTEW(ctypes.Structure):
        _fields_ = [
            ("Keyword", wintypes.LPWSTR),
            ("Flags", wintypes.DWORD),
            ("ValueSize", wintypes.DWORD),
            ("Value", ctypes.POINTER(ctypes.c_ubyte)),
        ]

    class CREDENTIALW(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR),
            ("LastWritten", FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
            ("Persist", wintypes.DWORD),
            ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.POINTER(CREDENTIAL_ATTRIBUTEW)),
            ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
        ]

    CredWriteW = advapi32.CredWriteW
    CredWriteW.argtypes = [ctypes.POINTER(CREDENTIALW), wintypes.DWORD]
    CredWriteW.restype = wintypes.BOOL

    CRED_TYPE_GENERIC = 1
    CRED_PERSIST_LOCAL_MACHINE = 2
    blob = secret.encode("utf-16-le")
    blob_buffer = ctypes.create_string_buffer(blob)

    credential = CREDENTIALW()
    credential.Flags = 0
    credential.Type = CRED_TYPE_GENERIC
    credential.TargetName = target
    credential.Comment = "AI Translate Assistant OpenAI API Key"
    credential.CredentialBlobSize = len(blob)
    credential.CredentialBlob = ctypes.cast(blob_buffer, ctypes.POINTER(ctypes.c_ubyte))
    credential.Persist = CRED_PERSIST_LOCAL_MACHINE
    credential.AttributeCount = 0
    credential.Attributes = None
    credential.TargetAlias = None
    credential.UserName = username

    ok = CredWriteW(ctypes.byref(credential), 0)
    if not ok:
        err = ctypes.get_last_error()
        raise WindowsCredentialError(f"保存 Windows 凭据失败，错误码: {err}")

    saved = read_windows_credential(target)
    if saved != secret:
        raise WindowsCredentialError("保存后校验失败")


def read_saved_api_key(provider: str) -> str:
    target = credential_target(provider)
    if sys.platform == "win32":
        value = read_windows_credential(target)
        if value:
            return value
        if provider == "OpenAI":
            return read_windows_credential(LEGACY_CREDENTIAL_TARGET)
        return ""

    try:
        import keyring
        value = (keyring.get_password(target, CREDENTIAL_USERNAME) or "").strip()
        if value:
            return value
        if provider == "OpenAI":
            return (keyring.get_password(LEGACY_CREDENTIAL_TARGET, CREDENTIAL_USERNAME) or "").strip()
        return ""
    except Exception:
        return ""


def save_api_key(provider: str, secret: str) -> str:
    target = credential_target(provider)
    if sys.platform == "win32":
        write_windows_credential(target, CREDENTIAL_USERNAME, secret)
        return "Windows 凭据管理器"

    import keyring
    keyring.set_password(target, CREDENTIAL_USERNAME, secret)
    return "系统凭据"


def get_startup_command() -> str:
    if getattr(sys, "frozen", False):
        return subprocess.list2cmdline([sys.executable])

    script_path = os.path.abspath(__file__)
    pythonw_path = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    python_path = pythonw_path if os.path.exists(pythonw_path) else sys.executable
    return subprocess.list2cmdline([python_path, script_path])


def is_startup_enabled() -> bool:
    if sys.platform != "win32":
        return False

    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_PATH, 0, winreg.KEY_READ) as key:
            value, _value_type = winreg.QueryValueEx(key, STARTUP_REG_NAME)
            return bool(str(value).strip())
    except FileNotFoundError:
        return False


def set_startup_enabled(enabled: bool) -> None:
    if sys.platform != "win32":
        raise RuntimeError("当前系统不支持开机启动设置")

    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, STARTUP_REG_NAME, 0, winreg.REG_SZ, get_startup_command())
            return

        try:
            winreg.DeleteValue(key, STARTUP_REG_NAME)
        except FileNotFoundError:
            pass


def friendly_error(exc: Exception) -> str:
    msg = str(exc)
    low = msg.lower()
    if "insufficient_quota" in low or "exceeded your current quota" in low:
        return "API 额度不足。ChatGPT Plus 不包含 API 额度，请到 OpenAI Platform Billing 充值 API 余额。"
    if "api key" in low or "authentication" in low or "401" in low:
        return "API Key 无效或未设置，请点击 设置Key 重新输入。"
    if "rate limit" in low or "429" in low:
        return "请求过快或额度受限，请稍后再试。"
    if "base url" in low or "base_url" in low:
        return "API 地址未设置或不可用，请检查模型提供商的 Base URL。"
    if "model" in low and ("not found" in low or "does not exist" in low):
        return "模型名称不可用，请打开模型设置修改模型名称。"
    return "翻译失败：" + msg


def round_rect(canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int, radius: int, **kwargs) -> int:
    radius = min(radius, max(0, (x2 - x1) // 2), max(0, (y2 - y1) // 2))
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=18, **kwargs)


class RoundedButton(tk.Canvas):
    def __init__(
        self,
        master,
        text: str,
        command: Callable[[], None] | None = None,
        width: int = 92,
        height: int = 34,
        primary: bool = False,
        font=None,
    ):
        super().__init__(master, width=width, height=height, highlightthickness=0, bd=0, bg=master["bg"])
        self.text = text
        self.command = command
        self.width = width
        self.height = height
        self.primary = primary
        self.font = font
        self.hover = False
        self.pressed = False
        self.configure(cursor="hand2")
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)
        self._draw()

    def _colors(self) -> tuple[str, str, str]:
        if self.primary:
            return (BLUE_DARK if self.hover else BLUE, BLUE, "#FFFFFF")
        return (BLUE_SOFT if self.hover else CARD, BORDER, TEXT)

    def _draw(self) -> None:
        self.delete("all")
        fill, outline, fg = self._colors()
        pad = 1 if not self.pressed else 2
        round_rect(self, pad, pad, self.width - pad, self.height - pad, 10, fill=fill, outline=outline, width=1)
        self.create_text(self.width // 2, self.height // 2, text=self.text, fill=fg, font=self.font)

    def _enter(self, _event=None) -> None:
        self.hover = True
        self._draw()

    def _leave(self, _event=None) -> None:
        self.hover = False
        self.pressed = False
        self._draw()

    def _press(self, _event=None) -> None:
        self.pressed = True
        self._draw()

    def _release(self, _event=None) -> None:
        was_pressed = self.pressed
        self.pressed = False
        self._draw()
        if was_pressed and self.command:
            self.command()


class ToggleSwitch(tk.Canvas):
    def __init__(
        self,
        master,
        variable: tk.BooleanVar,
        command: Callable[[], None],
        font=None,
        on_text: str = "开启",
        off_text: str = "关闭",
        width: int = 118,
    ):
        super().__init__(master, width=width, height=34, highlightthickness=0, bd=0, bg=master["bg"], cursor="hand2")
        self.variable = variable
        self.command = command
        self.font = font
        self.on_text = on_text
        self.off_text = off_text
        self.width = width
        self.bind("<Button-1>", self._toggle)
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        active = self.variable.get()
        fill = BLUE_SOFT if active else CARD
        outline = BLUE if active else BORDER
        txt = self.on_text if active else self.off_text
        round_rect(self, 1, 1, self.width - 1, 33, 17, fill=fill, outline=outline, width=1)
        self.create_text(self.width // 2, 17, text=txt, fill=BLUE if active else MUTED, font=self.font)

    def _toggle(self, _event=None) -> None:
        self.variable.set(not self.variable.get())
        self._draw()
        self.command()


class SegmentedStyle(tk.Frame):
    def __init__(self, master, variable: tk.StringVar, command: Callable[[], None], font=None):
        super().__init__(master, bg=master["bg"])
        self.variable = variable
        self.command = command
        self.font = font
        self.buttons: dict[str, RoundedButton] = {}
        self._make_button("professional", "专业化", 0)
        self._make_button("programmer", "程序员化", 1)
        self._make_button("spoken", "口语化", 2)

    def _make_button(self, value: str, text: str, col: int) -> None:
        btn = RoundedButton(self, text=text, command=lambda v=value: self.select(v), width=86, height=34, primary=False, font=self.font)
        btn.grid(row=0, column=col, padx=(0 if col == 0 else 8, 0))
        self.buttons[value] = btn
        self._refresh()

    def select(self, value: str) -> None:
        self.variable.set(value)
        self._refresh()
        self.command()

    def _refresh(self) -> None:
        for value, btn in self.buttons.items():
            btn.primary = value == self.variable.get()
            btn._draw()


class RoundedTextBox(tk.Frame):
    def __init__(
        self,
        master,
        placeholder: str,
        font,
        readonly: bool = False,
        height: int = 150,
        text_fg: str = INPUT_TEXT,
        placeholder_fg: str = PLACEHOLDER_TEXT,
    ):
        super().__init__(master, bg=master["bg"], height=height)
        self.placeholder = placeholder
        self.readonly = readonly
        self.text_fg = text_fg
        self.placeholder_fg = placeholder_fg
        self.placeholder_visible = False
        self.border_color = BORDER
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0, bg=master["bg"])
        self.canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.text = tk.Text(
            self,
            wrap="word",
            bd=0,
            relief="flat",
            bg=CARD_SOFT if readonly else CARD,
            fg=self.text_fg,
            insertbackground=BLUE,
            selectbackground=BLUE_SOFT,
            selectforeground=TEXT,
            inactiveselectbackground=BLUE_SOFT,
            font=font,
            padx=16,
            pady=14,
            undo=not readonly,
            height=6,
        )
        self.text.place(x=2, y=2, relwidth=1, relheight=1, width=-4, height=-4)
        self.bind("<Configure>", self._redraw)
        self.canvas.bind("<Configure>", self._redraw)
        self.text.bind("<FocusIn>", self._focus_in)
        self.text.bind("<FocusOut>", self._focus_out)
        self.text.bind("<KeyPress>", self._key_press)
        self.show_placeholder()
        if readonly:
            self.text.configure(state="disabled")

    def _redraw(self, _event=None) -> None:
        self.canvas.delete("all")
        w = max(10, self.winfo_width())
        h = max(10, self.winfo_height())
        fill = CARD_SOFT if self.readonly else CARD
        round_rect(self.canvas, 1, 1, w - 2, h - 2, 14, fill=fill, outline=self.border_color, width=1)

    def _focus_in(self, _event=None) -> None:
        self.border_color = BORDER_FOCUS
        self._redraw()
        if self.placeholder_visible and not self.readonly:
            self.text.delete("1.0", "end")
            self.text.configure(fg=self.text_fg)
            self.placeholder_visible = False

    def _key_press(self, event=None):
        if self.readonly or not self.placeholder_visible:
            return None
        if event and event.keysym in {"Tab", "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R", "Escape"}:
            return None
        self.text.delete("1.0", "end")
        self.text.configure(fg=self.text_fg)
        self.placeholder_visible = False
        return None

    def _focus_out(self, _event=None) -> None:
        self.border_color = BORDER
        self._redraw()
        if not self.get().strip():
            self.show_placeholder()

    def show_placeholder(self) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", self.placeholder)
        self.text.configure(fg=self.placeholder_fg)
        self.placeholder_visible = True
        if self.readonly:
            self.text.configure(state="disabled")

    def get(self) -> str:
        if self.placeholder_visible:
            return ""
        return self.text.get("1.0", "end-1c")

    def set(self, value: str, muted: bool = False) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", value)
        self.text.configure(fg=PLACEHOLDER_TEXT if muted else self.text_fg)
        self.placeholder_visible = False
        if self.readonly:
            self.text.configure(state="disabled")

    def clear(self) -> None:
        if not self.readonly and self.focus_get() == self.text:
            self.text.configure(state="normal")
            self.text.delete("1.0", "end")
            self.text.configure(fg=self.text_fg)
            self.placeholder_visible = False
            return
        self.show_placeholder()


class Card(tk.Canvas):
    def __init__(self, master, radius: int = 16):
        super().__init__(master, highlightthickness=0, bd=0, bg=BG)
        self.radius = radius
        self.inner = tk.Frame(self, bg=CARD)
        self.window_id = self.create_window(0, 0, window=self.inner, anchor="nw")
        self.bind("<Configure>", self._resize)

    def _resize(self, _event=None) -> None:
        self.delete("bg")
        w = self.winfo_width()
        h = self.winfo_height()
        round_rect(self, 1, 1, w - 2, h - 2, self.radius, fill=CARD, outline=BORDER, width=1, tags="bg")
        self.tag_lower("bg")
        self.coords(self.window_id, 1, 1)
        self.itemconfigure(self.window_id, width=max(1, w - 2), height=max(1, h - 2))


class TranslateSection(tk.Frame):
    def __init__(self, app, master, title_left: str, title_right: str, input_hint: str):
        super().__init__(master, bg=CARD)
        self.app = app
        self.title_left = title_left
        self.title_right = title_right
        self.after_id = None
        self.req_id = 0
        self.style_var = tk.StringVar(value="professional")

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        header = tk.Frame(self, bg=CARD)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=18, pady=(16, 10))
        header.columnconfigure(3, weight=1)

        tk.Label(header, text=title_left, bg=CARD, fg=BLUE, font=app.font_h2).grid(row=0, column=0, sticky="w")
        tk.Label(header, text="  →  ", bg=CARD, fg=TEXT, font=app.font_h2).grid(row=0, column=1)
        tk.Label(header, text=title_right, bg=CARD, fg=TEXT, font=app.font_h2).grid(row=0, column=2, sticky="w")

        SegmentedStyle(header, self.style_var, self.schedule_translate, font=app.font_btn).grid(row=0, column=4, padx=(12, 0))
        RoundedButton(header, "清空", self.clear, width=82, font=app.font_btn).grid(row=0, column=5, padx=(12, 0))
        RoundedButton(header, "复制结果", self.copy_result, width=104, primary=True, font=app.font_btn).grid(row=0, column=6, padx=(8, 0))

        left = tk.Frame(self, bg=CARD)
        right = tk.Frame(self, bg=CARD)
        left.grid(row=1, column=0, sticky="nsew", padx=(18, 9), pady=(0, 18))
        right.grid(row=1, column=1, sticky="nsew", padx=(9, 18), pady=(0, 18))
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)

        input_font = app.font_text_en if title_left == "English" else app.font_text_cn
        output_font = app.font_text_en if title_right == "English" else app.font_text_cn
        self.input_box = RoundedTextBox(left, input_hint, font=input_font, readonly=False, text_fg=INPUT_TEXT)
        self.input_box.grid(row=0, column=0, sticky="nsew")
        self.output_box = RoundedTextBox(right, "翻译结果将自动显示在这里...", font=output_font, readonly=True, text_fg=OUTPUT_TEXT)
        self.output_box.grid(row=0, column=0, sticky="nsew")

        self.count_label = tk.Label(left, text="0/5000", bg=CARD, fg=MUTED, font=app.font_small)
        self.count_label.place(relx=1.0, rely=1.0, anchor="se", x=-14, y=-10)

        self.input_box.text.bind("<<Modified>>", self._modified)

    def _modified(self, _event=None) -> None:
        if not self.input_box.text.edit_modified():
            return
        self.input_box.text.edit_modified(False)
        text = self.input_box.get()
        self.count_label.configure(text=f"{min(len(text), MAX_CHARS)}/{MAX_CHARS}")
        self.schedule_translate()

    def schedule_translate(self) -> None:
        text = self.input_box.get().strip()
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None
        if not text:
            self.output_box.clear()
            self.app.set_status("等待输入")
            return
        if len(text) > MAX_CHARS:
            self.output_box.set("输入内容超过 5000 字，请减少后再翻译。", muted=True)
            return
        self.after_id = self.after(DEBOUNCE_MS, self.start_translate)

    def start_translate(self) -> None:
        text = self.input_box.get().strip()
        if not text:
            return
        if not self.app.ensure_api_key():
            self.output_box.set("未设置 API Key，无法翻译。", muted=True)
            return
        self.req_id += 1
        req_id = self.req_id
        style = self.style_var.get()
        self.output_box.set("正在自动翻译...", muted=True)
        self.app.set_status(f"{self.title_left} → {self.title_right} 翻译中")
        threading.Thread(target=self._worker, args=(req_id, text, style), daemon=True).start()

    def _worker(self, req_id: int, text: str, style: str) -> None:
        try:
            result = self.app.translate_api(text, self.title_left, self.title_right, style)
            self.after(0, self._done, req_id, result, None)
        except Exception as exc:
            self.after(0, self._done, req_id, "", exc)

    def _done(self, req_id: int, result: str, exc: Exception | None) -> None:
        if req_id != self.req_id:
            return
        if exc:
            self.output_box.set(friendly_error(exc), muted=True)
            self.app.set_status("翻译失败", is_error=True)
            return
        self.output_box.set(result)
        self.app.set_status("翻译完成", is_error=False)

    def clear(self) -> None:
        self.req_id += 1
        self.input_box.clear()
        self.output_box.clear()
        self.count_label.configure(text="0/5000")
        self.app.set_status("已清空")

    def copy_result(self) -> None:
        text = self.output_box.get().strip()
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.app.set_status("结果已复制")


class ModelSettingsDialog(tk.Toplevel):
    def __init__(self, app: "TranslateApp"):
        super().__init__(app)
        self.app = app
        self.title("模型设置")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.transient(app)
        self.grab_set()

        self.provider_var = tk.StringVar(value=app.provider_var.get())
        self.model_var = tk.StringVar(value=app.model_var.get())
        self.model_display_var = tk.StringVar(value=app._model_display_name(app._current_provider(), app.model_var.get()))
        self.reasoning_effort_var = tk.StringVar(
            value=reasoning_label(app._current_reasoning_effort(app._current_provider(), app.model_var.get()))
        )
        self.base_url_var = tk.StringVar(value=app.base_url_var.get())

        self._build_ui()
        self._refresh_provider_view()
        self._center()
        self.protocol("WM_DELETE_WINDOW", self.close)

    def _build_ui(self) -> None:
        outer = tk.Frame(self, bg=BG)
        outer.pack(fill="both", expand=True, padx=22, pady=22)

        card_canvas = Card(outer, radius=16)
        card_canvas.pack(fill="both", expand=True)
        card = card_canvas.inner
        card.columnconfigure(1, weight=1)

        tk.Label(card, text="模型设置", bg=CARD, fg=TEXT, font=self.app.font_h2).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(20, 18)
        )

        tk.Label(card, text="提供商", bg=CARD, fg=MUTED, font=self.app.font_btn).grid(row=1, column=0, sticky="e", padx=(20, 10), pady=10)
        self.provider_combo = ttk.Combobox(
            card,
            textvariable=self.provider_var,
            values=list(DEFAULT_PROVIDERS.keys()),
            width=26,
            state="readonly",
            font=self.app.font_btn,
        )
        self.provider_combo.grid(row=1, column=1, sticky="ew", padx=(0, 20), pady=10, ipady=6)
        self.provider_combo.bind("<<ComboboxSelected>>", self._on_provider_changed)

        tk.Label(card, text="模型显示名", bg=CARD, fg=MUTED, font=self.app.font_btn).grid(row=2, column=0, sticky="e", padx=(20, 10), pady=10)
        self.model_combo = ttk.Combobox(
            card,
            textvariable=self.model_display_var,
            values=self.app._current_model_labels(),
            width=26,
            state="readonly",
            font=self.app.font_btn,
        )
        self.model_combo.grid(row=2, column=1, sticky="ew", padx=(0, 12), pady=10, ipady=6)
        self.model_combo.bind("<<ComboboxSelected>>", self._save_model)
        self.model_combo.bind("<FocusOut>", self._save_model)

        model_btns = tk.Frame(card, bg=CARD)
        model_btns.grid(row=2, column=2, sticky="w", padx=(0, 20), pady=10)
        RoundedButton(model_btns, "添加", self.add_model, width=66, font=self.app.font_btn).grid(row=0, column=0, padx=(0, 6))
        RoundedButton(model_btns, "删除", self.delete_model, width=66, font=self.app.font_btn).grid(row=0, column=1)

        tk.Label(card, text="推理强度", bg=CARD, fg=MUTED, font=self.app.font_btn).grid(row=3, column=0, sticky="e", padx=(20, 10), pady=10)
        self.reasoning_combo = ttk.Combobox(
            card,
            textvariable=self.reasoning_effort_var,
            values=REASONING_EFFORT_VALUES,
            width=26,
            state="readonly",
            font=self.app.font_btn,
        )
        self.reasoning_combo.grid(row=3, column=1, sticky="ew", padx=(0, 12), pady=10, ipady=6)
        self.reasoning_combo.bind("<<ComboboxSelected>>", self._save_reasoning_effort)
        self.reasoning_tip = tk.Label(card, text="仅 OpenAI Responses 模型使用", bg=CARD, fg=MUTED, font=self.app.font_small)
        self.reasoning_tip.grid(row=3, column=2, sticky="w", padx=(0, 20), pady=10)

        tk.Label(card, text="API 地址", bg=CARD, fg=MUTED, font=self.app.font_btn).grid(row=4, column=0, sticky="e", padx=(20, 10), pady=10)
        self.base_entry = tk.Entry(
            card,
            textvariable=self.base_url_var,
            bg=CARD_SOFT,
            fg=TEXT,
            bd=1,
            relief="solid",
            insertbackground=BLUE,
            font=self.app.font_btn,
        )
        self.base_entry.grid(row=4, column=1, columnspan=2, sticky="ew", padx=(0, 20), pady=10, ipady=8)

        hint = (
            "添加模型时需要填写模型ID和显示名；显示名在同一提供商下不能重复。"
            "OpenAI 的 xhigh 是推理强度，不是模型名后缀；"
            "DeepSeek 默认 https://api.deepseek.com；Z.AI 默认 https://api.z.ai/api/paas/v4；"
            "Custom 填 OpenAI-compatible Base URL。"
        )
        tk.Label(card, text=hint, bg=CARD, fg=MUTED, font=self.app.font_small, wraplength=580, justify="left").grid(
            row=5, column=0, columnspan=3, sticky="w", padx=20, pady=(6, 18)
        )

        btns = tk.Frame(card, bg=CARD)
        btns.grid(row=6, column=0, columnspan=3, sticky="ew", padx=20, pady=(0, 22))
        btns.columnconfigure(0, weight=1)
        RoundedButton(btns, "设置Key", lambda: self.app.reset_api_key(show_success=True, parent=self), width=92, font=self.app.font_btn).grid(row=0, column=1, padx=(0, 8))
        RoundedButton(btns, "保存", self.save_all, width=82, primary=True, font=self.app.font_btn).grid(row=0, column=2, padx=(0, 8))
        RoundedButton(btns, "关闭", self.close, width=82, font=self.app.font_btn).grid(row=0, column=3)

    def _center(self) -> None:
        self.update_idletasks()
        width = 660
        height = 500
        x = self.app.winfo_x() + max((self.app.winfo_width() - width) // 2, 0)
        y = self.app.winfo_y() + max((self.app.winfo_height() - height) // 2, 0)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _provider(self) -> str:
        provider = self.provider_var.get().strip() or "OpenAI"
        return provider if provider in DEFAULT_PROVIDERS else "OpenAI"

    def _refresh_provider_view(self) -> None:
        provider = self._provider()
        self.app.provider_var.set(provider)
        self.app.base_url_var.set(str(self.app.config_data.get("base_urls", {}).get(provider) or DEFAULT_PROVIDERS[provider]["base_url"]))
        self.base_url_var.set(self.app.base_url_var.get())
        model = str(self.app.config_data.get("last_model", {}).get(provider) or DEFAULT_PROVIDERS[provider]["default_model"])
        self.app.model_var.set(model)
        self.model_var.set(model)
        self.model_display_var.set(self.app._model_display_name(provider, model))
        self.reasoning_effort_var.set(reasoning_label(self.app._current_reasoning_effort(provider, model)))
        self.model_combo.configure(values=self.app._current_model_labels())
        self._refresh_reasoning_state()
        self.app.reasoning_effort_var.set(self.reasoning_effort_var.get())
        self.app._save_provider_state()
        self.app._refresh_model_summary()

    def _on_provider_changed(self, _event=None) -> None:
        self._refresh_provider_view()
        self.app.set_status(f"已切换到 {self._provider()}")

    def _save_model(self, _event=None) -> None:
        provider = self._provider()
        display_name = self.model_display_var.get().strip()
        model = self.app._model_from_display_name(provider, display_name) or self.model_var.get().strip()
        self.model_var.set(model)
        self.app.model_var.set(model)
        self.reasoning_effort_var.set(reasoning_label(self.app._current_reasoning_effort(provider, model)))
        self._refresh_reasoning_state()
        self.app.reasoning_effort_var.set(self.reasoning_effort_var.get())
        self.app._save_provider_state()
        self.app._refresh_model_summary()

    def _refresh_reasoning_state(self) -> None:
        provider = self._provider()
        supports = bool(DEFAULT_PROVIDERS[provider].get("supports_reasoning"))
        state = "readonly" if supports else "disabled"
        self.reasoning_combo.configure(state=state)
        self.reasoning_tip.configure(text="仅 OpenAI Responses 模型使用" if supports else "当前提供商不发送该参数")

    def _save_reasoning_effort(self, _event=None) -> None:
        provider = self._provider()
        model = self.model_var.get().strip()
        if not model:
            return
        effort = reasoning_value(self.reasoning_effort_var.get())
        self.app.config_data.setdefault("reasoning_efforts", {}).setdefault(provider, {})[model] = effort
        self.app.reasoning_effort_var.set(reasoning_label(effort))
        self.app._save_provider_state()
        self.app._refresh_model_summary()

    def add_model(self) -> None:
        provider = self._provider()
        model = simpledialog.askstring("添加模型", f"请输入 {provider} 模型ID，例如 gpt-5.5 / deepseek-v4-pro / glm-5.1:", parent=self)
        if not model or not model.strip():
            return
        model = model.strip()
        model, inferred_effort = normalize_openai_model_id(provider, model)
        if inferred_effort:
            messagebox.showinfo(
                "模型名称已转换",
                f"已识别为模型ID：{model}\n推理强度：{inferred_effort}",
                parent=self,
            )

        models = self.app.config_data.setdefault("models", {}).setdefault(provider, [])
        if model in models:
            messagebox.showinfo("添加模型", "该模型ID已经存在。", parent=self)
            return

        display_name = simpledialog.askstring("添加模型", "请输入显示名，例如 GPT 5.5 高精度:", initialvalue=model, parent=self)
        if not display_name or not display_name.strip():
            return
        display_name = display_name.strip()
        if self.app._display_name_exists(provider, display_name):
            messagebox.showwarning("显示名重复", f"显示名已经存在，请换一个名称。\n\n{display_name}", parent=self)
            return

        display_map = self.app.config_data.setdefault("model_display_names", {}).setdefault(provider, {})
        reasoning_map = self.app.config_data.setdefault("reasoning_efforts", {}).setdefault(provider, {})
        models.append(model)
        display_map[model] = display_name
        reasoning_map[model] = inferred_effort or reasoning_map.get(model, "")
        self.model_var.set(model)
        self.model_display_var.set(display_name)
        self.reasoning_effort_var.set(reasoning_label(reasoning_map.get(model, "")))
        self.app.model_var.set(model)
        self.app.reasoning_effort_var.set(self.reasoning_effort_var.get())
        self.model_combo.configure(values=self.app._current_model_labels())
        self.app._save_provider_state()
        self.app._refresh_model_summary()
        self.app.set_status(f"已添加模型: {display_name}", is_error=False)

    def delete_model(self) -> None:
        provider = self._provider()
        display_name = self.model_display_var.get().strip()
        model = self.app._model_from_display_name(provider, display_name) or self.model_var.get().strip()
        if not model:
            messagebox.showinfo("删除模型", "请先选择要删除的模型。", parent=self)
            return

        builtin_models = set(DEFAULT_PROVIDERS[provider].get("models", []))
        default_model = DEFAULT_PROVIDERS[provider].get("default_model", "")
        if model in builtin_models:
            messagebox.showinfo("删除模型", "内置默认模型不能删除，只能删除手动添加的模型。", parent=self)
            return

        if not messagebox.askyesno("删除模型", f"确定删除自定义模型？\n\n{model}", parent=self):
            return

        models = self.app.config_data.setdefault("models", {}).setdefault(provider, [])
        self.app.config_data["models"][provider] = [item for item in models if item != model]
        self.app.config_data.setdefault("model_display_names", {}).setdefault(provider, {}).pop(model, None)
        self.app.config_data.setdefault("reasoning_efforts", {}).setdefault(provider, {}).pop(model, None)

        remaining_models = self.app._current_models()
        next_model = remaining_models[0] if remaining_models else default_model
        self.model_combo.configure(values=self.app._current_model_labels())
        self.model_var.set(next_model)
        self.model_display_var.set(self.app._model_display_name(provider, next_model))
        self.reasoning_effort_var.set(reasoning_label(self.app._current_reasoning_effort(provider, next_model)))
        self.app.model_var.set(next_model)
        self.app.reasoning_effort_var.set(self.reasoning_effort_var.get())
        self.app.config_data.setdefault("last_model", {})[provider] = next_model
        self.app.config_data["provider"] = provider
        self.app.config_data.setdefault("base_urls", {})[provider] = self.base_url_var.get().strip()
        save_config(self.app.config_data)
        self.app._refresh_model_summary()
        self.app.set_status(f"已删除模型: {display_name or model}", is_error=False)

    def save_all(self) -> None:
        provider = self._provider()
        display_name = self.model_display_var.get().strip()
        model = self.app._model_from_display_name(provider, display_name) or self.model_var.get().strip()
        self.model_var.set(model)
        self.app.provider_var.set(provider)
        self.app.model_var.set(model)
        self.app.reasoning_effort_var.set(self.reasoning_effort_var.get())
        self.app.config_data.setdefault("reasoning_efforts", {}).setdefault(provider, {})[model] = reasoning_value(self.reasoning_effort_var.get())
        self.app.base_url_var.set(self.base_url_var.get().strip())
        self.app._save_provider_state()
        self.app._refresh_model_summary()
        self.app.set_status("模型设置已保存", is_error=False)

    def close(self) -> None:
        self.save_all()
        self.grab_release()
        self.destroy()


class TranslateApp(tk.Tk):
    def __init__(self):
        enable_high_dpi()
        set_windows_app_id()
        super().__init__()
        self.title(APP_TITLE)
        self._set_app_icon()
        self.window_width = 1040
        self.window_height = 740
        self.geometry(f"{self.window_width}x{self.window_height}")
        self.minsize(960, 660)
        self.configure(bg=BG)
        self.option_add("*Font", self._best_font(10))
        try:
            self.tk.call("tk", "scaling", 1.25)
        except Exception:
            pass

        family = self._best_font_family()
        english_family = self._best_english_font_family()
        self.font_title = tkfont.Font(family=family, size=18, weight="bold")
        self.font_h2 = tkfont.Font(family=family, size=15, weight="bold")
        self.font_text_cn = tkfont.Font(family=family, size=11)
        self.font_text_en = tkfont.Font(family=english_family, size=11)
        self.font_text = self.font_text_cn
        self.font_btn = tkfont.Font(family=family, size=10)
        self.font_small = tkfont.Font(family=family, size=9)
        self.font_logo = tkfont.Font(family="Segoe UI", size=16, weight="bold")

        self.cache: Dict[Tuple[str, str, str, str, str, str, str], str] = {}
        self.api_key_cache: Dict[str, str] = {}
        self.config_data = load_config()
        self.provider_var = tk.StringVar(value=str(self.config_data.get("provider", "OpenAI")))
        self.model_var = tk.StringVar(value=self._current_model_default())
        self.reasoning_effort_var = tk.StringVar(
            value=reasoning_label(self._current_reasoning_effort(self._current_provider(), self.model_var.get()))
        )
        self.base_url_var = tk.StringVar(value=self._current_base_url())
        self.top_var = tk.BooleanVar(value=False)
        self.startup_var = tk.BooleanVar(value=False)
        try:
            self.startup_var.set(is_startup_enabled())
        except Exception:
            self.startup_var.set(False)
        self._build_ui()
        self.maximize_window()
        self.after(300, self.ensure_api_key)

    def _set_app_icon(self) -> None:
        icon_path = resource_path(APP_ICON_FILE)
        if not icon_path.exists():
            return
        try:
            self.iconbitmap(str(icon_path))
        except tk.TclError:
            try:
                icon_image = tk.PhotoImage(file=str(icon_path))
                self.iconphoto(True, icon_image)
                self._icon_image = icon_image
            except Exception:
                pass

    def maximize_window(self) -> None:
        self.update_idletasks()
        try:
            self.state("zoomed")
            return
        except tk.TclError:
            pass

        try:
            self.attributes("-zoomed", True)
            return
        except tk.TclError:
            pass

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        self.geometry(f"{screen_width}x{screen_height}+0+0")

    def _current_provider(self) -> str:
        provider = self.provider_var.get().strip() or "OpenAI"
        return provider if provider in DEFAULT_PROVIDERS else "OpenAI"

    def _current_models(self) -> list[str]:
        provider = self._current_provider()
        models = list(self.config_data.get("models", {}).get(provider, []))
        default_model = DEFAULT_PROVIDERS[provider].get("default_model", "")
        if default_model and default_model not in models:
            models.insert(0, default_model)
        return models

    def _model_display_name(self, provider: str, model: str) -> str:
        if not model:
            return ""
        display_map = self.config_data.setdefault("model_display_names", {}).setdefault(provider, {})
        display_name = str(display_map.get(model, "")).strip()
        if display_name:
            return display_name
        display_map[model] = model
        return model

    def _current_model_labels(self) -> list[str]:
        provider = self._current_provider()
        labels: list[str] = []
        used: set[str] = set()
        for model in self._current_models():
            label = self._model_display_name(provider, model)
            if label in used:
                label = f"{label} ({model})"
            labels.append(label)
            used.add(label)
        return labels

    def _model_from_display_name(self, provider: str, display_name: str) -> str:
        display_name = display_name.strip()
        if not display_name:
            return ""
        display_map = self.config_data.setdefault("model_display_names", {}).setdefault(provider, {})
        for model in self._current_models():
            if display_map.get(model, model) == display_name:
                return model
        if display_name in self._current_models():
            return display_name
        return ""

    def _display_name_exists(self, provider: str, display_name: str, ignore_model: str = "") -> bool:
        target = display_name.strip().casefold()
        if not target:
            return False
        display_map = self.config_data.setdefault("model_display_names", {}).setdefault(provider, {})
        for model in self._current_models():
            if model == ignore_model:
                continue
            current = str(display_map.get(model, model)).strip().casefold()
            if current == target:
                return True
        return False

    def _current_model_default(self) -> str:
        provider = str(self.config_data.get("provider", "OpenAI"))
        if provider not in DEFAULT_PROVIDERS:
            provider = "OpenAI"
        model = os.environ.get("OPENAI_MODEL", "").strip() if provider == "OpenAI" else ""
        if model:
            return model
        return str(self.config_data.get("last_model", {}).get(provider) or DEFAULT_PROVIDERS[provider]["default_model"])

    def _current_base_url(self) -> str:
        provider = self._current_provider()
        return str(self.config_data.get("base_urls", {}).get(provider) or DEFAULT_PROVIDERS[provider]["base_url"])

    def _current_reasoning_effort(self, provider: str | None = None, model: str | None = None) -> str:
        provider = provider or self._current_provider()
        if provider not in DEFAULT_PROVIDERS or not DEFAULT_PROVIDERS[provider].get("supports_reasoning"):
            return ""
        model = (model or self.model_var.get().strip() or DEFAULT_PROVIDERS[provider]["default_model"]).strip()
        return str(self.config_data.setdefault("reasoning_efforts", {}).setdefault(provider, {}).get(model, "")).strip()

    def _save_provider_state(self) -> None:
        provider = self._current_provider()
        model = self.model_var.get().strip()
        self.config_data["provider"] = provider
        if model:
            self.config_data.setdefault("last_model", {})[provider] = model
            models = self.config_data.setdefault("models", {}).setdefault(provider, [])
            if model not in models:
                models.append(model)
            display_map = self.config_data.setdefault("model_display_names", {}).setdefault(provider, {})
            display_map.setdefault(model, model)
            if DEFAULT_PROVIDERS[provider].get("supports_reasoning"):
                effort = reasoning_value(self.reasoning_effort_var.get()) if hasattr(self, "reasoning_effort_var") else ""
                self.config_data.setdefault("reasoning_efforts", {}).setdefault(provider, {})[model] = effort
        self.config_data.setdefault("base_urls", {})[provider] = self.base_url_var.get().strip()
        save_config(self.config_data)

    def _best_font_family(self) -> str:
        families = set(tkfont.families(self))
        for name in ("Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", "Arial"):
            if name in families:
                return name
        return "TkDefaultFont"

    def _best_english_font_family(self) -> str:
        families = set(tkfont.families(self))
        for name in ("Segoe UI", "Arial", "Calibri", "Microsoft YaHei UI"):
            if name in families:
                return name
        return "TkDefaultFont"

    def _best_font(self, size: int):
        return ("Microsoft YaHei UI", size)

    def _setup_combo_style(self) -> None:
        try:
            style = ttk.Style(self)
            style.configure("TCombobox", fieldbackground=CARD_SOFT, background=CARD_SOFT, foreground=TEXT)
        except Exception:
            pass

    def on_provider_changed(self, _event=None) -> None:
        provider = self._current_provider()
        self.config_data["provider"] = provider
        self.base_url_var.set(self._current_base_url())
        model = str(self.config_data.get("last_model", {}).get(provider) or DEFAULT_PROVIDERS[provider]["default_model"])
        self.model_var.set(model)
        self.reasoning_effort_var.set(reasoning_label(self._current_reasoning_effort(provider, model)))
        if hasattr(self, "model_combo"):
            self.model_combo.configure(values=self._current_model_labels())
        self._save_provider_state()
        self._refresh_model_summary()
        self.set_status(f"已切换到 {provider}")

    def add_custom_model(self) -> None:
        provider = self._current_provider()
        model = simpledialog.askstring("添加模型", f"请输入 {provider} 模型ID:", parent=self)
        if not model or not model.strip():
            return
        model = model.strip()
        models = self.config_data.setdefault("models", {}).setdefault(provider, [])
        if model in models:
            messagebox.showinfo("添加模型", "该模型ID已经存在。", parent=self)
            return
        display_name = simpledialog.askstring("添加模型", "请输入显示名:", initialvalue=model, parent=self)
        if not display_name or not display_name.strip():
            return
        display_name = display_name.strip()
        if self._display_name_exists(provider, display_name):
            messagebox.showwarning("显示名重复", f"显示名已经存在，请换一个名称。\n\n{display_name}", parent=self)
            return
        self.config_data.setdefault("model_display_names", {}).setdefault(provider, {})[model] = display_name
        models.append(model)
        self.model_var.set(model)
        if hasattr(self, "model_combo"):
            self.model_combo.configure(values=self._current_model_labels())
        self._save_provider_state()
        self._refresh_model_summary()
        self.set_status(f"已添加模型: {display_name}", is_error=False)

    def set_base_url(self) -> None:
        provider = self._current_provider()
        current = self.base_url_var.get().strip() or DEFAULT_PROVIDERS[provider]["base_url"]
        tip = "OpenAI 官方接口通常留空；DeepSeek 默认 https://api.deepseek.com；Z.AI 默认 https://api.z.ai/api/paas/v4；自定义提供商请填 OpenAI-compatible Base URL。"
        url = simpledialog.askstring("设置 API 地址", f"{tip}\n\n当前提供商: {provider}\nBase URL:", initialvalue=current, parent=self)
        if url is None:
            return
        self.base_url_var.set(url.strip())
        self.config_data.setdefault("base_urls", {})[provider] = url.strip()
        save_config(self.config_data)
        self._refresh_model_summary()
        self.set_status("API 地址已保存", is_error=False)

    def _build_ui(self) -> None:
        root = tk.Frame(self, bg=BG)
        root.pack(fill="both", expand=True, padx=22, pady=18)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        card = Card(root, radius=18)
        card.grid(row=0, column=0, rowspan=2, sticky="nsew")
        panel = card.inner
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(2, weight=1)
        panel.rowconfigure(4, weight=1)

        header = tk.Frame(panel, bg=CARD)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 8))
        header.columnconfigure(2, weight=1)

        logo = tk.Canvas(header, width=46, height=46, bg=CARD, highlightthickness=0, bd=0)
        logo.grid(row=0, column=0, padx=(0, 12))
        round_rect(logo, 1, 1, 45, 45, 12, fill=BLUE, outline=BLUE)
        logo.create_text(23, 23, text="AI", fill="white", font=self.font_logo)
        tk.Label(header, text=APP_TITLE, bg=CARD, fg=TEXT, font=self.font_title).grid(row=0, column=1, sticky="w")

        self._setup_combo_style()
        self.model_summary = tk.Label(header, text="", bg=CARD, fg=MUTED, font=self.font_btn)
        self.model_summary.grid(row=0, column=3, padx=(12, 8), sticky="e")
        RoundedButton(header, "模型设置", self.open_model_settings, width=96, font=self.font_btn).grid(row=0, column=4, padx=(0, 10))
        ToggleSwitch(header, self.top_var, self.toggle_topmost, font=self.font_btn, on_text="置顶悬浮", off_text="未置顶", width=106).grid(row=0, column=5, padx=(0, 8))
        ToggleSwitch(header, self.startup_var, self.toggle_startup, font=self.font_btn, on_text="开机自启", off_text="手动启动", width=116).grid(row=0, column=6, padx=(0, 0))
        self._refresh_model_summary()

        intro = tk.Label(
            panel,
            text="输入后自动翻译，支持专业化、程序员化和口语化；模型、API 地址和 Key 请在右上角模型设置中配置。",
            bg=CARD,
            fg=MUTED,
            font=self.font_small,
        )
        intro.grid(row=1, column=0, sticky="w", padx=22, pady=(0, 8))

        self.zh_section = TranslateSection(self, panel, "中文", "English", "请输入中文内容...")
        self.zh_section.grid(row=2, column=0, sticky="nsew", padx=4)

        sep = tk.Frame(panel, bg=BORDER, height=1)
        sep.grid(row=3, column=0, sticky="ew", padx=22, pady=4)

        self.en_section = TranslateSection(self, panel, "English", "中文", "请输入 English 内容...")
        self.en_section.grid(row=4, column=0, sticky="nsew", padx=4)

        footer = tk.Frame(panel, bg=CARD)
        footer.grid(row=5, column=0, sticky="ew", padx=22, pady=(0, 14))
        footer.columnconfigure(0, weight=1)
        self.status = tk.Label(footer, text="等待输入", bg=CARD, fg=MUTED, font=self.font_small)
        self.status.grid(row=0, column=0, sticky="w")
        tk.Label(footer, text="AI 翻译仅供参考，重要内容请人工核对", bg=CARD, fg=MUTED, font=self.font_small).grid(row=0, column=1, sticky="e")

    def _refresh_model_summary(self) -> None:
        if not hasattr(self, "model_summary"):
            return
        provider = self._current_provider()
        model = self.model_var.get().strip() or DEFAULT_PROVIDERS[provider]["default_model"]
        display_name = self._model_display_name(provider, model)
        effort = self._current_reasoning_effort(provider, model)
        text = f"{provider} / {display_name}" if display_name else provider
        if effort and effort.casefold() not in text.casefold():
            text = f"{text} / {effort}"
        if len(text) > 42:
            text = text[:39] + "..."
        self.model_summary.configure(text=text)

    def open_model_settings(self) -> None:
        ModelSettingsDialog(self)

    def toggle_topmost(self) -> None:
        self.attributes("-topmost", bool(self.top_var.get()))
        self.set_status("已开启置顶悬浮" if self.top_var.get() else "已关闭置顶悬浮")

    def toggle_startup(self) -> None:
        enabled = bool(self.startup_var.get())
        try:
            set_startup_enabled(enabled)
        except Exception as exc:
            self.startup_var.set(not enabled)
            messagebox.showerror("设置失败", f"开机启动设置失败。\n\n原因: {exc}", parent=self)
            self.set_status("开机启动设置失败", is_error=True)
            return

        self.set_status("已开启开机自启" if enabled else "已改为手动启动")

    def set_status(self, text: str, is_error: bool | None = None) -> None:
        color = ERROR if is_error else OK if is_error is False else MUTED
        self.status.configure(text=text, fg=color)

    def ensure_api_key(self) -> bool:
        provider = self._current_provider()
        env_name = DEFAULT_PROVIDERS[provider].get("env_key", "")
        env_key = os.environ.get(env_name, "").strip() if env_name else ""
        if env_key:
            self.api_key_cache[provider] = env_key
            self.set_status(f"已使用环境变量 {env_name} 中的 API Key")
            return True

        if self.api_key_cache.get(provider):
            return True

        try:
            saved_key = read_saved_api_key(provider)
        except Exception as exc:
            messagebox.showerror("读取失败", str(exc), parent=self)
            saved_key = ""

        if saved_key:
            self.api_key_cache[provider] = saved_key
            self.set_status(f"已读取 {provider} 保存的 API Key")
            return True

        return self.reset_api_key(show_success=True)

    def reset_api_key(self, show_success: bool = True, parent=None) -> bool:
        parent = parent or self
        provider = self._current_provider()
        key = simpledialog.askstring("设置 API Key", f"请输入 {provider} API Key:", show="*", parent=parent)
        if not key or not key.strip():
            self.set_status("未设置 API Key", is_error=True)
            return False

        key = key.strip()
        try:
            location = save_api_key(provider, key)
        except Exception as exc:
            messagebox.showerror("保存失败", f"API Key 没有保存成功。\n\n原因: {exc}", parent=self)
            self.set_status("API Key 保存失败", is_error=True)
            return False

        self.api_key_cache[provider] = key
        self.set_status(f"{provider} API Key 已保存到 {location}", is_error=False)
        if show_success:
            messagebox.showinfo("已保存", f"{provider} API Key 已保存到 {location}。", parent=parent)
        return True

    def translate_api(self, text: str, source: str, target: str, style: str) -> str:
        provider = self._current_provider()
        model = self.model_var.get().strip() or DEFAULT_PROVIDERS[provider]["default_model"]
        model, inferred_effort = normalize_openai_model_id(provider, model)
        if inferred_effort:
            self.model_var.set(model)
            self.reasoning_effort_var.set(reasoning_label(inferred_effort))
            self.config_data.setdefault("reasoning_efforts", {}).setdefault(provider, {})[model] = inferred_effort
        base_url = self.base_url_var.get().strip()
        endpoint = DEFAULT_PROVIDERS[provider].get("endpoint", "chat")
        if provider == "Custom" and not base_url:
            raise RuntimeError("Custom 提供商必须先点击 设置地址，填写 OpenAI-compatible Base URL。")

        reasoning_effort = self._current_reasoning_effort(provider, model)
        self._save_provider_state()
        cache_key = (provider, model, reasoning_effort, base_url, source, target, style, text)
        if cache_key in self.cache:
            return self.cache[cache_key]

        env_name = DEFAULT_PROVIDERS[provider].get("env_key", "")
        api_key = self.api_key_cache.get(provider) or (os.environ.get(env_name, "").strip() if env_name else "")
        if not api_key:
            raise RuntimeError(f"未设置 {provider} API Key，请点击 设置Key 输入并保存。")

        from openai import OpenAI

        style_map = {
            "professional": "formal, professional, suitable for technical or business documents",
            "spoken": "natural, fluent, colloquial, suitable for daily conversation",
            "programmer": (
                "developer-oriented, concise and technical. Use common software engineering terms, "
                "keep code, commands, APIs, class names, function names, variable names, paths, errors and logs unchanged, "
                "and make the translation read like developer documentation, README, commit message, issue comment, or engineering communication"
            ),
        }
        style_desc = style_map.get(style, style_map["professional"])
        instructions = (
            "You are a professional translation engine. "
            "Keep the original meaning accurate. Do not add explanations. "
            "Preserve code, commands, variables, paths, IP addresses, product names, and proper nouns when appropriate. "
            "Output only the translated text."
        )
        prompt = f"Translate from {source} to {target}.\nStyle: {style_desc}.\n\nText:\n{text}"
        client_kwargs: Dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        client = OpenAI(**client_kwargs)

        if endpoint == "responses" and provider == "OpenAI":
            request_kwargs: Dict[str, Any] = {
                "model": model,
                "instructions": instructions,
                "input": prompt,
            }
            if reasoning_effort:
                request_kwargs["reasoning"] = {"effort": reasoning_effort}
            response = client.responses.create(**request_kwargs)
            result = response.output_text.strip()
        else:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            result = (response.choices[0].message.content or "").strip()

        self.cache[cache_key] = result
        return result


def main() -> None:
    app = TranslateApp()
    app.mainloop()


if __name__ == "__main__":
    main()
