#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 翻译助手
Python 3.11.9
依赖: pip install openai "httpx[socks]" pypdf
API Key: 首次启动弹窗输入，保存到 Windows 凭据管理器
"""

import os
import sys
import json
import ctypes
import subprocess
import ctypes.wintypes as wintypes
import threading
import unicodedata
import io
import re
from urllib.parse import urljoin

import httpx
from datetime import date, datetime, timedelta, timezone
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import simpledialog, messagebox, ttk
from typing import Dict, Tuple, Callable, Any

try:
    import socksio as _SOCKSIO
except ImportError:
    _SOCKSIO = None

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

APP_TITLE = "AI 翻译助手"
APP_ICON_FILE = "ai_translate_icon.ico"
MAX_CHARS = 5000
DEBOUNCE_MS = 800
UI_SCALE = 1.0

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
HAWAII_HOLIDAY_PAGE = "https://dhrd.hawaii.gov/state-observed-holidays/"

def get_app_dir() -> Path:
    """Return the directory where the script or frozen exe is located."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


APP_DIR = get_app_dir()
CONFIG_FILE = APP_DIR / "config.json"
HAWAII_HOLIDAY_CACHE_FILE = APP_DIR / "hawaii_holidays_cache.json"
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
PROXY_MODE_LABELS = ["自动检测", "手动代理", "不使用代理"]
PROXY_LABEL_TO_MODE = {"自动检测": "auto", "手动代理": "manual", "不使用代理": "none"}
PROXY_MODE_TO_LABEL = {value: key for key, value in PROXY_LABEL_TO_MODE.items()}
PROXY_ENV_NAMES = ("ALL_PROXY", "HTTPS_PROXY", "HTTP_PROXY", "all_proxy", "https_proxy", "http_proxy")


def proxy_mode_label(value: str) -> str:
    return PROXY_MODE_TO_LABEL.get((value or "auto").strip(), "自动检测")


def proxy_mode_value(label: str) -> str:
    return PROXY_LABEL_TO_MODE.get((label or "自动检测").strip(), "auto")


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
    """Enable crisp DPI-aware rendering before Tk creates the first window."""
    if sys.platform != "win32":
        return

    # Windows 10+: best result for high-DPI and mixed-DPI monitors.
    try:
        user32 = ctypes.windll.user32
        if hasattr(user32, "SetProcessDpiAwarenessContext"):
            if user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
                return
    except Exception:
        pass

    # Windows 8.1+: per-monitor DPI awareness.
    try:
        shcore = ctypes.windll.shcore
        shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass

    # Windows 7 fallback: system DPI awareness.
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def get_window_dpi(hwnd: int | None = None) -> int:
    """Return the current DPI for the window, falling back to 96."""
    if sys.platform != "win32":
        return 96

    user32 = ctypes.windll.user32

    try:
        if hwnd and hasattr(user32, "GetDpiForWindow"):
            dpi = int(user32.GetDpiForWindow(wintypes.HWND(hwnd)))
            if dpi > 0:
                return dpi
    except Exception:
        pass

    try:
        if hasattr(user32, "GetDpiForSystem"):
            dpi = int(user32.GetDpiForSystem())
            if dpi > 0:
                return dpi
    except Exception:
        pass

    try:
        hdc = user32.GetDC(0)
        if hdc:
            LOGPIXELSX = 88
            dpi = int(ctypes.windll.gdi32.GetDeviceCaps(hdc, LOGPIXELSX))
            user32.ReleaseDC(0, hdc)
            if dpi > 0:
                return dpi
    except Exception:
        pass

    return 96


def set_ui_scale(scale: float) -> None:
    """Set the pixel scaling factor used by custom Canvas widgets."""
    global UI_SCALE
    UI_SCALE = max(1.0, min(float(scale), 2.5))


def px(value: int | float) -> int:
    """Scale a raw pixel value for the current DPI."""
    return max(1, int(round(float(value) * UI_SCALE)))


def apply_tk_dpi_scaling(root: tk.Tk) -> float:
    """Apply Tk point scaling and return the DPI scale ratio."""
    dpi = get_window_dpi(root.winfo_id())
    scale = max(1.0, min(dpi / 96.0, 2.5))
    set_ui_scale(scale)

    try:
        root.tk.call("tk", "scaling", dpi / 72.0)
    except Exception:
        pass

    return scale


def has_socks_proxy() -> bool:
    for name in PROXY_ENV_NAMES:
        value = os.environ.get(name, "").strip().lower()
        if value.startswith(("socks4://", "socks5://", "socks5h://")):
            return True
    return False


def ensure_socks_proxy_support() -> None:
    if has_socks_proxy() and _SOCKSIO is None:
        raise RuntimeError(
            "当前启用了 SOCKS 代理，但缺少 socksio 依赖。"
            "请执行 pip install \"httpx[socks]\"，然后重新打包 exe。"
        )



def _proxy_env_exists() -> bool:
    for name in PROXY_ENV_NAMES:
        if os.environ.get(name, "").strip():
            return True
    return False


def _normalize_proxy_url(value: str, default_scheme: str = "http") -> str:
    value = value.strip()
    if not value:
        return ""
    low = value.lower()
    if low.startswith(("http://", "https://", "socks4://", "socks5://", "socks5h://")):
        return value
    return f"{default_scheme}://{value}"


def _parse_windows_proxy_server(proxy_server: str) -> Dict[str, str]:
    """Parse WinINet ProxyServer and convert it to HTTPX/OpenAI environment variables."""
    proxy_server = proxy_server.strip()
    proxies: Dict[str, str] = {}
    if not proxy_server:
        return proxies

    parts = [p.strip() for p in proxy_server.split(";") if p.strip()]
    has_protocol_map = any("=" in p for p in parts)

    if not has_protocol_map:
        proxy_url = _normalize_proxy_url(proxy_server, "http")
        proxies["HTTP_PROXY"] = proxy_url
        proxies["HTTPS_PROXY"] = proxy_url
        return proxies

    parsed: Dict[str, str] = {}
    for part in parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        key = key.strip().lower()
        value = value.strip()
        if not value:
            continue
        parsed[key] = value

    if parsed.get("http"):
        proxies["HTTP_PROXY"] = _normalize_proxy_url(parsed["http"], "http")
    if parsed.get("https"):
        proxies["HTTPS_PROXY"] = _normalize_proxy_url(parsed["https"], "http")

    # WinINet uses "socks=host:port". For HTTPX/OpenAI, use ALL_PROXY.
    if parsed.get("socks"):
        socks_url = _normalize_proxy_url(parsed["socks"], "socks5")
        proxies.setdefault("ALL_PROXY", socks_url)
        proxies.setdefault("HTTP_PROXY", socks_url)
        proxies.setdefault("HTTPS_PROXY", socks_url)

    return proxies


def detect_windows_system_proxy() -> Tuple[Dict[str, str], str]:
    """Read current-user Windows proxy settings. PAC/auto-detect is reported but not parsed."""
    if sys.platform != "win32":
        return {}, "非 Windows 系统，未读取系统代理"

    try:
        import winreg
    except Exception as exc:
        return {}, f"系统代理读取失败: {exc}"

    path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            try:
                proxy_enable = int(winreg.QueryValueEx(key, "ProxyEnable")[0])
            except FileNotFoundError:
                proxy_enable = 0

            try:
                proxy_server = str(winreg.QueryValueEx(key, "ProxyServer")[0]).strip()
            except FileNotFoundError:
                proxy_server = ""

            try:
                auto_config_url = str(winreg.QueryValueEx(key, "AutoConfigURL")[0]).strip()
            except FileNotFoundError:
                auto_config_url = ""

            try:
                auto_detect = int(winreg.QueryValueEx(key, "AutoDetect")[0])
            except FileNotFoundError:
                auto_detect = 0
    except Exception as exc:
        return {}, f"系统代理读取失败: {exc}"

    if proxy_enable and proxy_server:
        proxies = _parse_windows_proxy_server(proxy_server)
        if proxies:
            proxy_text = proxies.get("HTTPS_PROXY") or proxies.get("HTTP_PROXY") or proxies.get("ALL_PROXY") or proxy_server
            return proxies, f"已检测并启用系统代理: {proxy_text}"
        return {}, "系统代理已开启，但代理地址为空"

    if auto_config_url:
        return {}, "检测到系统 PAC 代理脚本，当前版本不自动解析 PAC，请改用系统 HTTP/SOCKS 代理或 TUN 模式"

    if auto_detect:
        return {}, "检测到系统代理自动发现，当前版本不自动解析 WPAD，请改用系统 HTTP/SOCKS 代理或 TUN 模式"

    return {}, "未检测到系统代理"


def clear_proxy_env() -> None:
    for name in PROXY_ENV_NAMES:
        os.environ.pop(name, None)


def apply_proxy_url_to_env(proxy_url: str) -> str:
    proxy_url = _normalize_proxy_url(proxy_url.strip(), "http")
    if not proxy_url:
        return "手动代理地址为空，请在模型设置里填写代理地址"

    clear_proxy_env()
    low = proxy_url.lower()
    if low.startswith(("socks4://", "socks5://", "socks5h://")):
        os.environ["ALL_PROXY"] = proxy_url
        os.environ["HTTP_PROXY"] = proxy_url
        os.environ["HTTPS_PROXY"] = proxy_url
        return f"已使用手动 SOCKS 代理: {proxy_url}"

    os.environ["HTTP_PROXY"] = proxy_url
    os.environ["HTTPS_PROXY"] = proxy_url
    return f"已使用手动 HTTP 代理: {proxy_url}"


def apply_system_proxy_to_env() -> str:
    """Use existing env proxy first; otherwise import Windows system proxy into env for OpenAI/httpx."""
    if _proxy_env_exists():
        for name in ("HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY", "https_proxy", "http_proxy", "all_proxy"):
            value = os.environ.get(name, "").strip()
            if value:
                return f"已使用环境变量代理: {name}={value}"
        return "已使用环境变量代理"

    proxies, status = detect_windows_system_proxy()
    for name, value in proxies.items():
        if value:
            os.environ.setdefault(name, value)
    return status


def get_auto_proxy_display() -> Tuple[str, str]:
    """Return the automatically detected proxy value and a human-readable status."""
    for name in ("HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY", "https_proxy", "http_proxy", "all_proxy"):
        value = os.environ.get(name, "").strip()
        if value:
            return value, f"自动检测：环境变量 {name}"

    proxies, status = detect_windows_system_proxy()
    if proxies:
        value = proxies.get("HTTPS_PROXY") or proxies.get("HTTP_PROXY") or proxies.get("ALL_PROXY") or ""
        if value:
            return value, "自动检测：Windows 系统代理"

    return "", status




def apply_proxy_settings_to_env(cfg: Dict[str, Any]) -> str:
    proxy_cfg = cfg.setdefault("proxy", {})
    mode = str(proxy_cfg.get("mode", "auto")).strip() or "auto"
    url = str(proxy_cfg.get("url", "")).strip()

    if mode == "none":
        clear_proxy_env()
        return "当前网络代理：不使用代理"

    if mode == "manual":
        return apply_proxy_url_to_env(url)

    return apply_system_proxy_to_env()




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
        "proxy": {"mode": "auto", "url": ""},
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
                for key in ("provider", "last_model", "models", "model_display_names", "reasoning_efforts", "base_urls", "proxy"):
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

    proxy_cfg = cfg.setdefault("proxy", {})
    if proxy_cfg.get("mode") not in {"auto", "manual", "none"}:
        proxy_cfg["mode"] = "auto"
    proxy_cfg.setdefault("url", "")

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
    if "connection error" in low or "apiconnectionerror" in low or "connection refused" in low or "timed out" in low:
        return "连接失败：请打开模型设置，把网络代理改为手动代理，例如 http://127.0.0.1:7890 或 socks5://127.0.0.1:7891；同时检查防火墙、模型 API 地址和 Key。"
    if "socksio" in low or "socks proxy" in low or "httpx[socks]" in low:
        return "当前网络使用了 SOCKS 代理，但程序缺少 socksio 依赖。请安装 httpx[socks] 后重新打包 exe。"
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
        width = px(width)
        height = px(height)
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
        pad = px(1) if not self.pressed else px(2)
        round_rect(self, pad, pad, self.width - pad, self.height - pad, px(10), fill=fill, outline=outline, width=px(1))
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
        width = px(width)
        height = px(34)
        super().__init__(master, width=width, height=height, highlightthickness=0, bd=0, bg=master["bg"], cursor="hand2")
        self.height = height
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
        round_rect(self, px(1), px(1), self.width - px(1), self.height - px(1), self.height // 2, fill=fill, outline=outline, width=px(1))
        self.create_text(self.width // 2, self.height // 2, text=txt, fill=BLUE if active else MUTED, font=self.font)

    def _toggle(self, _event=None) -> None:
        self.variable.set(not self.variable.get())
        self._draw()
        self.command()


class SegmentedStyle(tk.Frame):
    def __init__(self, master, variable: tk.StringVar, command: Callable[[], None], font=None, include_hawaii: bool = False):
        super().__init__(master, bg=master["bg"])
        self.variable = variable
        self.command = command
        self.font = font
        self.buttons: dict[str, RoundedButton] = {}
        self._make_button("professional", "专业化", 0)
        self._make_button("programmer", "程序员化", 1)
        self._make_button("spoken", "口语化", 2)
        if include_hawaii:
            self._make_button("hawaii_local", "夏威夷本地英语", 3)

    def _make_button(self, value: str, text: str, col: int) -> None:
        btn = RoundedButton(self, text=text, command=lambda v=value: self.select(v), width=86, height=34, primary=False, font=self.font)
        btn.grid(row=0, column=col, padx=(0 if col == 0 else px(8), 0))
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
        height = px(height)
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
            padx=px(16),
            pady=px(14),
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
        self.style_var = tk.StringVar(value="hawaii_local" if title_right == "English" else "professional")

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        header = tk.Frame(self, bg=CARD)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=18, pady=(16, 10))
        header.columnconfigure(3, weight=1)

        tk.Label(header, text=title_left, bg=CARD, fg=BLUE, font=app.font_h2).grid(row=0, column=0, sticky="w")
        tk.Label(header, text="  →  ", bg=CARD, fg=TEXT, font=app.font_h2).grid(row=0, column=1)
        tk.Label(header, text=title_right, bg=CARD, fg=TEXT, font=app.font_h2).grid(row=0, column=2, sticky="w")

        SegmentedStyle(
            header,
            self.style_var,
            self.schedule_translate,
            font=app.font_btn,
            include_hawaii=(title_right == "English"),
        ).grid(row=0, column=4, padx=(12, 0))
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
        self.output_box.text.bind("<<Copy>>", self._copy_selected_output)
        self.output_box.text.bind("<Control-c>", self._copy_selected_output)
        self.output_box.text.bind("<Control-C>", self._copy_selected_output)
        self.output_box.text.bind("<Control-Insert>", self._copy_selected_output)

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
        if style := self.style_var.get():
            if style == "hawaii_local":
                self.app.remind_if_hawaii_off_hours()
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

    def _copy_text_with_guard(self, text: str) -> bool:
        text = text.strip()
        if not text:
            return False

        if self.title_right == "English" and self.app._contains_chinese_elements(text):
            messagebox.showerror(
                "禁止复制",
                "检测到英文翻译结果中仍存在中文元素或全角字符。\n\n"
                "为避免将不专业的内容发送给客户，本次复制已被阻止。\n"
                "请重新翻译后再复制。",
                parent=self.app,
            )
            self.app.set_status("复制已阻止：英文结果存在中文元素", is_error=True)
            return False

        self.clipboard_clear()
        self.clipboard_append(text)
        self.app.set_status("结果已复制")
        return True

    def _copy_selected_output(self, _event=None):
        try:
            selected = self.output_box.text.get("sel.first", "sel.last")
        except tk.TclError:
            return "break"
        self._copy_text_with_guard(selected)
        return "break"

    def copy_result(self) -> None:
        self._copy_text_with_guard(self.output_box.get())


class ModelSettingsDialog(tk.Toplevel):
    def __init__(self, app: "TranslateApp"):
        super().__init__(app)
        self.app = app
        self.title("模型设置")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(px(800), px(540))
        self.transient(app)
        self.grab_set()

        self.provider_var = tk.StringVar(value=app.provider_var.get())
        self.model_var = tk.StringVar(value=app.model_var.get())
        self.model_display_var = tk.StringVar(value=app._model_display_name(app._current_provider(), app.model_var.get()))
        self.reasoning_effort_var = tk.StringVar(
            value=reasoning_label(app._current_reasoning_effort(app._current_provider(), app.model_var.get()))
        )
        self.base_url_var = tk.StringVar(value=app.base_url_var.get())
        proxy_cfg = app.config_data.setdefault("proxy", {})
        self.proxy_mode_var = tk.StringVar(value=proxy_mode_label(str(proxy_cfg.get("mode", "auto"))))
        self.manual_proxy_url = str(proxy_cfg.get("url", "")).strip()
        self.proxy_url_var = tk.StringVar(value=self.manual_proxy_url)

        self._build_ui()
        self._refresh_provider_view()
        self._refresh_proxy_state()
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

        tk.Label(card, text="网络代理", bg=CARD, fg=MUTED, font=self.app.font_btn).grid(row=5, column=0, sticky="e", padx=(20, 10), pady=10)
        self.proxy_combo = ttk.Combobox(
            card,
            textvariable=self.proxy_mode_var,
            values=PROXY_MODE_LABELS,
            width=26,
            state="readonly",
            font=self.app.font_btn,
        )
        self.proxy_combo.grid(row=5, column=1, sticky="ew", padx=(0, 12), pady=10, ipady=6)
        self.proxy_combo.bind("<<ComboboxSelected>>", self._refresh_proxy_state)
        self.proxy_tip = tk.Label(card, text="", bg=CARD, fg=MUTED, font=self.app.font_small)
        self.proxy_tip.grid(row=5, column=2, sticky="w", padx=(0, 20), pady=10)

        tk.Label(card, text="代理地址", bg=CARD, fg=MUTED, font=self.app.font_btn).grid(row=6, column=0, sticky="e", padx=(20, 10), pady=10)
        self.proxy_entry = tk.Entry(
            card,
            textvariable=self.proxy_url_var,
            bg=CARD_SOFT,
            fg=TEXT,
            bd=1,
            relief="solid",
            insertbackground=BLUE,
            font=self.app.font_btn,
        )
        self.proxy_entry.grid(row=6, column=1, columnspan=2, sticky="ew", padx=(0, 20), pady=10, ipady=8)

        hint = (
            "添加模型时需要填写模型ID和显示名；显示名在同一提供商下不能重复。"
            "自动检测模式会把检测到的代理地址显示在代理地址框中，仅供查看，不允许修改。"
            "网络不通时建议把网络代理改为手动代理，例如 http://127.0.0.1:7890 或 socks5://127.0.0.1:7891。"
            "OpenAI 的 xhigh 是推理强度，不是模型名后缀；"
            "Custom 填 OpenAI-compatible Base URL。"
        )
        tk.Label(card, text=hint, bg=CARD, fg=MUTED, font=self.app.font_small, wraplength=px(760), justify="left").grid(
            row=7, column=0, columnspan=3, sticky="w", padx=20, pady=(6, 18)
        )

        btns = tk.Frame(card, bg=CARD)
        btns.grid(row=8, column=0, columnspan=3, sticky="ew", padx=20, pady=(0, 22))
        btns.columnconfigure(0, weight=1)
        RoundedButton(btns, "设置Key", lambda: self.app.reset_api_key(show_success=True, parent=self), width=92, font=self.app.font_btn).grid(row=0, column=1, padx=(0, 8))
        RoundedButton(btns, "保存", self.save_all, width=82, primary=True, font=self.app.font_btn).grid(row=0, column=2, padx=(0, 8))
        RoundedButton(btns, "关闭", self.close, width=82, font=self.app.font_btn).grid(row=0, column=3)

    def _center(self) -> None:
        self.update_idletasks()

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        width = min(px(920), max(px(760), screen_width - px(80)))
        # Keep the dialog compact. It is still resizable if more space is needed.
        height = min(px(640), max(px(540), screen_height - px(160)))

        parent_x = self.app.winfo_x()
        parent_y = self.app.winfo_y()
        parent_w = max(self.app.winfo_width(), width)
        parent_h = max(self.app.winfo_height(), height)

        x = parent_x + max((parent_w - width) // 2, 0)
        y = parent_y + max((parent_h - height) // 2, 0)
        x = max(0, min(x, screen_width - width))
        y = max(0, min(y, screen_height - height))
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _refresh_proxy_state(self, _event=None) -> None:
        mode = proxy_mode_value(self.proxy_mode_var.get())
        current_state = str(self.proxy_entry.cget("state")) if hasattr(self, "proxy_entry") else "normal"

        if current_state != "disabled":
            self.manual_proxy_url = self.proxy_url_var.get().strip()

        if mode == "manual":
            self.proxy_entry.configure(state="normal")
            self.proxy_url_var.set(self.manual_proxy_url)
            self.proxy_tip.configure(text="可填写 http:// 或 socks5://")
        elif mode == "none":
            self.proxy_entry.configure(state="normal")
            self.proxy_url_var.set("不使用代理")
            self.proxy_entry.configure(state="disabled")
            self.proxy_tip.configure(text="直连或 TUN 模式可选")
        else:
            detected_proxy, status = get_auto_proxy_display()
            self.proxy_entry.configure(state="normal")
            self.proxy_url_var.set(detected_proxy or status)
            self.proxy_entry.configure(state="disabled")
            self.proxy_tip.configure(text="自动检测结果，仅查看")

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
        proxy_mode = proxy_mode_value(self.proxy_mode_var.get())
        if proxy_mode == "manual":
            self.manual_proxy_url = self.proxy_url_var.get().strip()
        self.app.config_data["proxy"] = {
            "mode": proxy_mode,
            "url": self.manual_proxy_url,
        }
        self.app.proxy_status = apply_proxy_settings_to_env(self.app.config_data)
        self.app._save_provider_state()
        self.app._refresh_model_summary()
        self.app.set_status(f"模型设置已保存，{self.app.proxy_status}", is_error=False)

    def close(self) -> None:
        self.save_all()
        self.grab_release()
        self.destroy()


class TranslateApp(tk.Tk):
    def __init__(self):
        enable_high_dpi()
        set_windows_app_id()
        super().__init__()
        self.dpi_scale = apply_tk_dpi_scaling(self)
        self.title(APP_TITLE)
        self._set_app_icon()
        self.window_width = 1040
        self.window_height = 740
        self.geometry(f"{px(self.window_width)}x{px(self.window_height)}")
        self.minsize(px(960), px(660))
        self.configure(bg=BG)
        self.option_add("*Font", self._best_font(10))

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
        self.hawaii_online_holidays: Dict[date, list[str]] = self._builtin_hawaii_official_holidays()
        self.hawaii_holiday_source = "内置 DHRD 官方基线（2026-2028）"
        self.hawaii_holiday_updated_at = ""
        self._load_hawaii_holiday_cache()
        self.proxy_status = apply_proxy_settings_to_env(self.config_data)
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
        if self.proxy_status:
            self.set_status(self.proxy_status)
        self.maximize_window()
        self.after(300, self.ensure_api_key)
        self.after(800, self.refresh_hawaii_holidays_async)

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
            text="输入后自动翻译，中文转英文支持专业化、程序员化、口语化和夏威夷本地英语；模型、API 地址、Key 和网络代理请在右上角模型设置中配置。",
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

    @staticmethod
    def _nth_weekday(year: int, month: int, weekday: int, nth: int) -> date:
        """Return the nth weekday in a month. Monday is 0 and Sunday is 6."""
        first = date(year, month, 1)
        offset = (weekday - first.weekday()) % 7
        return first + timedelta(days=offset + (nth - 1) * 7)

    @staticmethod
    def _last_weekday(year: int, month: int, weekday: int) -> date:
        """Return the last weekday in a month. Monday is 0 and Sunday is 6."""
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        last = next_month - timedelta(days=1)
        return last - timedelta(days=(last.weekday() - weekday) % 7)

    @staticmethod
    def _observed_fixed_holiday(year: int, month: int, day: int) -> date:
        """Return the weekday-observed date for a fixed Hawaii state holiday."""
        holiday = date(year, month, day)
        if holiday.weekday() == 5:
            return holiday - timedelta(days=1)
        if holiday.weekday() == 6:
            return holiday + timedelta(days=1)
        return holiday

    @staticmethod
    def _easter_sunday(year: int) -> date:
        """Calculate Gregorian Easter Sunday."""
        a = year % 19
        b = year // 100
        c = year % 100
        d = b // 4
        e = b % 4
        f = (b + 8) // 25
        g = (b - f + 1) // 3
        h = (19 * a + b - d - g + 15) % 30
        i = c // 4
        k = c % 4
        l = (32 + 2 * e + 2 * i - h - k) % 7
        m = (a + 11 * h + 22 * l) // 451
        month = (h + l - 7 * m + 114) // 31
        day = ((h + l - 7 * m + 114) % 31) + 1
        return date(year, month, day)

    @classmethod
    def _hawaii_state_holidays(cls, year: int) -> Dict[date, str]:
        """Build Hawaii state observed holidays from statutory calendar rules."""
        holidays: Dict[date, str] = {}

        def add(day: date, name: str) -> None:
            holidays[day] = name

        add(cls._observed_fixed_holiday(year, 1, 1), "New Year's Day")
        add(cls._nth_weekday(year, 1, 0, 3), "Dr. Martin Luther King, Jr. Day")
        add(cls._nth_weekday(year, 2, 0, 3), "Presidents' Day")
        add(cls._observed_fixed_holiday(year, 3, 26), "Prince Jonah Kuhio Kalanianaole Day")
        add(cls._easter_sunday(year) - timedelta(days=2), "Good Friday")
        add(cls._last_weekday(year, 5, 0), "Memorial Day")
        add(cls._observed_fixed_holiday(year, 6, 11), "King Kamehameha I Day")
        add(cls._observed_fixed_holiday(year, 7, 4), "Independence Day")
        add(cls._nth_weekday(year, 8, 4, 3), "Statehood Day")
        add(cls._nth_weekday(year, 9, 0, 1), "Labor Day")

        if year % 2 == 0:
            first_monday = cls._nth_weekday(year, 11, 0, 1)
            add(first_monday + timedelta(days=1), "General Election Day")

        add(cls._observed_fixed_holiday(year, 11, 11), "Veterans' Day")
        add(cls._nth_weekday(year, 11, 3, 4), "Thanksgiving")
        add(cls._observed_fixed_holiday(year, 12, 25), "Christmas")
        return holidays

    @staticmethod
    def _normalize_holiday_text(value: str) -> str:
        value = value.replace("ʻ", "'").replace("’", "'").replace("‘", "'")
        value = re.sub(r"\s+", " ", value).strip()
        return value

    @classmethod
    def _parse_hawaii_holiday_text(cls, raw_text: str) -> tuple[Dict[date, list[str]], set[int]]:
        """Parse observed holiday rows directly from official DHRD text."""
        text = raw_text.replace("ʻ", "'").replace("’", "'").replace("‘", "'")
        if "HAWAI" not in text.upper() or "STATE HOLIDAYS" not in text.upper():
            raise ValueError("官方 PDF 内容校验失败")

        month_map = {
            "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
            "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
            "august": 8, "aug": 8, "september": 9, "sept": 9, "sep": 9,
            "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
        }
        weekday_map = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6,
        }
        header_re = re.compile(r"(?im)^\s*(20\d{2})\s+HAWAI[^\n]*STATE HOLIDAYS\s*$")
        row_re = re.compile(
            r"^\s*(?P<name>.+?)\s+"
            r"(?P<month>January|Jan\.?|February|Feb\.?|March|Mar\.?|April|Apr\.?|May|June|Jun\.?|July|Jul\.?|August|Aug\.?|September|Sept\.?|Sep\.?|October|Oct\.?|November|Nov\.?|December|Dec\.?)"
            r"\s+(?P<day>\d{1,2}),\s+"
            r"(?P<weekday>Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b",
            re.I,
        )

        headers = list(header_re.finditer(text))
        if not headers:
            raise ValueError("未识别到官方 PDF 年份区块")

        result: Dict[date, list[str]] = {}
        parsed_years: set[int] = set()
        for index, header in enumerate(headers):
            section_year = int(header.group(1))
            section_end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
            section = text[header.end():section_end]
            section_count = 0

            for raw_line in section.splitlines():
                line = re.sub(r"\s+", " ", raw_line).strip()
                if not line or line.upper().startswith("FOOTNOTES"):
                    continue
                match = row_re.match(line)
                if not match:
                    continue

                name = match.group("name").strip(" -:\t")
                month_key = match.group("month").lower().replace(".", "")
                month = month_map[month_key]
                day_num = int(match.group("day"))
                expected_weekday = weekday_map[match.group("weekday").lower()]

                candidates = []
                for candidate_year in (section_year, section_year - 1, section_year + 1):
                    try:
                        candidate = date(candidate_year, month, day_num)
                    except ValueError:
                        continue
                    if candidate.weekday() == expected_weekday:
                        candidates.append(candidate)

                if not candidates:
                    raise ValueError(
                        f"官方节假日日期与星期不一致: {name} {month_key} {day_num}, {match.group('weekday')}"
                    )

                observed = min(candidates, key=lambda d: (abs(d.year - section_year), d.year != section_year))
                if month == 12 and observed.year == section_year and section_year - 1 >= 2000:
                    try:
                        prior = date(section_year - 1, month, day_num)
                        if prior.weekday() == expected_weekday:
                            observed = prior
                    except ValueError:
                        pass

                names = result.setdefault(observed, [])
                if name not in names:
                    names.append(name)
                section_count += 1

            if section_count:
                parsed_years.add(section_year)

        return result, parsed_years

    @classmethod
    def _parse_hawaii_holiday_pdf(cls, pdf_bytes: bytes) -> Dict[date, list[str]]:
        """Parse and validate official Hawaii DHRD observed holiday rows."""
        if PdfReader is None:
            raise RuntimeError("缺少 pypdf，无法解析夏威夷官方节假日 PDF")

        reader = PdfReader(io.BytesIO(pdf_bytes))
        raw_text = "\n".join((page.extract_text() or "") for page in reader.pages)
        result, parsed_years = cls._parse_hawaii_holiday_text(raw_text)
        if not parsed_years:
            raise ValueError("官方 PDF 未解析到任何节假日")

        # DHRD annual tables normally contain at least 13 rows per year.
        # Use a conservative lower bound only to detect truncated or broken PDF extraction;
        # do not compare dates with locally calculated holidays, so official changes remain authoritative.
        for year in parsed_years:
            count = sum(1 for day in result if day.year in {year - 1, year})
            if count < 10:
                raise ValueError(f"官方 PDF {year} 年节假日解析数量异常，仅解析到 {count} 个日期")

        return result

    @staticmethod
    def _builtin_hawaii_official_holidays() -> Dict[date, list[str]]:
        """Built-in DHRD observed-holiday baseline for 2026-2028.

        This is a last-good official snapshot so holiday warnings remain available
        even when the DHRD site, network/proxy, or pypdf is temporarily unavailable.
        Online DHRD data and local statutory rules are still unioned on top of it.
        """
        rows = (
            # 2026 DHRD observed dates
            ("2026-01-01", "New Year's Day"),
            ("2026-01-19", "Dr. Martin Luther King, Jr. Day"),
            ("2026-02-16", "Presidents' Day"),
            ("2026-03-26", "Prince Jonah Kuhio Kalanianaole Day"),
            ("2026-04-03", "Good Friday"),
            ("2026-05-25", "Memorial Day"),
            ("2026-06-11", "King Kamehameha I Day"),
            ("2026-07-03", "Independence Day"),
            ("2026-08-21", "Statehood Day"),
            ("2026-09-07", "Labor Day"),
            ("2026-11-03", "General Election Day"),
            ("2026-11-11", "Veterans' Day"),
            ("2026-11-26", "Thanksgiving"),
            ("2026-12-25", "Christmas"),
            # 2027 DHRD observed dates
            ("2027-01-01", "New Year's Day"),
            ("2027-01-18", "Dr. Martin Luther King, Jr. Day"),
            ("2027-02-15", "Presidents' Day"),
            ("2027-03-26", "Prince Jonah Kuhio Kalanianaole Day"),
            ("2027-03-26", "Good Friday"),
            ("2027-05-31", "Memorial Day"),
            ("2027-06-11", "King Kamehameha I Day"),
            ("2027-07-05", "Independence Day"),
            ("2027-08-20", "Statehood Day"),
            ("2027-09-06", "Labor Day"),
            ("2027-11-11", "Veterans' Day"),
            ("2027-11-25", "Thanksgiving"),
            ("2027-12-24", "Christmas"),
            # 2028 DHRD observed dates. New Year's Day is observed on 2027-12-31.
            ("2027-12-31", "New Year's Day (2028 observed)"),
            ("2028-01-17", "Dr. Martin Luther King, Jr. Day"),
            ("2028-02-21", "Presidents' Day"),
            ("2028-03-27", "Prince Jonah Kuhio Kalanianaole Day"),
            ("2028-04-14", "Good Friday"),
            ("2028-05-29", "Memorial Day"),
            ("2028-06-12", "King Kamehameha I Day"),
            ("2028-07-04", "Independence Day"),
            ("2028-08-18", "Statehood Day"),
            ("2028-09-04", "Labor Day"),
            ("2028-11-07", "General Election Day"),
            ("2028-11-10", "Veterans' Day"),
            ("2028-11-23", "Thanksgiving"),
            ("2028-12-25", "Christmas"),
        )
        result: Dict[date, list[str]] = {}
        for day_text, name in rows:
            result.setdefault(date.fromisoformat(day_text), []).append(name)
        return result

    def _load_hawaii_holiday_cache(self) -> None:
        try:
            if not HAWAII_HOLIDAY_CACHE_FILE.exists():
                return
            raw = json.loads(HAWAII_HOLIDAY_CACHE_FILE.read_text(encoding="utf-8"))
            loaded: Dict[date, list[str]] = {}
            for day_text, names in raw.get("holidays", {}).items():
                day = date.fromisoformat(day_text)
                if isinstance(names, str):
                    names = [names]
                if isinstance(names, list) and names:
                    loaded[day] = [str(x) for x in names if str(x).strip()]
            if loaded:
                merged = dict(self.hawaii_online_holidays)
                for day, names in loaded.items():
                    current = merged.setdefault(day, [])
                    for name in names:
                        if name not in current:
                            current.append(name)
                self.hawaii_online_holidays = merged
                cached_source = str(raw.get("source", "")).strip()
                if cached_source:
                    self.hawaii_holiday_source = "内置 DHRD 官方基线 + 上次官方缓存"
                self.hawaii_holiday_updated_at = str(raw.get("updated_at", ""))
        except Exception:
            # Keep the built-in official baseline rather than dropping to an empty set.
            pass

    def _save_hawaii_holiday_cache(self, holidays: Dict[date, list[str]], source: str) -> None:
        payload = {
            "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": source,
            "holidays": {d.isoformat(): names for d, names in sorted(holidays.items())},
        }
        HAWAII_HOLIDAY_CACHE_FILE.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _fetch_url(self, url: str, timeout: float = 8.0) -> bytes:
        """Fetch DHRD data from the local machine using the app's proxy settings.

        The local app first applies its configured proxy/system proxy and performs
        the request with httpx. If that path fails, it retries once with a true
        local direct connection (trust_env=False). No external service is used.
        """
        headers = {"User-Agent": "AITranslateAssistant/1.0"}
        proxy_mode = str(self.config_data.get("proxy", {}).get("mode", "auto")).strip() or "auto"
        errors = []

        if proxy_mode != "none":
            try:
                self.proxy_status = apply_proxy_settings_to_env(self.config_data)
                ensure_socks_proxy_support()
                with httpx.Client(timeout=timeout, follow_redirects=True, trust_env=True) as client:
                    response = client.get(url, headers=headers)
                    response.raise_for_status()
                    self.hawaii_last_fetch_route = "本机代理/系统代理"
                    return response.content
            except Exception as exc:
                errors.append(f"本机代理请求失败: {exc}")

        try:
            with httpx.Client(timeout=timeout, follow_redirects=True, trust_env=False) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                self.hawaii_last_fetch_route = "本机直连"
                return response.content
        except Exception as exc:
            errors.append(f"本机直连失败: {exc}")

        raise RuntimeError("；".join(errors) or "本机网络请求失败")

    def _fetch_hawaii_holidays_online(self) -> tuple[Dict[date, list[str]], str]:
        page_html = self._fetch_url(HAWAII_HOLIDAY_PAGE).decode("utf-8", errors="ignore")
        pdf_links = re.findall(r"href=[\"']([^\"']*State-Holidays[^\"']*\.pdf)[\"']", page_html, re.I)
        pdf_urls = []
        for href in pdf_links:
            url = urljoin(HAWAII_HOLIDAY_PAGE, href)
            if url not in pdf_urls:
                pdf_urls.append(url)
        if not pdf_urls:
            raise RuntimeError("夏威夷 DHRD 页面未找到官方节假日 PDF")

        merged: Dict[date, list[str]] = {}
        used_sources = []
        errors = []
        for pdf_url in pdf_urls[:6]:
            try:
                parsed = self._parse_hawaii_holiday_pdf(self._fetch_url(pdf_url))
                for day, names in parsed.items():
                    current = merged.setdefault(day, [])
                    for name in names:
                        if name not in current:
                            current.append(name)
                used_sources.append(pdf_url)
            except Exception as exc:
                errors.append(f"{pdf_url}: {exc}")

        current_year = datetime.now(timezone(timedelta(hours=-10))).year
        if not any(d.year in {current_year, current_year + 1} for d in merged):
            detail = "; ".join(errors[:2])
            raise RuntimeError("未获取到当前或下一年度官方节假日" + (f"：{detail}" if detail else ""))
        return merged, " | ".join(used_sources)

    def refresh_hawaii_holidays_async(self) -> None:
        threading.Thread(target=self._refresh_hawaii_holidays_worker, daemon=True).start()

    def _refresh_hawaii_holidays_worker(self) -> None:
        if PdfReader is None:
            self.after(0, self.set_status, "夏威夷节假日：缺少 pypdf，使用内置 DHRD 官方基线 + 本地规则")
            return
        try:
            holidays, source = self._fetch_hawaii_holidays_online()
            merged = dict(self.hawaii_online_holidays)
            for day, names in holidays.items():
                current = merged.setdefault(day, [])
                for name in names:
                    if name not in current:
                        current.append(name)
            self._save_hawaii_holiday_cache(merged, source)
            self.hawaii_online_holidays = merged
            route = getattr(self, "hawaii_last_fetch_route", "本机网络")
            self.hawaii_holiday_source = f"DHRD 在线官方数据（{route}） + 内置官方基线"
            self.hawaii_holiday_updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            self.after(0, self.set_status, f"夏威夷节假日：DHRD 官方数据已更新（{route}）")
        except Exception as exc:
            self.after(
                0,
                self.set_status,
                "夏威夷节假日：联网更新失败，继续使用内置/缓存官方数据 + 本地规则",
            )

    @classmethod
    def _local_hawaii_holiday_names(cls, day: date) -> list[str]:
        names = []
        for year in (day.year - 1, day.year, day.year + 1):
            name = cls._hawaii_state_holidays(year).get(day)
            if name and name not in names:
                names.append(name)
        return names

    def _hawaii_holiday_names(self, day: date) -> tuple[list[str], str]:
        """Return the union of official PDF holidays and local statutory-rule holidays."""
        official_names = list(self.hawaii_online_holidays.get(day, []))
        local_names = self._local_hawaii_holiday_names(day)

        names = []
        for name in official_names + local_names:
            if name and name not in names:
                names.append(name)

        if official_names and local_names:
            source = "夏威夷州政府官方数据 + 本地法定规则"
        elif official_names:
            source = "夏威夷州政府官方数据"
        elif local_names:
            source = "本地法定规则"
        elif self.hawaii_online_holidays:
            source = "DHRD 官方数据与本地法定规则均未命中"
        else:
            source = "内置 DHRD 官方基线可用，本地法定规则未命中"

        return names, source

    def remind_if_hawaii_off_hours(self) -> None:
        """Warn on every Hawaii-local translation outside work time or on a state holiday."""
        now = datetime.now(timezone(timedelta(hours=-10)))
        local_day = now.date()
        holiday_names, holiday_source = self._hawaii_holiday_names(local_day)
        is_weekday = now.weekday() < 5
        is_worktime = 9 <= now.hour < 17

        reasons = []
        if holiday_names:
            reasons.append("今天是夏威夷州节假日：" + " / ".join(holiday_names))
        if not is_weekday:
            reasons.append("今天是周末")
        elif not is_worktime:
            reasons.append("当前不在常规工作时间：周一至周五 09:00-17:00")

        if not reasons:
            return

        dialog = tk.Toplevel(self)
        dialog.title("夏威夷联系时间提醒")
        dialog.configure(bg="#fff7ed")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        try:
            dialog.iconbitmap(str(resource_path(APP_ICON_FILE)))
        except Exception:
            pass

        width, height = px(620), px(390)
        self.update_idletasks()
        x = self.winfo_rootx() + max(20, (self.winfo_width() - width) // 2)
        y = self.winfo_rooty() + max(20, (self.winfo_height() - height) // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")

        outer = tk.Frame(dialog, bg="#fff7ed", padx=px(28), pady=px(24))
        outer.pack(fill="both", expand=True)

        tk.Label(
            outer,
            text="⚠ 不建议现在联系夏威夷客户",
            bg="#fff7ed",
            fg="#b42318",
            font=("Microsoft YaHei UI", 17, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, px(14)))

        tk.Label(
            outer,
            text="当前夏威夷时间  " + now.strftime("%Y-%m-%d %H:%M"),
            bg="#fff7ed",
            fg="#111827",
            font=("Microsoft YaHei UI", 13, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, px(12)))

        alert_box = tk.Frame(outer, bg="#fee2e2", padx=px(18), pady=px(16))
        alert_box.pack(fill="x", pady=(0, px(14)))
        for reason in reasons:
            tk.Label(
                alert_box,
                text="• " + reason,
                bg="#fee2e2",
                fg="#991b1b",
                font=("Microsoft YaHei UI", 12, "bold"),
                anchor="w",
                justify="left",
                wraplength=px(520),
            ).pack(fill="x", pady=px(3))

        tk.Label(
            outer,
            text="节假日判定来源：" + holiday_source,
            bg="#fff7ed",
            fg="#6b7280",
            font=("Microsoft YaHei UI", 9),
            anchor="w",
            justify="left",
            wraplength=px(540),
        ).pack(fill="x")

        tk.Label(
            outer,
            text="翻译仍会继续，但请确认联系时间后再发送给客户。",
            bg="#fff7ed",
            fg="#92400e",
            font=("Microsoft YaHei UI", 11, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(px(16), px(16)))

        btn = tk.Button(
            outer,
            text="我知道了",
            command=dialog.destroy,
            bg="#b42318",
            fg="white",
            activebackground="#991b1b",
            activeforeground="white",
            relief="flat",
            bd=0,
            font=("Microsoft YaHei UI", 11, "bold"),
            padx=px(26),
            pady=px(8),
            cursor="hand2",
        )
        btn.pack(anchor="e")
        btn.focus_set()
        dialog.bind("<Return>", lambda _e: dialog.destroy())
        dialog.bind("<Escape>", lambda _e: dialog.destroy())
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        dialog.wait_window()

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

    @staticmethod
    def _normalize_english_output(value: str) -> str:
        """Normalize full-width forms and Chinese typography in English output."""
        value = unicodedata.normalize("NFKC", value)
        replacements = (
            ("……", "..."),
            ("——", "—"),
            ("，", ","),
            ("。", "."),
            ("！", "!"),
            ("？", "?"),
            ("：", ":"),
            ("；", ";"),
            ("、", ","),
            ("（", "("),
            ("）", ")"),
            ("【", "["),
            ("】", "]"),
            ("［", "["),
            ("］", "]"),
            ("｛", "{"),
            ("｝", "}"),
            ("“", '"'),
            ("”", '"'),
            ("‘", "'"),
            ("’", "'"),
            ("《", '"'),
            ("》", '"'),
            ("〈", '"'),
            ("〉", '"'),
            ("〔", "["),
            ("〕", "]"),
            ("﹏", "_"),
            ("　", " "),
        )
        for src, dst in replacements:
            value = value.replace(src, dst)
        return value

    @staticmethod
    def _contains_chinese_text(value: str) -> bool:
        """Return True when Han ideographs remain in an English result."""
        return bool(re.search(r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]", value))

    @staticmethod
    def _contains_chinese_elements(value: str) -> bool:
        """Return True when Chinese/CJK text, punctuation, or full-width forms remain."""
        if not value:
            return False

        patterns = (
            r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]",
            r"[\u3000-\u303F]",
            r"[\uFE10-\uFE1F]",
            r"[\uFE30-\uFE4F]",
            r"[\uFF01-\uFF60]",
            r"[\uFFE0-\uFFE6]",
        )
        return any(re.search(pattern, value) for pattern in patterns)

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

        self.proxy_status = apply_proxy_settings_to_env(self.config_data)
        ensure_socks_proxy_support()

        from openai import OpenAI

        style_map = {
            "professional": "formal, professional, suitable for technical or business documents",
            "spoken": "natural, fluent, colloquial, suitable for daily conversation",
            "hawaii_local": (
                "natural contemporary English as a local Hawaii resident would actually speak or write in the same situation. "
                "Follow local Hawaii communication habits, tone, phrasing, rhythm, and level of formality naturally. "
                "Do not force or artificially add Hawaii Pidgin, slang, Hawaiian words, or local expressions, but do not avoid them either. "
                "When Pidgin, slang, Hawaiian words, or local expressions are genuinely natural for the context, speaker, relationship, and message, use them naturally. "
                "The result should sound like something a real local person in Hawaii would naturally say, not a mainland-English sentence decorated with Hawaii vocabulary."
            ),
            "programmer": (
                "developer-oriented, concise and technical. The translation should read like developer documentation, "
                "README, commit message, issue comment, API document, or engineering communication. "
                "Do not translate existing English computer proper nouns, acronyms, product names, protocol names, "
                "library names, framework names, package names, command names, flags, environment variables, error codes, "
                "class names, function names, variable names, file names, paths, URLs, IP addresses, code snippets, logs, "
                "or stack traces. Keep their original spelling and letter case. "
                "Examples of terms to preserve when they already appear in the source: API, SDK, CLI, GUI, UI, JSON, XML, YAML, SQL, "
                "HTTP, HTTPS, TCP, UDP, DNS, TLS, SSH, Git, Docker, Kubernetes, Linux, Windows, Python, JavaScript, Rust, Go, "
                "OpenAI, DeepSeek, Z.AI, GLM, GPT, token, prompt, endpoint, request, response, commit, branch, issue, bug. "
                "For Chinese technical concepts, translate them into standard English software engineering terms when translating to English."
            ),
        }
        style_desc = style_map.get(style, style_map["professional"])
        base_instructions = (
            "You are a professional translation engine. "
            "Keep the original meaning accurate. Do not add explanations. "
            "Preserve code, commands, variables, paths, IP addresses, product names, and proper nouns when appropriate. "
            "Output only the translated text."
        )
        english_output_instructions = (
            " When the target language is English, the final output must be completely English-facing. "
            "Translate every Chinese-language element that carries meaning, including Chinese words, labels, date/time wording, units, currency wording, address wording, titles, and business expressions. "
            "Do not leave any Chinese Han characters in the final English output. If a Chinese proper noun has no known official English name, use a reasonable romanization rather than retaining Chinese characters. "
            "Use English punctuation, ASCII/full English-width letters and numbers, spacing, and typography conventions throughout. "
            "Do not retain Chinese or full-width punctuation such as ，。！？：；、“”‘’（）【】《》 or Chinese-style ellipses. "
            "Convert full-width Latin letters and digits to normal English forms. Preserve factual values exactly while expressing dates, times, numbers, currencies, units, addresses, and phone-related wording in natural English conventions. "
            "Before returning, silently scan the entire answer and make sure no Chinese-language text or Chinese formatting artifact remains."
        )
        programmer_instructions = (
            " When style is programmer-oriented, preserve existing English computer proper nouns and acronyms. "
            "Do not translate or localize code identifiers, commands, command-line flags, package names, library names, "
            "framework names, protocol names, product names, environment variables, error codes, file paths, URLs, logs, or stack traces. "
            "Translate the surrounding natural language only."
        )
        hawaii_instructions = (
            " When style is Hawaii-local English and the target language is English, translate the message the way a real local Hawaii resident would naturally communicate it in that specific context. "
            "Match the source speaker's intent, relationship, formality, and emotion while using locally natural Hawaii phrasing and rhythm. "
            "Do not deliberately inject Pidgin, slang, Hawaiian words, or stereotypical local expressions just to make the text sound Hawaiian. "
            "At the same time, never suppress or avoid Pidgin, slang, Hawaiian words, or local expressions when they would genuinely be the natural choice for a local speaker in that context. "
            "Choose them only when contextually appropriate, and otherwise use natural local English. Avoid caricature, parody, and mainland stereotypes of Hawaii speech. "
            "The final English output must contain no Chinese-language formatting artifacts. Convert Chinese punctuation and full-width punctuation to natural English punctuation, including commas, periods, colons, semicolons, question marks, exclamation marks, quotation marks, parentheses, brackets, ellipses, dashes, and list separators. "
            "Use English spacing and typography conventions throughout. Do not leave Chinese quotation marks, Chinese commas or periods, full-width colons or semicolons, Chinese-style parentheses, enumeration commas, or other CJK punctuation in the English result unless a character is part of an official proper name that must be preserved exactly. "
            "Also render dates, times, numbers, currency, units, addresses, phone-related wording, and similar business-facing expressions in natural English conventions when translation requires localization, while preserving factual values exactly. "
            "Before returning the answer, silently proofread the entire output and normalize any remaining Chinese punctuation or formatting into standard English form."
        )
        instructions = base_instructions
        if target.strip().lower() == "english":
            instructions += english_output_instructions
        if style == "programmer":
            instructions += programmer_instructions
        elif style == "hawaii_local":
            instructions += hawaii_instructions
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

        if target.strip().lower() == "english":
            result = self._normalize_english_output(result)
            if self._contains_chinese_text(result):
                cleanup_instructions = (
                    "Rewrite the supplied translation as natural English only. Preserve its meaning, tone, names, numbers, dates, amounts, and factual values. "
                    "Translate every remaining Chinese word or Han character into English. For a Chinese proper noun without a known official English name, romanize it rather than leaving Han characters. "
                    "Use normal English letters, digits, punctuation, spacing, units, currency, date/time, and business-writing conventions. "
                    "Return only the cleaned English text. Absolutely no Chinese Han characters may remain."
                )
                cleanup_prompt = "Clean this English translation so it contains no Chinese-language elements:\n\n" + result
                if endpoint == "responses" and provider == "OpenAI":
                    cleanup_kwargs: Dict[str, Any] = {
                        "model": model,
                        "instructions": cleanup_instructions,
                        "input": cleanup_prompt,
                    }
                    if reasoning_effort:
                        cleanup_kwargs["reasoning"] = {"effort": reasoning_effort}
                    cleanup_response = client.responses.create(**cleanup_kwargs)
                    result = cleanup_response.output_text.strip()
                else:
                    cleanup_response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": cleanup_instructions},
                            {"role": "user", "content": cleanup_prompt},
                        ],
                        temperature=0.1,
                    )
                    result = (cleanup_response.choices[0].message.content or "").strip()
                result = self._normalize_english_output(result)
                if self._contains_chinese_text(result):
                    raise RuntimeError("英文翻译结果仍包含中文内容，已停止输出，请重新翻译。")

        self.cache[cache_key] = result
        return result


def main() -> None:
    app = TranslateApp()
    app.mainloop()


if __name__ == "__main__":
    main()
