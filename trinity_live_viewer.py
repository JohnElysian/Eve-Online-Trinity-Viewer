# Python 2.7 live viewer executed by the EVE client's exefile /py mode.
#
# This is deliberately a thin native harness around the installed client's
# compiled Blue/Trinity runtime. CCP's public Trinity source tells us the scene
# driver contract, while the installed client still owns Granny, Blue, resource
# IO, SOF data loading, and DX11 device creation.

from __future__ import print_function

import ctypes
import ctypes.wintypes
import json
import math
import os
import random
import re
import sys
import time
import traceback


try:
    unicode
except NameError:
    unicode = str

SCRIPT_ROOT = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_ROOT not in sys.path:
    sys.path.insert(0, SCRIPT_ROOT)

from trinity_worker import (  # noqa: E402
    initialize_client_resource_cache,
    resolve_icon_scene_path,
)


POINTER_SIZE = ctypes.sizeof(ctypes.c_void_p)
LONG_PTR = ctypes.c_longlong if POINTER_SIZE == 8 else ctypes.c_long
UINT_PTR = ctypes.c_ulonglong if POINTER_SIZE == 8 else ctypes.c_ulong
LRESULT = LONG_PTR
WPARAM = UINT_PTR
LPARAM = LONG_PTR
HFONT = getattr(ctypes.wintypes, "HFONT", ctypes.wintypes.HANDLE)
HRESULT = getattr(ctypes.wintypes, "HRESULT", ctypes.c_long)
LPCVOID = getattr(ctypes.wintypes, "LPCVOID", ctypes.c_void_p)

USER32 = ctypes.windll.user32
KERNEL32 = ctypes.windll.kernel32
GDI32 = ctypes.windll.gdi32
UXTHEME = ctypes.windll.uxtheme
DWMAPI = ctypes.windll.dwmapi

WNDPROC = ctypes.WINFUNCTYPE(
    LRESULT,
    ctypes.wintypes.HWND,
    ctypes.wintypes.UINT,
    WPARAM,
    LPARAM,
)

NULL = 0
CS_HREDRAW = 2
CS_VREDRAW = 1
IDI_APPLICATION = 32512
IDC_ARROW = 32512
BLACK_BRUSH = 4
WS_OVERLAPPEDWINDOW = 13565952
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_CHILD = 0x40000000
WS_VISIBLE = 0x10000000
WS_BORDER = 0x00800000
WS_VSCROLL = 0x00200000
WS_TABSTOP = 0x00010000
LBS_NOTIFY = 0x00000001
LBS_NOINTEGRALHEIGHT = 0x00000100
BS_PUSHBUTTON = 0x00000000
BS_AUTOCHECKBOX = 0x00000003
CBS_DROPDOWNLIST = 0x00000003
ES_READONLY = 0x00000800
ES_AUTOHSCROLL = 0x00000080
CW_USEDEFAULT = -2147483648
SW_HIDE = 0
SW_SHOWNORMAL = 1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_SHOWWINDOW = 0x0040
PM_REMOVE = 1
WM_COMMAND = 273
WM_DESTROY = 2
WM_CLOSE = 16
WM_QUIT = 18
WM_SIZE = 5
WM_ERASEBKGND = 20
WM_KEYDOWN = 256
WM_LBUTTONDOWN = 513
WM_LBUTTONUP = 514
WM_RBUTTONDOWN = 516
WM_RBUTTONUP = 517
WM_MOUSEMOVE = 512
WM_MOUSEWHEEL = 522
WM_SETFONT = 48
WM_SETREDRAW = 11
WM_CTLCOLORLISTBOX = 308
WM_CTLCOLORBTN = 309
WM_CTLCOLORSTATIC = 312
WM_USER = 1024
VK_ESCAPE = 27
VK_RETURN = 13
VK_SPACE = 32
VK_ADD = 107
VK_SUBTRACT = 109
VK_OEM_PLUS = 187
VK_OEM_MINUS = 189
LB_ADDSTRING = 384
LB_INITSTORAGE = 424
LB_RESETCONTENT = 388
LB_SETCURSEL = 390
LB_GETCURSEL = 392
CB_ADDSTRING = 0x0143
CB_GETCURSEL = 0x0147
CB_RESETCONTENT = 0x014B
CB_SETCURSEL = 0x014E
BM_GETCHECK = 0x00F0
BM_SETCHECK = 0x00F1
BST_UNCHECKED = 0
BST_CHECKED = 1
LBN_DBLCLK = 2
CBN_SELCHANGE = 1
EN_CHANGE = 0x0300

CONTROL_PANEL_WIDTH = 430
MAX_VISIBLE_SEARCH_RESULTS = 240
SEARCH_DEBOUNCE_SECONDS = 0.16
IDC_ASSET_LIST = 1001
IDC_SEARCH = 1015
IDC_LOAD = 1002
IDC_PREV = 1003
IDC_NEXT = 1004
IDC_MODE = 1005
IDC_NEBULA = 1006
IDC_LIGHT_UP = 1007
IDC_LIGHT_DOWN = 1008
IDC_BOOSTERS = 1009
IDC_POST = 1010
IDC_AFTER = 1011
IDC_EXPLODE = 1012
IDC_ACTIVATE = 1014
IDC_ARM_MAX = 1016
IDC_FIRE_DUMMY = 1017
IDC_CLEAR_WEAPONS = 1018
IDC_FILTER_SHIPS = 1020
IDC_FILTER_GATES = 1021
IDC_FILTER_STATIONS = 1022
IDC_FILTER_STRUCTURES = 1023
IDC_FILTER_ANIMATIONS = 1024
IDC_FILTER_EXPLOSIONS = 1025
IDC_FILTER_PUBLISHED = 1026
IDC_ANIMATION_LIST = 1030
IDC_PLAY_ANIMATION = 1031
IDC_WEAPON_LIST = 1032
IDC_RESET_CAMERA = 1033
IDC_SEARCH_STATUS = 1201
IDC_ANIMATION_LABEL = 1202
IDC_WEAPON_LABEL = 1203

FILTER_CONTROLS = (
    (IDC_FILTER_SHIPS, "ships"),
    (IDC_FILTER_GATES, "gates"),
    (IDC_FILTER_STATIONS, "stations"),
    (IDC_FILTER_STRUCTURES, "structures"),
    (IDC_FILTER_ANIMATIONS, "animations"),
    (IDC_FILTER_EXPLOSIONS, "explosions"),
    (IDC_FILTER_PUBLISHED, "published"),
)

VISUAL_MODES = (
    ("white", 3),
    ("wireframe", 5),
    ("material", 0),
    ("texcoord", 1),
    ("overdraw", 4),
)


class WNDCLASS(ctypes.Structure):
    _fields_ = [
        ("style", ctypes.c_uint),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", ctypes.wintypes.HINSTANCE),
        ("hIcon", ctypes.wintypes.HICON),
        ("hCursor", ctypes.wintypes.HICON),
        ("hbrBackground", ctypes.wintypes.HBRUSH),
        ("lpszMenuName", ctypes.wintypes.LPCSTR),
        ("lpszClassName", ctypes.wintypes.LPCSTR),
    ]


class POINT(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_long),
        ("y", ctypes.c_long),
    ]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.wintypes.HWND),
        ("message", ctypes.wintypes.UINT),
        ("wParam", WPARAM),
        ("lParam", LPARAM),
        ("time", ctypes.wintypes.DWORD),
        ("pt", POINT),
    ]


USER32.DefWindowProcA.argtypes = [
    ctypes.wintypes.HWND,
    ctypes.wintypes.UINT,
    WPARAM,
    LPARAM,
]
USER32.DefWindowProcA.restype = LRESULT
USER32.RegisterClassA.argtypes = [ctypes.POINTER(WNDCLASS)]
USER32.RegisterClassA.restype = ctypes.wintypes.ATOM
USER32.CreateWindowExA.argtypes = [
    ctypes.wintypes.DWORD,
    ctypes.wintypes.LPCSTR,
    ctypes.wintypes.LPCSTR,
    ctypes.wintypes.DWORD,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.wintypes.HWND,
    ctypes.wintypes.HMENU,
    ctypes.wintypes.HINSTANCE,
    ctypes.wintypes.LPVOID,
]
USER32.CreateWindowExA.restype = ctypes.wintypes.HWND
USER32.ShowWindow.argtypes = [ctypes.wintypes.HWND, ctypes.c_int]
USER32.ShowWindow.restype = ctypes.wintypes.BOOL
USER32.UpdateWindow.argtypes = [ctypes.wintypes.HWND]
USER32.UpdateWindow.restype = ctypes.wintypes.BOOL
USER32.GetClientRect.argtypes = [ctypes.wintypes.HWND, ctypes.POINTER(RECT)]
USER32.GetClientRect.restype = ctypes.wintypes.BOOL
USER32.GetWindowRect.argtypes = [ctypes.wintypes.HWND, ctypes.POINTER(RECT)]
USER32.GetWindowRect.restype = ctypes.wintypes.BOOL
USER32.MoveWindow.argtypes = [
    ctypes.wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.wintypes.BOOL,
]
USER32.MoveWindow.restype = ctypes.wintypes.BOOL
USER32.EnableWindow.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.BOOL]
USER32.EnableWindow.restype = ctypes.wintypes.BOOL
USER32.SetWindowTextA.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.LPCSTR]
USER32.SetWindowTextA.restype = ctypes.wintypes.BOOL
USER32.GetWindowTextA.argtypes = [
    ctypes.wintypes.HWND,
    ctypes.wintypes.LPSTR,
    ctypes.c_int,
]
USER32.GetWindowTextA.restype = ctypes.c_int
USER32.SendMessageA.argtypes = [
    ctypes.wintypes.HWND,
    ctypes.wintypes.UINT,
    WPARAM,
    LPARAM,
]
USER32.SendMessageA.restype = LRESULT
USER32.TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
USER32.TranslateMessage.restype = ctypes.wintypes.BOOL
USER32.DispatchMessageA.argtypes = [ctypes.POINTER(MSG)]
USER32.DispatchMessageA.restype = LRESULT
USER32.PeekMessageA.argtypes = [
    ctypes.POINTER(MSG),
    ctypes.wintypes.HWND,
    ctypes.wintypes.UINT,
    ctypes.wintypes.UINT,
    ctypes.wintypes.UINT,
]
USER32.PeekMessageA.restype = ctypes.wintypes.BOOL
USER32.SetWindowPos.argtypes = [
    ctypes.wintypes.HWND,
    ctypes.wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_uint,
]
USER32.SetWindowPos.restype = ctypes.wintypes.BOOL
KERNEL32.GetModuleHandleA.argtypes = [ctypes.wintypes.LPCSTR]
KERNEL32.GetModuleHandleA.restype = ctypes.wintypes.HINSTANCE
KERNEL32.GetLastError.argtypes = []
KERNEL32.GetLastError.restype = ctypes.wintypes.DWORD
GDI32.GetStockObject.argtypes = [ctypes.c_int]
GDI32.GetStockObject.restype = ctypes.wintypes.HGDIOBJ
GDI32.CreateSolidBrush.argtypes = [ctypes.wintypes.DWORD]
GDI32.CreateSolidBrush.restype = ctypes.wintypes.HBRUSH
GDI32.SetTextColor.argtypes = [ctypes.wintypes.HDC, ctypes.wintypes.DWORD]
GDI32.SetTextColor.restype = ctypes.wintypes.DWORD
GDI32.SetBkColor.argtypes = [ctypes.wintypes.HDC, ctypes.wintypes.DWORD]
GDI32.SetBkColor.restype = ctypes.wintypes.DWORD
GDI32.CreateFontA.argtypes = [
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.wintypes.DWORD,
    ctypes.wintypes.DWORD,
    ctypes.wintypes.DWORD,
    ctypes.wintypes.DWORD,
    ctypes.wintypes.DWORD,
    ctypes.wintypes.DWORD,
    ctypes.wintypes.DWORD,
    ctypes.wintypes.DWORD,
    ctypes.wintypes.LPCSTR,
]
GDI32.CreateFontA.restype = HFONT
UXTHEME.SetWindowTheme.argtypes = [
    ctypes.wintypes.HWND,
    ctypes.wintypes.LPCWSTR,
    ctypes.wintypes.LPCWSTR,
]
UXTHEME.SetWindowTheme.restype = HRESULT
DWMAPI.DwmSetWindowAttribute.argtypes = [
    ctypes.wintypes.HWND,
    ctypes.wintypes.DWORD,
    LPCVOID,
    ctypes.wintypes.DWORD,
]
DWMAPI.DwmSetWindowAttribute.restype = HRESULT


def colorref(red, green, blue):
    return int(red) | (int(green) << 8) | (int(blue) << 16)


def loword(value):
    return int(value) & 0xffff


def hiword_signed(value):
    raw = (int(value) >> 16) & 0xffff
    return raw - 0x10000 if raw & 0x8000 else raw


def hiword(value):
    return (int(value) >> 16) & 0xffff


def get_client_size(hwnd):
    rect = RECT()
    USER32.GetClientRect(hwnd, ctypes.byref(rect))
    return max(1, rect.right - rect.left), max(1, rect.bottom - rect.top)


def get_window_rect(hwnd):
    rect = RECT()
    USER32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect


def topmost_handle():
    mask = (1 << (POINTER_SIZE * 8)) - 1
    return ctypes.wintypes.HWND((-1) & mask)


def set_title(hwnd, title):
    USER32.SetWindowTextA(
        hwnd,
        ctypes.c_char_p(str(title)),
    )


def native_text(value):
    if value is None:
        return ""
    if isinstance(value, unicode):
        return value.encode("mbcs", "replace")
    return str(value)


def weapon_trace(message):
    if os.environ.get("ELYSIAN_JESSICA_DEBUG_WEAPONS") != "1":
        return
    try:
        runtime_root = os.path.join(SCRIPT_ROOT, "runtime")
        if not os.path.isdir(runtime_root):
            os.makedirs(runtime_root)
        with open(os.path.join(runtime_root, "weapon-native-trace.log"), "a") as handle:
            handle.write("%s %s\n" % (time.time(), native_text(message)))
            handle.flush()
    except Exception:
        pass


class LiveTrinityViewer(object):
    def __init__(
        self,
        type_id,
        dna,
        radius,
        width,
        height,
        render_mode,
        catalog_path=None,
        command_path=None,
    ):
        self.type_id = int(type_id)
        self.dna = dna
        self.radius = float(radius)
        self.catalog_path = catalog_path
        self.command_path = command_path
        self.command_offset = 0
        self.last_command_poll_at = 0.0
        self.catalog_payload = {}
        self.catalog = self.load_catalog(catalog_path)
        self.asset_search_blobs = []
        self.asset_search_names = []
        self.asset_search_words = []
        self.search_first_character_index = {}
        self.search_candidate_index = {}
        self.filter_indexes = {}
        self.build_search_indexes()
        self.search_text = ""
        self.search_pending = False
        self.search_changed_at = 0.0
        self.filter_flags = dict((name, False) for _control_id, name in FILTER_CONTROLS)
        self.filtered_catalog_indices = list(range(len(self.catalog)))
        self.displayed_catalog_indices = []
        self.catalog_index = self.find_catalog_index(self.type_id)
        self.current_asset = self.resolve_current_asset()
        self.weapon_catalog = self.load_weapon_catalog()
        self.armed_turret_sets = []
        self.armed_weapon = None
        self.selected_weapon_index = -1
        self.animation_options = []
        self.selected_animation_index = -1
        self.dummy_target = None
        self.dummy_target_position = (0.0, 0.0, 0.0)
        self.firing_dummy = False
        self.next_dummy_fire_at = 0.0
        self.weapon_cycle_seconds = 2.2
        self.active_missiles = []
        self.active_weapon_impacts = []
        self.missile_templates = {}
        self.impact_templates = {}
        self.last_search_poll_at = 0.0
        self.activation_step = 0
        if self.current_asset:
            self.dna = native_text(self.current_asset.get("dna") or self.dna)
            self.radius = float(self.current_asset.get("radius") or self.radius)
        self.width = int(width)
        self.height = int(height)
        self.running = True
        self.paused = False
        self.dragging = False
        self.drag_button = None
        self.drag_distance = 0
        self.last_mouse = (0, 0)
        self.yaw = 0.0
        self.pitch = 0.22
        self.zoom = 1.0
        self.camera_pan = [0.0, 0.0, 0.0]
        self.light_scale = 1.1
        self.post_enabled = True
        self.after_effects_enabled = True
        self.boosters_enabled = True
        self.original_boosters = None
        self.activation_possible = False
        self.mode_index = self.resolve_mode_index(render_mode)
        self.scene_index = 0
        self.nebula_index = 0
        self.nebula_cube_maps = self.load_nebula_cube_maps()
        self.scene_paths = self.build_scene_paths()
        self.hwnd = None
        self.panel_hwnd = None
        self.wndclass = None
        self.panel_wndclass = None
        self.wndproc = None
        self.blue = None
        self.tri = None
        self.audio2 = None
        self.geo2 = None
        self.trinity_package = None
        self.device = None
        self.render_jobs = None
        self.scene = None
        self.space_object = None
        self.sof_factory = None
        self.model_radius = self.radius
        self.model_center = (0.0, 0.0, 0.0)
        self.render_driver = None
        self.execute_node = None
        self.explosion_models = []
        self.explosion_until = 0.0
        self.explosion_ship_hide_at = 0.0
        self.explosion_restore_display = None
        self.frame_count = 0
        self.last_title_at = time.time()
        self.fps_window_at = time.time()
        self.fps_window_frames = 0
        self.fps = 0.0
        self.panel_visible = True
        self.controls = {}
        self.control_buffers = []
        self.panel_brush = GDI32.CreateSolidBrush(colorref(15, 22, 31))
        self.panel_font = GDI32.CreateFontA(
            -16,
            0,
            0,
            0,
            400,
            0,
            0,
            0,
            1,
            0,
            0,
            5,
            0,
            ctypes.c_char_p("Segoe UI"),
        )

    def load_catalog(self, catalog_path):
        if not catalog_path:
            return []
        try:
            with open(catalog_path, "r") as handle:
                payload = json.load(handle)
            self.catalog_payload = payload if isinstance(payload, dict) else {}
            assets = (
                payload.get("assets", [])
                if isinstance(payload, dict)
                else (payload if isinstance(payload, list) else [])
            )
            return [entry for entry in assets if entry.get("dna")]
        except Exception:
            print(traceback.format_exc(), file=sys.stderr)
            return []

    def find_catalog_index(self, type_id):
        for index, entry in enumerate(self.catalog):
            if int(entry.get("typeID") or 0) == int(type_id):
                return index
        return 0 if self.catalog else -1

    def resolve_current_asset(self):
        if 0 <= self.catalog_index < len(self.catalog):
            return self.catalog[self.catalog_index]
        return None

    def build_asset_search_blob(self, entry):
        sof = entry.get("sof") or {}
        fields = [
            entry.get("typeID"),
            entry.get("name"),
            entry.get("groupID"),
            entry.get("groupName"),
            entry.get("categoryID"),
            entry.get("assetKind"),
            entry.get("graphicID"),
            entry.get("graphicFile"),
            entry.get("dna"),
            sof.get("hull"),
            sof.get("faction"),
            sof.get("race"),
            sof.get("materialSetID"),
        ]
        layout = sof.get("layout")
        if isinstance(layout, list):
            fields.extend(layout)
        elif layout:
            fields.append(layout)
        return " ".join([
            native_text(value).lower()
            for value in fields
            if value is not None
        ])

    def build_search_indexes(self):
        self.asset_search_blobs = []
        self.asset_search_names = []
        self.asset_search_words = []
        self.search_first_character_index = {}
        self.search_candidate_index = {}
        self.filter_indexes = dict((name, set()) for _control_id, name in FILTER_CONTROLS)
        for index, entry in enumerate(self.catalog):
            blob = self.build_asset_search_blob(entry)
            name = native_text(entry.get("name") or "").lower()
            words = tuple(set(re.findall(r"[a-z0-9]+", blob)))
            self.asset_search_blobs.append(blob)
            self.asset_search_names.append(name)
            self.asset_search_words.append(words)
            for initial in set(word[0] for word in words if word):
                self.search_first_character_index.setdefault(initial, set()).add(index)
            candidate_keys = set()
            for word in words:
                candidate_keys.add(word)
                for prefix_length in range(2, min(9, len(word) + 1)):
                    candidate_keys.add(word[:prefix_length])
                if len(word) >= 4:
                    for position in range(len(word)):
                        candidate_keys.add(word[:position] + word[position + 1:])
            for key in candidate_keys:
                self.search_candidate_index.setdefault(key, set()).add(index)
            kind = native_text(entry.get("assetKind")).lower()
            if kind == "ship":
                self.filter_indexes["ships"].add(index)
            elif kind == "gate":
                self.filter_indexes["gates"].add(index)
            elif kind == "station":
                self.filter_indexes["stations"].add(index)
            elif kind == "structure":
                self.filter_indexes["structures"].add(index)
            capabilities = entry.get("capabilities") or {}
            if capabilities.get("animations"):
                self.filter_indexes["animations"].add(index)
            if capabilities.get("explosions") or entry.get("explosions"):
                self.filter_indexes["explosions"].add(index)
            if entry.get("published") is True:
                self.filter_indexes["published"].add(index)

    def load_weapon_catalog(self):
        payload = self.catalog_payload.get("weaponPreview", {})
        weapons = payload.get("weapons") if isinstance(payload, dict) else []
        return [
            weapon
            for weapon in weapons or []
            if weapon.get("resourcePath")
        ]

    def parse_search_query(self, text):
        filters = {}
        tokens = []
        for raw_token in re.split(r"\s+", native_text(text).lower().strip()):
            if not raw_token:
                continue
            if raw_token.startswith("@"):
                filters["kind"] = raw_token[1:]
                continue
            if ":" in raw_token:
                key, value = raw_token.split(":", 1)
                if key in ("kind", "race", "group", "type", "id"):
                    filters[key] = value
                    continue
            tokens.append(raw_token)
        return filters, tokens

    def bounded_edit_distance(self, left, right, limit):
        if abs(len(left) - len(right)) > limit:
            return limit + 1
        previous = list(range(len(right) + 1))
        for left_index, left_character in enumerate(left, 1):
            current = [left_index]
            row_minimum = current[0]
            for right_index, right_character in enumerate(right, 1):
                current.append(min(
                    current[right_index - 1] + 1,
                    previous[right_index] + 1,
                    previous[right_index - 1] + (left_character != right_character),
                ))
                row_minimum = min(row_minimum, current[-1])
            if row_minimum > limit:
                return limit + 1
            previous = current
        return previous[-1]

    def fuzzy_word_matches(self, catalog_index, token):
        if not token:
            return True
        blob = self.asset_search_blobs[catalog_index]
        if token in blob:
            return True
        limit = 1 if len(token) < 7 else 2
        for word in self.asset_search_words[catalog_index]:
            if word.startswith(token):
                return True
            if self.bounded_edit_distance(word, token, limit) <= limit:
                return True
        return False

    def asset_matches_filter(self, catalog_index, filters, tokens):
        if not filters and not tokens:
            return True
        if catalog_index < 0 or catalog_index >= len(self.asset_search_blobs):
            return False
        entry = self.catalog[catalog_index]
        sof = entry.get("sof") or {}
        kind_filter = filters.get("kind")
        if kind_filter and kind_filter not in native_text(entry.get("assetKind")).lower():
            return False
        race_filter = filters.get("race")
        if race_filter and race_filter not in native_text(sof.get("race")).lower():
            return False
        group_filter = filters.get("group")
        if group_filter and group_filter not in native_text(entry.get("groupName")).lower():
            return False
        type_filter = filters.get("type") or filters.get("id")
        if type_filter and type_filter not in native_text(entry.get("typeID")).lower():
            return False
        blob = self.asset_search_blobs[catalog_index]
        return all(self.fuzzy_word_matches(catalog_index, token) for token in tokens)

    def search_rank(self, catalog_index, tokens):
        if not tokens:
            return (0, self.asset_search_names[catalog_index], catalog_index)
        name = self.asset_search_names[catalog_index]
        blob = self.asset_search_blobs[catalog_index]
        score = 0
        for token in tokens:
            if name == token:
                score += 0
            elif name.startswith(token):
                score += 4
            elif (" " + name).find(" " + token) >= 0:
                score += 8
            elif token in name:
                score += 12
            elif token in blob:
                score += 20
            else:
                distance = min([
                    self.bounded_edit_distance(
                        word,
                        token,
                        1 if len(token) < 7 else 2,
                    )
                    for word in self.asset_search_words[catalog_index]
                ] or [3])
                score += 30 + min(3, distance)
        return (score, len(name), name, catalog_index)

    def selected_kind_filter(self):
        return [
            name
            for name in ("ships", "gates", "stations", "structures")
            if self.filter_flags.get(name)
        ]

    def apply_catalog_filter(self):
        filters, tokens = self.parse_search_query(self.search_text)
        candidates = set(range(len(self.catalog)))
        selected_kinds = self.selected_kind_filter()
        if selected_kinds:
            kind_candidates = set()
            for name in selected_kinds:
                kind_candidates.update(self.filter_indexes.get(name, set()))
            candidates.intersection_update(kind_candidates)
        for name in ("animations", "explosions", "published"):
            if self.filter_flags.get(name):
                candidates.intersection_update(self.filter_indexes.get(name, set()))
        for token in tokens:
            if token:
                token_candidates = set(self.search_candidate_index.get(token, set()))
                if len(token) >= 4:
                    for position in range(len(token)):
                        token_candidates.update(self.search_candidate_index.get(
                            token[:position] + token[position + 1:],
                            set(),
                        ))
                if not token_candidates:
                    token_candidates = self.search_first_character_index.get(token[0], set())
                candidates.intersection_update(token_candidates)
        matches = [
            index
            for index in candidates
            if self.asset_matches_filter(index, filters, tokens)
        ]
        matches.sort(key=lambda index: self.search_rank(index, tokens))
        self.filtered_catalog_indices = matches

    def resolve_mode_index(self, mode):
        normalized = str(mode or "white").lower()
        for index, (name, _) in enumerate(VISUAL_MODES):
            if name == normalized:
                return index
        return 0

    def build_scene_paths(self):
        nebulas = self.catalog_payload.get("nebulas", {})
        scene_rows = nebulas.get("scenes") or []
        paths = [row.get("scenePath") for row in scene_rows if row.get("scenePath")]
        paths.extend([
            "res:/dx9/scene/starfield/universe.black",
            "res:/dx9/scene/starfield/starfieldnebula.black",
            resolve_icon_scene_path(self.dna),
            "res:/dx9/scene/iconbackground/generic.black",
        ])
        unique = []
        for path in paths:
            if path not in unique:
                unique.append(path)
        return unique

    def load_nebula_cube_maps(self):
        nebulas = self.catalog_payload.get("nebulas", {})
        rows = nebulas.get("cubeMaps") or []
        result = []
        for row in rows:
            cube_path = row.get("cubePath")
            if not cube_path:
                continue
            result.append({
                "label": row.get("label") or cube_path,
                "cubePath": native_text(cube_path),
                "reflectionPath": native_text(
                    row.get("reflectionPath") or cube_path.replace(".dds", "_refl.dds")
                ),
                "blurPath": native_text(
                    row.get("blurPath") or cube_path.replace(".dds", "_blur.dds")
                ),
            })
        if not result:
            result = [{
                "label": "universe/a01_cube",
                "cubePath": "res:/dx9/scene/universe/a01_cube.dds",
                "reflectionPath": "res:/dx9/scene/universe/a01_cube_refl.dds",
                "blurPath": "res:/dx9/scene/universe/a01_cube_blur.dds",
            }]
        return result

    def create_window(self):
        hinstance = KERNEL32.GetModuleHandleA(None)
        self.wndproc = WNDPROC(window_proc)
        class_name = "ElysianTrinityLive-%s-%s" % (os.getpid(), self.type_id)
        wndclass = WNDCLASS()
        wndclass.style = CS_HREDRAW | CS_VREDRAW
        wndclass.lpfnWndProc = self.wndproc
        wndclass.cbClsExtra = 0
        wndclass.cbWndExtra = 0
        wndclass.hInstance = hinstance
        wndclass.hIcon = USER32.LoadImageA(
            ctypes.c_void_p(NULL),
            ctypes.c_char_p(IDI_APPLICATION),
            ctypes.c_uint(1),
            ctypes.c_int(24),
            ctypes.c_int(24),
            ctypes.c_uint(0),
        )
        wndclass.hCursor = USER32.LoadImageA(
            ctypes.c_void_p(NULL),
            ctypes.c_char_p(IDC_ARROW),
            ctypes.c_uint(2),
            ctypes.c_int(24),
            ctypes.c_int(24),
            ctypes.c_uint(0),
        )
        wndclass.hbrBackground = GDI32.GetStockObject(
            ctypes.c_int(BLACK_BRUSH),
        )
        wndclass.lpszMenuName = None
        wndclass.lpszClassName = class_name
        if not USER32.RegisterClassA(ctypes.byref(wndclass)):
            error_code = KERNEL32.GetLastError()
            raise ctypes.WinError(error_code)
        self.wndclass = wndclass

        hwnd = USER32.CreateWindowExA(
            0,
            wndclass.lpszClassName,
            "Elysian Jessica Live",
            WS_OVERLAPPEDWINDOW,
            CW_USEDEFAULT,
            CW_USEDEFAULT,
            self.width,
            self.height,
            NULL,
            NULL,
            hinstance,
            NULL,
        )
        if not hwnd:
            error_code = KERNEL32.GetLastError()
            raise ctypes.WinError(error_code)
        self.hwnd = hwnd
        USER32.ShowWindow(hwnd, SW_SHOWNORMAL)
        USER32.UpdateWindow(hwnd)

    def create_panel_window(self):
        hinstance = KERNEL32.GetModuleHandleA(None)
        class_name = "ElysianTrinityPanel-%s-%s" % (os.getpid(), self.type_id)
        wndclass = WNDCLASS()
        wndclass.style = CS_HREDRAW | CS_VREDRAW
        wndclass.lpfnWndProc = self.wndproc
        wndclass.cbClsExtra = 0
        wndclass.cbWndExtra = 0
        wndclass.hInstance = hinstance
        wndclass.hIcon = USER32.LoadImageA(
            ctypes.c_void_p(NULL),
            ctypes.c_char_p(IDI_APPLICATION),
            ctypes.c_uint(1),
            ctypes.c_int(24),
            ctypes.c_int(24),
            ctypes.c_uint(0),
        )
        wndclass.hCursor = USER32.LoadImageA(
            ctypes.c_void_p(NULL),
            ctypes.c_char_p(IDC_ARROW),
            ctypes.c_uint(2),
            ctypes.c_int(24),
            ctypes.c_int(24),
            ctypes.c_uint(0),
        )
        wndclass.hbrBackground = self.panel_brush
        wndclass.lpszMenuName = None
        wndclass.lpszClassName = class_name
        if not USER32.RegisterClassA(ctypes.byref(wndclass)):
            error_code = KERNEL32.GetLastError()
            raise ctypes.WinError(error_code)
        self.panel_wndclass = wndclass

        main_rect = get_window_rect(self.hwnd)
        panel_x = max(20, main_rect.left + 28)
        panel_y = max(20, main_rect.top + 58)
        panel_hwnd = USER32.CreateWindowExA(
            WS_EX_TOOLWINDOW | WS_EX_TOPMOST,
            wndclass.lpszClassName,
            "Jessica Quick Controls",
            WS_OVERLAPPEDWINDOW,
            panel_x,
            panel_y,
            CONTROL_PANEL_WIDTH + 42,
            720,
            NULL,
            NULL,
            hinstance,
            NULL,
        )
        if not panel_hwnd:
            error_code = KERNEL32.GetLastError()
            raise ctypes.WinError(error_code)
        self.panel_hwnd = panel_hwnd
        dark_mode = ctypes.c_int(1)
        for attribute in (20, 19):
            try:
                if DWMAPI.DwmSetWindowAttribute(
                    panel_hwnd,
                    attribute,
                    ctypes.byref(dark_mode),
                    ctypes.sizeof(dark_mode),
                ) == 0:
                    break
            except Exception:
                pass
        try:
            UXTHEME.SetWindowTheme(panel_hwnd, u"DarkMode_Explorer", None)
        except Exception:
            pass
        self.create_controls()
        USER32.ShowWindow(panel_hwnd, SW_SHOWNORMAL)
        USER32.SetWindowPos(
            panel_hwnd,
            topmost_handle(),
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW,
        )
        USER32.UpdateWindow(panel_hwnd)

    def create_child(self, class_name, text, style, control_id, x, y, width, height):
        if not self.panel_hwnd:
            raise RuntimeError("control panel window has not been created")
        hwnd = USER32.CreateWindowExA(
            0,
            ctypes.c_char_p(class_name),
            ctypes.c_char_p(native_text(text)),
            WS_CHILD | WS_VISIBLE | style,
            x,
            y,
            width,
            height,
            self.panel_hwnd,
            ctypes.wintypes.HMENU(control_id),
            KERNEL32.GetModuleHandleA(None),
            None,
        )
        if not hwnd:
            raise ctypes.WinError(KERNEL32.GetLastError())
        try:
            UXTHEME.SetWindowTheme(hwnd, u"DarkMode_Explorer", None)
        except Exception:
            pass
        if self.panel_font:
            USER32.SendMessageA(hwnd, WM_SETFONT, self.panel_font, 1)
        self.controls[control_id] = hwnd
        return hwnd

    def create_controls(self):
        self.create_child("STATIC", "Jessica Asset Library", 0, 1200, 0, 0, 100, 20)
        search_style = WS_BORDER | WS_TABSTOP | ES_AUTOHSCROLL
        self.create_child("EDIT", "", search_style, IDC_SEARCH, 0, 0, 100, 26)
        self.create_child("STATIC", "", 0, IDC_SEARCH_STATUS, 0, 0, 100, 18)
        filter_labels = {
            IDC_FILTER_SHIPS: "Ships",
            IDC_FILTER_GATES: "Gates",
            IDC_FILTER_STATIONS: "Stations",
            IDC_FILTER_STRUCTURES: "Structures",
            IDC_FILTER_ANIMATIONS: "Has animations",
            IDC_FILTER_EXPLOSIONS: "Has explosions",
            IDC_FILTER_PUBLISHED: "Published",
        }
        for control_id, _name in FILTER_CONTROLS:
            self.create_child(
                "BUTTON",
                filter_labels[control_id],
                BS_AUTOCHECKBOX | WS_TABSTOP,
                control_id,
                0,
                0,
                100,
                22,
            )
        self.create_child("STATIC", "Animation", 0, IDC_ANIMATION_LABEL, 0, 0, 100, 18)
        self.create_child(
            "COMBOBOX",
            "",
            CBS_DROPDOWNLIST | WS_VSCROLL | WS_TABSTOP,
            IDC_ANIMATION_LIST,
            0,
            0,
            100,
            240,
        )
        self.create_child(
            "BUTTON",
            "Play",
            BS_PUSHBUTTON | WS_TABSTOP,
            IDC_PLAY_ANIMATION,
            0,
            0,
            64,
            24,
        )
        self.create_child("STATIC", "Weapon", 0, IDC_WEAPON_LABEL, 0, 0, 100, 18)
        self.create_child(
            "COMBOBOX",
            "",
            CBS_DROPDOWNLIST | WS_VSCROLL | WS_TABSTOP,
            IDC_WEAPON_LIST,
            0,
            0,
            100,
            280,
        )
        list_style = WS_BORDER | WS_VSCROLL | LBS_NOTIFY | LBS_NOINTEGRALHEIGHT | WS_TABSTOP
        self.create_child("LISTBOX", "", list_style, IDC_ASSET_LIST, 0, 0, 100, 100)
        self.create_child("BUTTON", "Load", BS_PUSHBUTTON | WS_TABSTOP, IDC_LOAD, 0, 0, 64, 24)
        self.create_child("BUTTON", "Prev", BS_PUSHBUTTON | WS_TABSTOP, IDC_PREV, 0, 0, 64, 24)
        self.create_child("BUTTON", "Next", BS_PUSHBUTTON | WS_TABSTOP, IDC_NEXT, 0, 0, 64, 24)
        self.create_child("BUTTON", "Mode", BS_PUSHBUTTON | WS_TABSTOP, IDC_MODE, 0, 0, 64, 24)
        self.create_child("BUTTON", "Nebula", BS_PUSHBUTTON | WS_TABSTOP, IDC_NEBULA, 0, 0, 64, 24)
        self.create_child("BUTTON", "Light +", BS_PUSHBUTTON | WS_TABSTOP, IDC_LIGHT_UP, 0, 0, 64, 24)
        self.create_child("BUTTON", "Light -", BS_PUSHBUTTON | WS_TABSTOP, IDC_LIGHT_DOWN, 0, 0, 64, 24)
        self.create_child("BUTTON", "Boosters", BS_PUSHBUTTON | WS_TABSTOP, IDC_BOOSTERS, 0, 0, 64, 24)
        self.create_child("BUTTON", "Post", BS_PUSHBUTTON | WS_TABSTOP, IDC_POST, 0, 0, 64, 24)
        self.create_child("BUTTON", "After FX", BS_PUSHBUTTON | WS_TABSTOP, IDC_AFTER, 0, 0, 64, 24)
        self.create_child("BUTTON", "Explode", BS_PUSHBUTTON | WS_TABSTOP, IDC_EXPLODE, 0, 0, 64, 24)
        self.create_child("BUTTON", "Activate", BS_PUSHBUTTON | WS_TABSTOP, IDC_ACTIVATE, 0, 0, 64, 24)
        self.create_child("BUTTON", "Arm Max", BS_PUSHBUTTON | WS_TABSTOP, IDC_ARM_MAX, 0, 0, 64, 24)
        self.create_child("BUTTON", "Fire Dummy", BS_PUSHBUTTON | WS_TABSTOP, IDC_FIRE_DUMMY, 0, 0, 64, 24)
        self.create_child("BUTTON", "Clear Guns", BS_PUSHBUTTON | WS_TABSTOP, IDC_CLEAR_WEAPONS, 0, 0, 64, 24)
        self.create_child("BUTTON", "Reset Camera", BS_PUSHBUTTON | WS_TABSTOP, IDC_RESET_CAMERA, 0, 0, 64, 24)
        self.populate_weapon_list()
        self.populate_catalog_list()
        self.position_controls()
        self.sync_control_text()

    def populate_catalog_list(self):
        listbox = self.controls.get(IDC_ASSET_LIST)
        if not listbox:
            return
        USER32.SendMessageA(listbox, WM_SETREDRAW, 0, 0)
        try:
            USER32.SendMessageA(listbox, LB_RESETCONTENT, 0, 0)
            self.control_buffers = []
            if not self.catalog:
                buffer = ctypes.create_string_buffer("No catalogue loaded")
                self.control_buffers.append(buffer)
                USER32.SendMessageA(
                    listbox,
                    LB_ADDSTRING,
                    0,
                    ctypes.cast(buffer, ctypes.c_void_p).value,
                )
                return
            self.displayed_catalog_indices = self.filtered_catalog_indices[
                :MAX_VISIBLE_SEARCH_RESULTS
            ]
            if not self.displayed_catalog_indices:
                buffer = ctypes.create_string_buffer("No matches")
                self.control_buffers.append(buffer)
                USER32.SendMessageA(
                    listbox,
                    LB_ADDSTRING,
                    0,
                    ctypes.cast(buffer, ctypes.c_void_p).value,
                )
                return
            USER32.SendMessageA(
                listbox,
                LB_INITSTORAGE,
                len(self.displayed_catalog_indices),
                len(self.displayed_catalog_indices) * 96,
            )
            for catalog_index in self.displayed_catalog_indices:
                entry = self.catalog[catalog_index]
                label = "%s  |  %s  |  %s" % (
                    entry.get("name") or entry.get("typeID"),
                    entry.get("groupName") or "",
                    entry.get("sof", {}).get("race") or "",
                )
                buffer = ctypes.create_string_buffer(native_text(label))
                self.control_buffers.append(buffer)
                USER32.SendMessageA(
                    listbox,
                    LB_ADDSTRING,
                    0,
                    ctypes.cast(buffer, ctypes.c_void_p).value,
                )
            if self.catalog_index >= 0:
                try:
                    selected_row = self.displayed_catalog_indices.index(
                        self.catalog_index
                    )
                except ValueError:
                    selected_row = 0
                USER32.SendMessageA(listbox, LB_SETCURSEL, selected_row, 0)
        finally:
            USER32.SendMessageA(listbox, WM_SETREDRAW, 1, 0)
            USER32.InvalidateRect(listbox, None, True)
        visible_count = len(self.displayed_catalog_indices)
        total_count = len(self.filtered_catalog_indices)
        suffix = (
            " - showing first %s" % visible_count
            if total_count > visible_count
            else ""
        )
        self.set_control_text(
            IDC_SEARCH_STATUS,
            "%s match%s%s" % (
                total_count,
                "" if total_count == 1 else "es",
                suffix,
            ),
        )

    def position_controls(self):
        if not self.controls or not self.panel_hwnd:
            return
        width, height = get_client_size(self.panel_hwnd)
        x = 12
        y = 12
        gap = 8
        content_width = max(260, width - 24)
        panel_height = max(260, height - 24)
        USER32.MoveWindow(self.controls[1200], x, y, 150, 20, True)
        USER32.MoveWindow(
            self.controls[IDC_SEARCH_STATUS],
            x + 158,
            y,
            max(100, content_width - 158),
            20,
            True,
        )
        USER32.MoveWindow(
            self.controls[IDC_SEARCH],
            x,
            y + 26,
            content_width,
            26,
            True,
        )
        checkbox_gap = 4
        first_row = (
            IDC_FILTER_SHIPS,
            IDC_FILTER_GATES,
            IDC_FILTER_STATIONS,
            IDC_FILTER_STRUCTURES,
        )
        second_row = (
            IDC_FILTER_ANIMATIONS,
            IDC_FILTER_EXPLOSIONS,
            IDC_FILTER_PUBLISHED,
        )
        first_width = max(74, int((content_width - checkbox_gap * 3) / 4))
        second_width = max(100, int((content_width - checkbox_gap * 2) / 3))
        for column, control_id in enumerate(first_row):
            USER32.MoveWindow(
                self.controls[control_id],
                x + column * (first_width + checkbox_gap),
                y + 58,
                first_width,
                22,
                True,
            )
        for column, control_id in enumerate(second_row):
            USER32.MoveWindow(
                self.controls[control_id],
                x + column * (second_width + checkbox_gap),
                y + 82,
                second_width,
                22,
                True,
            )
        action_button_width = 76
        USER32.MoveWindow(self.controls[IDC_ANIMATION_LABEL], x, y + 110, 90, 18, True)
        USER32.MoveWindow(
            self.controls[IDC_ANIMATION_LIST],
            x,
            y + 130,
            max(120, content_width - action_button_width - gap),
            240,
            True,
        )
        USER32.MoveWindow(
            self.controls[IDC_PLAY_ANIMATION],
            x + content_width - action_button_width,
            y + 130,
            action_button_width,
            26,
            True,
        )
        USER32.MoveWindow(self.controls[IDC_WEAPON_LABEL], x, y + 162, 90, 18, True)
        USER32.MoveWindow(
            self.controls[IDC_WEAPON_LIST],
            x,
            y + 182,
            content_width,
            280,
            True,
        )
        button_y = y + max(146, panel_height - 242)
        USER32.MoveWindow(
            self.controls[IDC_ASSET_LIST],
            x,
            y + 214,
            content_width,
            max(80, button_y - (y + 222)),
            True,
        )
        button_w = max(72, int((content_width - (gap * 2)) / 3))
        button_h = 26
        rows = [
            (IDC_LOAD, IDC_PREV, IDC_NEXT),
            (IDC_MODE, IDC_NEBULA, IDC_RESET_CAMERA),
            (IDC_LIGHT_DOWN, IDC_LIGHT_UP, IDC_BOOSTERS),
            (IDC_POST, IDC_AFTER, IDC_EXPLODE),
            (IDC_ACTIVATE, IDC_ARM_MAX, IDC_FIRE_DUMMY),
            (IDC_CLEAR_WEAPONS,),
        ]
        for row_index, row in enumerate(rows):
            for col_index, control_id in enumerate(row):
                USER32.MoveWindow(
                    self.controls[control_id],
                    x + col_index * (button_w + gap),
                    button_y + row_index * (button_h + gap),
                    button_w,
                    button_h,
                    True,
                )
        self.apply_panel_visibility()

    def apply_panel_visibility(self):
        if not self.panel_hwnd:
            return
        if self.panel_visible:
            USER32.ShowWindow(self.panel_hwnd, SW_SHOWNORMAL)
            USER32.SetWindowPos(
                self.panel_hwnd,
                topmost_handle(),
                0,
                0,
                0,
                0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW,
            )
        else:
            USER32.ShowWindow(self.panel_hwnd, SW_HIDE)

    def toggle_panel(self):
        self.panel_visible = not self.panel_visible
        self.apply_panel_visibility()
        self.update_title(force=True)

    def set_control_text(self, control_id, text):
        hwnd = self.controls.get(control_id)
        if hwnd:
            USER32.SetWindowTextA(hwnd, ctypes.c_char_p(native_text(text)))

    def populate_combo(self, control_id, labels, selected_index=0):
        hwnd = self.controls.get(control_id)
        if not hwnd:
            return
        USER32.SendMessageA(hwnd, CB_RESETCONTENT, 0, 0)
        for label in labels:
            buffer = ctypes.create_string_buffer(native_text(label))
            USER32.SendMessageA(
                hwnd,
                CB_ADDSTRING,
                0,
                ctypes.cast(buffer, ctypes.c_void_p).value,
            )
        if labels:
            USER32.SendMessageA(
                hwnd,
                CB_SETCURSEL,
                max(0, min(len(labels) - 1, int(selected_index))),
                0,
            )

    def get_combo_selection(self, control_id):
        hwnd = self.controls.get(control_id)
        if not hwnd:
            return -1
        return int(USER32.SendMessageA(hwnd, CB_GETCURSEL, 0, 0))

    def weapon_display_label(self, weapon):
        kind = native_text(
            weapon.get("variant") or
            ("Missile" if weapon.get("kind") == "launcher" else weapon.get("family")) or
            "Turret"
        )
        size = native_text(weapon.get("size") or "unknown").title()
        return "%s / %s  |  %s" % (
            kind,
            size,
            weapon.get("name") or weapon.get("typeID"),
        )

    def populate_weapon_list(self):
        size_hint = self.current_ship_size_hint()
        families = self.weapon_family_preferences()

        def score(index):
            weapon = self.weapon_catalog[index]
            family = weapon.get("family")
            return (
                0 if weapon.get("size") == size_hint else 1,
                families.index(family) if family in families else 50,
                0 if weapon.get("kind") == "turret" else 1,
                native_text(weapon.get("name")).lower(),
            )

        self.weapon_display_indices = sorted(range(len(self.weapon_catalog)), key=score)
        default_weapon = self.select_preview_weapon(ignore_combo=True)
        default_display_index = 0
        if default_weapon is not None:
            try:
                default_catalog_index = self.weapon_catalog.index(default_weapon)
                default_display_index = self.weapon_display_indices.index(default_catalog_index)
            except ValueError:
                default_display_index = 0
        self.populate_combo(
            IDC_WEAPON_LIST,
            [
                self.weapon_display_label(self.weapon_catalog[index])
                for index in self.weapon_display_indices
            ],
            default_display_index,
        )
        self.selected_weapon_index = default_display_index

    def select_weapon_by_text(self, query):
        normalized = native_text(query).lower().strip()
        if not normalized:
            return False
        ranked = []
        for display_index, catalog_index in enumerate(self.weapon_display_indices):
            weapon = self.weapon_catalog[catalog_index]
            label = self.weapon_display_label(weapon).lower()
            name = native_text(weapon.get("name")).lower()
            variant = native_text(weapon.get("variant")).lower()
            if normalized == name or normalized == variant:
                score = 0
            elif name.startswith(normalized) or variant.startswith(normalized):
                score = 1
            elif normalized in label:
                score = 2
            else:
                continue
            ranked.append((score, display_index))
        if not ranked:
            return False
        ranked.sort()
        self.selected_weapon_index = ranked[0][1]
        USER32.SendMessageA(
            self.controls.get(IDC_WEAPON_LIST),
            CB_SETCURSEL,
            self.selected_weapon_index,
            0,
        )
        self.update_title(force=True)
        return True

    def discover_animation_options(self):
        if self.space_object is None:
            return []
        options = []
        seen = set()

        def add_option(key, label, kind, target, name=None, value=None, controller=None):
            if key in seen or len(options) >= 320:
                return
            seen.add(key)
            options.append({
                "label": label,
                "kind": kind,
                "target": target,
                "name": name,
                "value": value,
                "controller": controller,
            })

        queue = [self.space_object]
        visited = set()
        while queue and len(visited) < 1800:
            obj = queue.pop(0)
            marker = id(obj)
            if marker in visited:
                continue
            visited.add(marker)
            updater = getattr(obj, "animationUpdater", None)
            if updater is not None and hasattr(updater, "GetAnimationNames"):
                try:
                    for animation_name in updater.GetAnimationNames():
                        name = native_text(animation_name)
                        add_option(
                            ("animation", name.lower()),
                            "Animation  |  %s" % name,
                            "animation",
                            obj,
                            name=name,
                            controller=updater,
                        )
                except Exception:
                    pass
            for controller in list(getattr(obj, "controllers", []) or []):
                for event_handler in list(getattr(controller, "eventHandlers", []) or []):
                    name = native_text(getattr(event_handler, "name", "") or "")
                    if name:
                        add_option(
                            ("event", name.lower()),
                            "Event  |  %s" % name,
                            "event",
                            self.space_object,
                            name=name,
                        )
                for variable in list(getattr(controller, "variables", []) or []):
                    enum_values = native_text(getattr(variable, "enumValues", "") or "")
                    variable_name = native_text(getattr(variable, "name", "") or "State")
                    if not enum_values:
                        continue
                    for index, enum_label in enumerate(enum_values.split(",")):
                        label = enum_label.strip() or str(index)
                        add_option(
                            ("state", variable_name.lower(), index),
                            "State  |  %s = %s" % (variable_name, label),
                            "state",
                            variable,
                            value=index,
                        )
            if hasattr(obj, "Find"):
                try:
                    for curve_set in obj.Find("trinity.TriCurveSet", 2):
                        name = native_text(getattr(curve_set, "name", "") or "")
                        if name:
                            add_option(
                                ("curve", name.lower()),
                                "Curve  |  %s" % name,
                                "curve",
                                curve_set,
                                name=name,
                            )
                except Exception:
                    pass
            for child in self.iter_known_children(obj):
                queue.append(child)
        return options

    def populate_animation_list(self):
        self.animation_options = self.discover_animation_options()
        labels = [entry["label"] for entry in self.animation_options]
        if not labels:
            labels = ["No authored animations"]
        self.populate_combo(IDC_ANIMATION_LIST, labels, 0)
        self.selected_animation_index = 0 if self.animation_options else -1
        self.refresh_action_buttons()

    def play_selected_animation(self):
        selected = self.get_combo_selection(IDC_ANIMATION_LIST)
        if not (0 <= selected < len(self.animation_options)):
            return
        option = self.animation_options[selected]
        self.selected_animation_index = selected
        kind = option.get("kind")
        target = option.get("target")
        name = option.get("name")
        played = False
        if kind == "animation":
            played = self.safe_call(target, "PlayAnimation", name)
            if not played:
                played = self.safe_call(option.get("controller"), "PlayAnimation", name)
        elif kind == "event":
            played = self.safe_call(target, "HandleControllerEvent", name)
        elif kind == "state":
            try:
                target.value = option.get("value")
                played = True
            except Exception:
                played = False
        elif kind == "curve":
            played = self.safe_call(target, "PlayFrom", 0.0)
            if not played:
                played = self.safe_call(target, "Play")
        if played:
            self.pump_resource_loads("animation %s" % option.get("label"), 0.4)
        print("[live] animation played=%s option=%s" % (
            played,
            option.get("label"),
        ), file=sys.stderr)
        self.update_title(force=True)

    def get_control_text(self, control_id, max_chars=512):
        hwnd = self.controls.get(control_id)
        if not hwnd:
            return ""
        buffer = ctypes.create_string_buffer(max_chars)
        USER32.GetWindowTextA(hwnd, buffer, max_chars)
        value = buffer.value
        try:
            return value.decode("mbcs", "replace")
        except Exception:
            return native_text(value)

    def read_filter_controls(self):
        changed = False
        for control_id, name in FILTER_CONTROLS:
            hwnd = self.controls.get(control_id)
            checked = bool(hwnd and USER32.SendMessageA(hwnd, BM_GETCHECK, 0, 0) == BST_CHECKED)
            if self.filter_flags.get(name) != checked:
                self.filter_flags[name] = checked
                changed = True
        return changed

    def schedule_search_update(self):
        self.search_pending = True
        self.search_changed_at = time.time()

    def handle_search_changed(self, force=False):
        next_text = self.get_control_text(IDC_SEARCH).strip()
        filters_changed = self.read_filter_controls()
        if not force and next_text == self.search_text and not filters_changed:
            return
        self.search_text = next_text
        self.search_pending = False
        self.apply_catalog_filter()
        self.populate_catalog_list()
        self.update_title(force=True)

    def poll_search_text(self):
        now = time.time()
        if not self.search_pending:
            return
        if now - self.search_changed_at < SEARCH_DEBOUNCE_SECONDS:
            return
        self.handle_search_changed(force=True)

    def set_control_enabled(self, control_id, enabled):
        hwnd = self.controls.get(control_id)
        if hwnd:
            USER32.EnableWindow(hwnd, bool(enabled))

    def refresh_action_buttons(self):
        self.set_control_enabled(
            IDC_EXPLODE,
            len(self.current_explosion_options()) > 0,
        )
        self.set_control_enabled(
            IDC_ACTIVATE,
            bool(self.activation_possible),
        )
        self.set_control_enabled(
            IDC_ARM_MAX,
            self.can_arm_weapons(),
        )
        self.set_control_enabled(
            IDC_FIRE_DUMMY,
            bool(self.armed_turret_sets),
        )
        self.set_control_enabled(
            IDC_CLEAR_WEAPONS,
            bool(self.armed_turret_sets or self.dummy_target),
        )
        self.set_control_enabled(
            IDC_PLAY_ANIMATION,
            bool(self.animation_options),
        )

    def sync_control_text(self):
        self.set_control_text(IDC_MODE, "Mode: %s" % VISUAL_MODES[self.mode_index][0])
        self.set_control_text(IDC_NEBULA, "Nebula %s/%s" % (
            (self.nebula_index % len(self.nebula_cube_maps)) + 1,
            len(self.nebula_cube_maps),
        ))
        self.set_control_text(IDC_BOOSTERS, "Boosters %s" % (
            "On" if self.boosters_enabled else "Off",
        ))
        self.set_control_text(IDC_POST, "Post %s" % (
            "On" if self.post_enabled else "Off",
        ))
        self.set_control_text(IDC_AFTER, "After %s" % (
            "On" if self.after_effects_enabled else "Off",
        ))
        self.set_control_text(IDC_FIRE_DUMMY, "%s Dummy" % (
            "Stop" if self.firing_dummy else "Fire",
        ))
        self.refresh_action_buttons()

    def initialize_trinity(self):
        import blue
        tri = blue.LoadExtension("_trinity_dx11")

        self.blue = blue
        self.tri = tri
        # FISFX explosion Black graphs contain Audio2 curves and emitters.
        # Blue discards the entire graph if those native classes are not
        # registered before deserialization.
        self.audio2 = blue.LoadExtension("_audio2")
        self.geo2 = blue.LoadExtension("_geo2")
        try:
            import trinity as trinity_package
            self.trinity_package = trinity_package
        except Exception:
            self.trinity_package = None
        initialize_client_resource_cache(blue)
        self.render_jobs = blue.classes.CreateInstance("trinity.Tr2RenderJobs")
        self.device = blue.classes.CreateInstance("trinity.TriDevice")
        self.device.tickInterval = 0
        self.device.disableAsyncLoad = False
        self.device.SetRenderJobs(self.render_jobs)
        width, height = get_client_size(self.hwnd)
        self.device.CreateWindowedDevice(self.hwnd, width, height)
        tri.SetShaderModel("SM_3_0_DEPTH")
        self.device.mipLevelSkipCount = 0
        self.device.minimumModelLOD = 0
        if hasattr(tri, "SetEveSpaceObjectResourceUnloadingEnabled"):
            tri.SetEveSpaceObjectResourceUnloadingEnabled(0)
        def set_setting(name, value):
            try:
                tri.settings.SetValue(name, value)
            except Exception:
                pass
        set_setting("newBloom", True)
        set_setting("dynamicExposureQualityRequirement", 2)
        set_setting("eveSpaceSceneDynamicLighting", True)
        set_setting("eveReflectionSetting", 4)
        set_setting("postprocessDofEnabled", False)
        set_setting("eveSpaceObjectTrailsEnabled", True)
        set_setting("eveSpaceObjectTrailsIntensity", 1.0)
        set_setting("eveSpaceSceneVisibilityThreshold", 3.0)
        set_setting("eveSpaceSceneLowDetailThreshold", 35.0)
        set_setting("eveSpaceSceneMediumDetailThreshold", 120.0)
        set_setting("eveSpaceSceneLODFactor", 1.0)
        try:
            tri.GetTextureLodManager().useLowResVtaFiles = False
        except Exception:
            pass
        tri.GetVariableStore().RegisterVariable(
            "EveSpaceSceneShadowMap",
            tri.TriTextureRes(),
        )

    def get_resource_queue_depth(self):
        pending = 0
        for name in ("pendingLoads", "pendingPrepares"):
            try:
                pending += int(getattr(self.blue.resMan, name, 0) or 0)
            except Exception:
                pass
        return pending

    def pump_resource_loads(self, reason, max_seconds=15.0):
        started = time.time()
        last_queue_depth = None
        while self.get_resource_queue_depth() > 0:
            queue_depth = self.get_resource_queue_depth()
            if queue_depth != last_queue_depth:
                print(
                    "[live] loading %s queue=%s" % (reason, queue_depth),
                    file=sys.stderr,
                )
                last_queue_depth = queue_depth
            if self.device is not None:
                self.device.Render()
            self.blue.os.Pump()
            if time.time() - started > max_seconds:
                raise RuntimeError(
                    "Timed out loading %s; resource queue depth=%s" %
                    (reason, self.get_resource_queue_depth())
                )

    def load_blue_object(
        self,
        path,
        reason,
        non_cached=False,
        urgent=True,
    ):
        import stackless

        state = {
            "done": False,
            "object": None,
            "error": None,
        }

        def load_on_blue_tasklet():
            try:
                if non_cached:
                    self.blue.resMan.loadObjectCache.Delete(path)
                    self.blue.motherLode.Delete(path)
                self.blue.resMan.SetUrgentResourceLoads(bool(urgent))
                value = self.blue.resMan.LoadObject(path)
                if urgent:
                    self.blue.resMan.WaitUrgent()
                self.blue.resMan.Wait()
                if value is None:
                    value = self.blue.resMan.LoadObject(path)
                    if urgent:
                        self.blue.resMan.WaitUrgent()
                    self.blue.resMan.Wait()
                state["object"] = value
            except Exception:
                state["error"] = traceback.format_exc()
            finally:
                self.blue.resMan.SetUrgentResourceLoads(False)
                state["done"] = True

        stackless.tasklet(load_on_blue_tasklet)()
        deadline = time.time() + 30.0
        while not state["done"] and time.time() < deadline:
            if self.device is not None:
                self.device.Render()
            self.blue.os.Pump()
        if not state["done"]:
            raise RuntimeError("Timed out loading %s (%s)" % (reason, path))
        if state["error"]:
            raise RuntimeError(
                "Failed loading %s (%s):\n%s" %
                (reason, path, state["error"])
            )
        return state["object"]

    def copy_blue_object(self, resource_key, template, reason):
        import stackless

        state = {
            "done": False,
            "object": None,
            "error": None,
        }

        def copy_on_blue_tasklet():
            try:
                # CopyTo is Blue's native deep-copy path. The full client wraps
                # this in blue.recycler.RecycleOrCopy, but that Python package
                # is intentionally absent from exefile /py. Calling CopyTo
                # directly preserves independent Trinity ownership without
                # bootstrapping the game service runtime.
                state["object"] = template.CopyTo()
            except Exception:
                state["error"] = traceback.format_exc()
            finally:
                state["done"] = True

        stackless.tasklet(copy_on_blue_tasklet)()
        deadline = time.time() + 15.0
        while not state["done"] and time.time() < deadline:
            if self.device is not None:
                self.device.Render()
            self.blue.os.Pump()
        if not state["done"]:
            raise RuntimeError("Timed out copying %s" % reason)
        if state["error"]:
            raise RuntimeError("Failed copying %s:\n%s" % (reason, state["error"]))
        return state["object"]

    def build_space_object(self):
        sof_factory = self.get_sof_factory()
        self.pump_resource_loads("SOF data")
        space_object = None
        build_started = time.time()
        while space_object is None and time.time() - build_started < 15.0:
            space_object = sof_factory.BuildFromDNA(self.dna)
            if space_object is None:
                self.pump_resource_loads("SOF DNA %s" % self.dna, 1.0)
                self.blue.os.Pump()
        if space_object is None:
            raise RuntimeError("Trinity could not build SOF DNA %s" % self.dna)
        for curve_name in (
            "modelRotationCurve",
            "modelTranslationCurve",
            "rotationCurve",
            "translationCurve",
        ):
            if hasattr(space_object, curve_name):
                setattr(space_object, curve_name, None)
        if hasattr(space_object, "boosters"):
            self.original_boosters = space_object.boosters
        if hasattr(space_object, "FreezeHighDetailMesh"):
            space_object.FreezeHighDetailMesh()
        if hasattr(space_object, "StartControllers"):
            space_object.StartControllers()
        self.space_object = space_object
        self.apply_booster_state(rebuild=True)
        self.pump_resource_loads("space object")
        self.model_radius = float(space_object.GetBoundingSphereRadius())
        self.model_center = tuple(space_object.GetBoundingSphereCenter())
        if self.model_radius <= 0.0:
            self.model_radius = self.radius
        self.activation_possible = self.detect_activation_possible()
        self.populate_animation_list()
        self.populate_weapon_list()
        self.refresh_action_buttons()

    def get_sof_factory(self):
        if self.sof_factory is None:
            self.sof_factory = self.blue.classes.CreateInstance("trinity.EveSOF")
            self.sof_factory.dataMgr.LoadData("res:/dx9/model/spaceobjectfactory/data.black")
        return self.sof_factory

    def build_sof_object(self, dna, reason):
        sof_factory = self.get_sof_factory()
        self.pump_resource_loads("SOF data")
        model = None
        started = time.time()
        while model is None and time.time() - started < 15.0:
            model = sof_factory.BuildFromDNA(native_text(dna))
            if model is None:
                self.pump_resource_loads(reason, 1.0)
                self.blue.os.Pump()
        if model is None:
            raise RuntimeError("Trinity could not build %s SOF DNA %s" % (reason, dna))
        for curve_name in (
            "modelRotationCurve",
            "modelTranslationCurve",
            "rotationCurve",
            "translationCurve",
        ):
            if hasattr(model, curve_name):
                setattr(model, curve_name, None)
        if hasattr(model, "FreezeHighDetailMesh"):
            model.FreezeHighDetailMesh()
        if hasattr(model, "StartControllers"):
            model.StartControllers()
        return model

    def load_scene(self):
        tri = self.tri
        scene_path = self.scene_paths[self.scene_index % len(self.scene_paths)]
        scene = self.load_blue_object(scene_path, "scene", urgent=True)
        if scene is None:
            scene = tri.EveSpaceScene()
            scene.postprocess = tri.Tr2PostProcess2()
        elif hasattr(scene, "postprocess") and scene.postprocess is None:
            scene.postprocess = self.load_blue_object(
                "res:/dx9/default/postprocess.black",
                "default postprocess",
                urgent=True,
            ) or tri.Tr2PostProcess2()
        scene.sunDiffuseColor = (
            1.65 * self.light_scale,
            1.65 * self.light_scale,
            1.65 * self.light_scale,
            1.0,
        )
        scene.ambientColor = (
            0.28 * self.light_scale,
            0.28 * self.light_scale,
            0.28 * self.light_scale,
            1.0,
        )
        scene.reflectionIntensity = 1.2 * self.light_scale
        scene.backgroundReflectionIntensity = 1.0
        scene.backgroundRenderingEnabled = True
        scene.sunDirection = (-0.55, -0.72, 0.42)
        if not getattr(scene, "reflectionProbe", None):
            scene.reflectionProbe = tri.Tr2ReflectionProbe()
        scene.reflectionProbe.renderFrequency = (
            tri.ReflectionProbeRenderFrequency.AllSidesPerFrame
        )
        if not getattr(scene, "shLightingManager", None):
            scene.shLightingManager = tri.Tr2ShLightingManager()
        scene.shLightingManager.primaryIntensity = 3.14 * self.light_scale
        scene.shLightingManager.secondaryIntensity = 2.2 * self.light_scale
        if hasattr(scene, "gpuParticleSystem") and not getattr(scene, "gpuParticleSystem", None):
            scene.gpuParticleSystem = self.load_blue_object(
                "res:/fisfx/gpuparticles/system.black",
                "GPU particle system",
                urgent=True,
            )
        self.apply_nebula_to_scene(scene)
        scene.objects.append(self.space_object)
        self.scene = scene

    def get_current_nebula(self):
        if not self.nebula_cube_maps:
            return None
        return self.nebula_cube_maps[
            self.nebula_index % len(self.nebula_cube_maps)
        ]

    def set_effect_resource_path(self, effect, resource_name, resource_path):
        if effect is None or not hasattr(effect, "resources"):
            return False
        resources = effect.resources
        resource = None
        try:
            resource = resources.FindByName(resource_name)
        except Exception:
            resource = None
        if resource is None:
            return False
        try:
            resource.resourcePath = native_text(resource_path)
            return True
        except Exception:
            return False

    def apply_nebula_to_scene(self, scene=None):
        scene = scene or self.scene
        nebula = self.get_current_nebula()
        if scene is None or nebula is None:
            return False
        cube_path = native_text(nebula.get("cubePath"))
        reflection_path = native_text(nebula.get("reflectionPath") or cube_path.replace(".dds", "_refl.dds"))
        blur_path = native_text(nebula.get("blurPath") or cube_path.replace(".dds", "_blur.dds"))
        changed = False
        try:
            if hasattr(scene, "backgroundRenderingEnabled"):
                scene.backgroundRenderingEnabled = True
            if hasattr(scene, "nebulaIntensity"):
                scene.nebulaIntensity = 1.18
            if hasattr(scene, "backgroundReflectionIntensity"):
                scene.backgroundReflectionIntensity = 1.08
            if hasattr(scene, "envMapResPath"):
                scene.envMapResPath = reflection_path
                changed = True
            if hasattr(scene, "envMap1ResPath"):
                scene.envMap1ResPath = cube_path
                changed = True
            if hasattr(scene, "envMap2ResPath"):
                scene.envMap2ResPath = blur_path
                changed = True
            effect = getattr(scene, "backgroundEffect", None)
            changed = self.set_effect_resource_path(effect, "AlphaMap", reflection_path) or changed
            changed = self.set_effect_resource_path(effect, "NebulaMap", cube_path) or changed
        except Exception:
            print(traceback.format_exc(), file=sys.stderr)
        if changed:
            self.pump_resource_loads("nebula %s" % nebula.get("label", cube_path), 0.25)
        return changed

    def create_render_job(self):
        tri = self.tri
        self.render_driver = tri.EveSpaceSceneRenderDriver()
        self.render_driver.name = "ElysianLiveSpaceScene"
        self.render_driver.scene = self.scene
        self.render_driver.clearColor = (0.006, 0.012, 0.025, 1.0)
        self.render_driver.internalPixelFormat = tri.PIXEL_FORMAT.R16G16B16A16_FLOAT
        self.render_driver.shadowQuality = 3
        self.render_driver.antiAliasingQuality = 3
        self.render_driver.aoQuality = 3 if self.after_effects_enabled else 0
        self.render_driver.volumetricQuality = 3 if self.after_effects_enabled else 0
        self.render_driver.postProcessingQuality = 2 if self.post_enabled else 0
        self.render_driver.enableUpscaling = False
        self.render_driver.enableDistortion = bool(self.after_effects_enabled)
        self.render_driver.forceOpaqueBuffer = True
        self.render_driver.SSAO = self.load_blue_object(
            "res:/dx9/default/ssao.black",
            "default SSAO",
            urgent=True,
        ) or tri.Tr2SSAO()
        self.execute_node = tri.Tr2StepExecuteRenderNode()
        self.execute_node.name = "ElysianLiveExecuteSpaceScene"
        self.execute_node.node = self.render_driver
        self.execute_node.destinationTarget = (
            self.device.GetRenderContext().GetDefaultBackBuffer()
        )
        self.execute_node.clearTargetOnFailure = True
        job = tri.TriRenderJob()
        job.name = "ElysianLiveRecurringRender"
        job.steps.append(self.execute_node)
        self.render_jobs.recurring.append(job)

    def remove_scene_object(self, obj):
        if not self.scene or obj is None:
            return
        try:
            self.scene.objects.fremove(obj)
        except Exception:
            try:
                if obj in self.scene.objects:
                    self.scene.objects.remove(obj)
            except Exception:
                pass

    def clear_explosions(self):
        for obj in list(self.explosion_models):
            self.remove_scene_object(obj)
        self.explosion_models = []
        self.explosion_until = 0.0
        self.explosion_ship_hide_at = 0.0
        if (
            self.space_object is not None and
            self.explosion_restore_display is not None and
            hasattr(self.space_object, "display")
        ):
            self.space_object.display = self.explosion_restore_display
        self.explosion_restore_display = None

    def remove_from_trinity_list(self, collection, obj):
        if collection is None or obj is None:
            return
        try:
            collection.fremove(obj)
            return
        except Exception:
            pass
        try:
            collection.remove(obj)
        except Exception:
            pass

    def clear_preview_weapons(self):
        self.stop_dummy_fire()
        for entry in list(self.active_missiles):
            self.release_preview_missile(entry.get("model"))
        self.active_missiles = []
        for entry in list(self.active_weapon_impacts):
            self.remove_scene_object(entry.get("model"))
        self.active_weapon_impacts = []
        if self.space_object is not None and hasattr(self.space_object, "turretSets"):
            for turret_set in list(self.armed_turret_sets):
                effect = getattr(turret_set, "firingEffect", None)
                for stretch in list(getattr(effect, "stretch", []) or []):
                    for attr_name in ("sourceSpaceObject", "destSpaceObject"):
                        try:
                            if hasattr(stretch, attr_name):
                                setattr(stretch, attr_name, None)
                        except Exception:
                            pass
                try:
                    turret_set.targetObject = None
                except Exception:
                    pass
                try:
                    turret_set.firingEffect = None
                except Exception:
                    pass
                self.remove_from_trinity_list(self.space_object.turretSets, turret_set)
            if hasattr(self.space_object, "RebuildTurretPositions"):
                self.safe_call(self.space_object, "RebuildTurretPositions")
        self.armed_turret_sets = []
        self.armed_weapon = None
        if self.dummy_target is not None:
            self.remove_scene_object(self.dummy_target)
            self.dummy_target = None
        self.sync_control_text()
        self.update_title(force=True)

    def release_preview_missile(self, missile):
        if missile is None:
            return
        self.remove_scene_object(missile)
        for attr_name in ("target", "translationCurve", "rotationCurve", "explosionCallback"):
            try:
                if hasattr(missile, attr_name):
                    setattr(missile, attr_name, None)
            except Exception:
                pass
        for observer in list(getattr(missile, "observers", []) or []):
            try:
                observer.observer = None
            except Exception:
                pass
        warheads = getattr(missile, "warheads", None)
        if warheads:
            try:
                if len(warheads) > 1:
                    del warheads[1:]
                for observer in list(getattr(warheads[0], "observers", []) or []):
                    try:
                        observer.observer = None
                    except Exception:
                        pass
            except Exception:
                pass

    def can_arm_weapons(self):
        if self.space_object is None or not self.weapon_catalog:
            return False
        if not hasattr(self.space_object, "turretSets"):
            return False
        return self.get_turret_locator_count() > 0

    def get_turret_locator_count(self):
        if self.space_object is None:
            return 0
        if hasattr(self.space_object, "GetTurretLocatorCount"):
            try:
                return max(0, int(self.space_object.GetTurretLocatorCount()))
            except Exception:
                pass
        indices = set()
        locator_expression = re.compile(r"^locator_turret_([0-9]+)[a-z]$", re.I)
        for child in self.iter_known_children(self.space_object):
            try:
                name = native_text(getattr(child, "name", "") or child.GetName()).lower()
            except Exception:
                name = native_text(getattr(child, "name", "")).lower()
            match = locator_expression.match(name)
            if match:
                indices.add(int(match.group(1)))
        return len(indices)

    def current_ship_size_hint(self):
        group_name = native_text((self.current_asset or {}).get("groupName")).lower()
        if any(value in group_name for value in ("titan", "supercarrier", "capital", "dreadnought", "carrier", "force auxiliary")):
            return "xlarge"
        if any(value in group_name for value in ("battleship", "battlecruiser", "command ship")):
            return "large"
        if any(value in group_name for value in ("cruiser", "industrial", "mining barge", "exhumer")):
            return "medium"
        return "small"

    def weapon_family_preferences(self):
        sof = (self.current_asset or {}).get("sof") or {}
        race = native_text(sof.get("race")).lower()
        if race == "amarr":
            return ("energy", "missile", "hybrid", "projectile")
        if race == "caldari":
            return ("missile", "hybrid", "energy", "projectile")
        if race == "gallente":
            return ("hybrid", "missile", "energy", "projectile")
        if race == "minmatar":
            return ("projectile", "missile", "hybrid", "energy")
        return ("hybrid", "projectile", "energy", "missile")

    def select_preview_weapon(self, ignore_combo=False):
        if not self.weapon_catalog:
            return None
        if not ignore_combo and getattr(self, "weapon_display_indices", None):
            selected = self.get_combo_selection(IDC_WEAPON_LIST)
            if 0 <= selected < len(self.weapon_display_indices):
                self.selected_weapon_index = selected
                return self.weapon_catalog[self.weapon_display_indices[selected]]
        size_hint = self.current_ship_size_hint()
        families = self.weapon_family_preferences()

        def score(weapon):
            family_score = families.index(weapon.get("family")) if weapon.get("family") in families else 50
            size_score = 0 if weapon.get("size") == size_hint else 8
            launcher_penalty = 0 if weapon.get("kind") == "turret" else 2
            return (family_score, size_score, launcher_penalty, native_text(weapon.get("name")).lower())

        return sorted(self.weapon_catalog, key=score)[0]

    def make_translation_curve(self, position):
        curve = None
        try:
            curve = self.tri.Tr2TranslationAdapter()
        except Exception:
            try:
                curve = self.blue.classes.CreateInstance("trinity.Tr2TranslationAdapter")
            except Exception:
                curve = None
        if curve is not None:
            try:
                curve.value = position
            except Exception:
                pass
        return curve

    def make_rotation_curve(self):
        curve = None
        try:
            curve = self.tri.Tr2RotationAdapter()
        except Exception:
            try:
                curve = self.blue.classes.CreateInstance(
                    "trinity.Tr2RotationAdapter"
                )
            except Exception:
                curve = None
        if curve is not None:
            try:
                curve.value = (0.0, 0.0, 0.0, 1.0)
            except Exception:
                pass
        return curve

    def set_object_position(self, obj, position):
        for attr_name in ("translation", "position"):
            try:
                if hasattr(obj, attr_name):
                    setattr(obj, attr_name, position)
            except Exception:
                pass
        if hasattr(obj, "translationCurve"):
            curve = self.make_translation_curve(position)
            if curve is not None:
                try:
                    obj.translationCurve = curve
                except Exception:
                    pass
        if hasattr(obj, "modelTranslationCurve"):
            try:
                obj.modelTranslationCurve = None
            except Exception:
                pass

    def pick_dummy_target_asset(self):
        preferred_names = ("Punisher", "Merlin", "Incursus", "Rifter")
        for name in preferred_names:
            for entry in self.catalog:
                if (
                    int(entry.get("categoryID") or 0) == 6 and
                    native_text(entry.get("name")).lower() == name.lower() and
                    int(entry.get("typeID") or 0) != int(self.type_id)
                ):
                    return entry
        for entry in self.catalog:
            if int(entry.get("categoryID") or 0) == 6 and int(entry.get("typeID") or 0) != int(self.type_id):
                return entry
        return self.current_asset

    def ensure_dummy_target(self):
        if self.dummy_target is not None:
            return self.dummy_target
        target_asset = self.pick_dummy_target_asset()
        if not target_asset or not target_asset.get("dna"):
            return None
        target = self.build_sof_object(target_asset.get("dna"), "dummy target")
        distance = max(220.0, float(self.model_radius or self.radius or 1.0) * 7.0)
        self.dummy_target_position = (
            self.model_center[0] + distance,
            self.model_center[1] + max(25.0, distance * 0.08),
            self.model_center[2] - distance * 0.65,
        )
        self.set_object_position(target, self.dummy_target_position)
        try:
            if hasattr(target, "boundingSphereRadius"):
                target.boundingSphereRadius = max(10.0, float(target.GetBoundingSphereRadius()))
        except Exception:
            pass
        if self.scene is not None:
            self.scene.objects.append(target)
        self.dummy_target = target
        return target

    def assign_turret_target(self, turret_set, target):
        if turret_set is None or target is None:
            return
        try:
            turret_set.targetObject = target
        except Exception:
            pass
        for attr_name in ("targetPosition", "position"):
            try:
                if hasattr(turret_set, attr_name):
                    setattr(turret_set, attr_name, self.dummy_target_position)
            except Exception:
                pass

    def configure_turret_firing_effect(self, turret_set, target):
        effect_path = native_text(getattr(turret_set, "firingEffectResPath", "") or "")
        if not effect_path:
            return False
        effect, resolved_path = self.load_authored_object(
            effect_path,
            "turret firing effect",
            diagnostics=False,
        )
        if effect is None:
            print("[live] failed firing effect %s" % resolved_path, file=sys.stderr)
            return False
        try:
            turret_set.firingEffect = effect
        except Exception:
            return False
        for stretch in list(getattr(effect, "stretch", []) or []):
            for attr_name, value in (
                ("sourceSpaceObject", self.space_object),
                ("destSpaceObject", target),
            ):
                try:
                    if hasattr(stretch, attr_name):
                        setattr(stretch, attr_name, value)
                except Exception:
                    pass
        return True

    def get_preview_flight_seconds(self):
        preview = (self.armed_weapon or {}).get("missilePreview") or {}
        authored = float(preview.get("flightTimeSeconds") or 2.5)
        distance = math.sqrt(sum(
            (float(self.dummy_target_position[index]) - float(self.model_center[index])) ** 2
            for index in range(3)
        ))
        velocity = float(preview.get("maxVelocity") or 0.0)
        physical = distance / velocity if velocity > 0.0 else 0.0
        return max(2.4, min(5.5, max(physical, authored * 0.25)))

    def spawn_authored_missile(self, turret_set, target):
        preview = (self.armed_weapon or {}).get("missilePreview") or {}
        missile_path = preview.get("missilePath")
        if not missile_path:
            return False
        weapon_trace("missile load begin %s" % missile_path)
        template = self.missile_templates.get(missile_path)
        resolved_path = missile_path
        if template is None:
            template, resolved_path = self.load_authored_object(
                missile_path,
                "missile preview template",
                diagnostics=False,
            )
            if template is not None:
                self.missile_templates[missile_path] = template
        missile = None
        if template is not None:
            try:
                missile = self.copy_blue_object(
                    "%s:jessicaMissile" % missile_path,
                    template,
                    "missile preview",
                )
            except Exception:
                weapon_trace("missile copy failed %s" % traceback.format_exc())
        warheads = list(getattr(missile, "warheads", []) or []) if missile is not None else []
        weapon_trace("missile load complete model=%s warheads=%s" % (
            type(missile).__name__ if missile is not None else "None",
            len(warheads),
        ))
        if missile is None or not warheads:
            print("[live] failed missile model %s" % resolved_path, file=sys.stderr)
            return False
        source_position = tuple(self.model_center)
        source_curve = self.make_translation_curve(source_position)
        rotation_curve = self.make_rotation_curve()
        try:
            missile.translationCurve = source_curve
        except Exception:
            pass
        try:
            missile.rotationCurve = rotation_curve
        except Exception:
            pass
        try:
            missile.name = "JessicaMissilePreview"
        except Exception:
            pass
        try:
            missile.display = True
        except Exception:
            pass
        weapon_trace("missile curves assigned")
        try:
            missile.target = target
            missile.targetRadius = max(
                1.0,
                float(getattr(target, "boundingSphereRadius", 0.0) or target.GetBoundingSphereRadius()),
            )
        except Exception:
            pass
        weapon_trace("missile target assigned")
        self.scene.objects.append(missile)
        weapon_trace("missile appended to scene")
        warhead = warheads[0]
        self.safe_call(warhead, "PrepareLaunch")
        weapon_trace("warhead prepared")
        launch_transform = None
        try:
            fire_index = int(getattr(turret_set, "currentCyclingFiresPos", 0) or 0)
            launch_transform = turret_set.GetFiringBoneWorldTransform(fire_index)
            missile_world = self.geo2.MatrixTranslation(*source_position)
            launch_transform = self.geo2.MatrixMultiply(
                launch_transform,
                self.geo2.MatrixInverse(missile_world),
            )
        except Exception:
            launch_transform = None
        if launch_transform is None:
            try:
                launch_transform = self.geo2.MatrixTranslation(*source_position)
            except Exception:
                launch_transform = self.geo2.MatrixIdentity()
        weapon_trace("launch transform ready")
        self.safe_call(warhead, "Launch", launch_transform)
        weapon_trace("warhead launched")
        flight_seconds = self.get_preview_flight_seconds()
        self.safe_call(missile, "Start", (0.0, 0.0, 0.0), flight_seconds)
        weapon_trace("missile started duration=%s" % flight_seconds)
        started_at = time.time()
        self.active_missiles.append({
            "model": missile,
            "curve": source_curve,
            "rotationCurve": rotation_curve,
            "sourcePosition": source_position,
            "targetPosition": tuple(self.dummy_target_position),
            "impactPath": preview.get("impactPath"),
            "startedAt": started_at,
            "impactAt": started_at + flight_seconds,
        })
        return True

    def spawn_weapon_impact(self, impact_path):
        if not impact_path:
            return
        template = self.impact_templates.get(impact_path)
        if template is None:
            template, _resolved_path = self.load_authored_object(
                impact_path,
                "missile impact template",
                diagnostics=False,
            )
            if template is not None:
                self.impact_templates[impact_path] = template
        impact = None
        if template is not None:
            try:
                impact = self.copy_blue_object(
                    "%s:jessicaImpact" % impact_path,
                    template,
                    "missile impact",
                )
            except Exception:
                weapon_trace("impact copy failed %s" % traceback.format_exc())
        if impact is None:
            return
        self.set_object_position(impact, self.dummy_target_position)
        self.scene.objects.append(impact)
        for method_name in ("StartControllers", "Start", "Play"):
            self.safe_call(impact, method_name)
        self.active_weapon_impacts.append({
            "model": impact,
            "removeAt": time.time() + 4.0,
        })

    def update_weapon_projectiles(self, now):
        pending_missiles = []
        for entry in self.active_missiles:
            impact_at = entry.get("impactAt", 0.0)
            if now < impact_at:
                started_at = entry.get("startedAt", now)
                duration = max(0.001, impact_at - started_at)
                progress = max(0.0, min(1.0, (now - started_at) / duration))
                eased = progress * progress * (3.0 - (2.0 * progress))
                source = entry.get("sourcePosition", (0.0, 0.0, 0.0))
                target = entry.get("targetPosition", source)
                arc = math.sin(math.pi * progress) * max(
                    4.0,
                    math.sqrt(sum(
                        (target[index] - source[index]) ** 2
                        for index in range(3)
                    )) * 0.035,
                )
                position = (
                    source[0] + ((target[0] - source[0]) * eased),
                    source[1] + ((target[1] - source[1]) * eased) + arc,
                    source[2] + ((target[2] - source[2]) * eased),
                )
                try:
                    entry.get("curve").value = position
                except Exception:
                    pass
                pending_missiles.append(entry)
                continue
            self.release_preview_missile(entry.get("model"))
            self.spawn_weapon_impact(entry.get("impactPath"))
        self.active_missiles = pending_missiles
        pending_impacts = []
        for entry in self.active_weapon_impacts:
            if now < entry.get("removeAt", 0.0):
                pending_impacts.append(entry)
                continue
            self.remove_scene_object(entry.get("model"))
        self.active_weapon_impacts = pending_impacts

    def arm_max_turrets(self):
        if not self.can_arm_weapons():
            self.refresh_action_buttons()
            print("[live] selected asset has no turret locators", file=sys.stderr)
            return
        self.clear_preview_weapons()
        weapon = self.select_preview_weapon()
        if not weapon:
            print("[live] no weapon preview resources in catalog", file=sys.stderr)
            return
        locator_count = min(32, self.get_turret_locator_count())
        if locator_count <= 0:
            print("[live] selected asset has no turret locator count", file=sys.stderr)
            return
        target = self.ensure_dummy_target()
        mounted = 0
        for slot_number in range(1, locator_count + 1):
            turret_set, res_path = self.load_authored_object(
                weapon.get("resourcePath"),
                "weapon preview",
                diagnostics=os.environ.get("ELYSIAN_JESSICA_DEBUG_WEAPONS") == "1",
            )
            if turret_set is None:
                continue
            try:
                turret_set.name = "JessicaPreviewWeapon%s" % slot_number
            except Exception:
                pass
            for attr_name, value in (
                ("display", True),
                ("displayEffects", True),
                ("isOnline", True),
                ("useRandomFiringDelay", True),
            ):
                try:
                    if hasattr(turret_set, attr_name):
                        setattr(turret_set, attr_name, value)
                except Exception:
                    pass
            try:
                turret_set.locatorName = "locator_turret_"
            except Exception:
                pass
            try:
                turret_set.slotNumber = slot_number
            except Exception:
                pass
            self.assign_turret_target(turret_set, target)
            self.configure_turret_firing_effect(turret_set, target)
            try:
                self.get_sof_factory().SetupTurretMaterialFromDNA(turret_set, self.dna)
            except Exception:
                try:
                    sof = (self.current_asset or {}).get("sof") or {}
                    self.get_sof_factory().SetupTurretMaterialFromFaction(
                        turret_set,
                        native_text(sof.get("faction") or sof.get("race") or "generic"),
                    )
                except Exception:
                    pass
            self.space_object.turretSets.append(turret_set)
            self.armed_turret_sets.append(turret_set)
            mounted += 1
        if hasattr(self.space_object, "RebuildTurretPositions"):
            self.safe_call(self.space_object, "RebuildTurretPositions")
        for turret_set in self.armed_turret_sets:
            self.safe_call(turret_set, "StartControllers")
            self.safe_call(turret_set, "EnterStateIdle")
        self.armed_weapon = weapon
        self.pump_resource_loads("weapon preview", 1.5)
        self.sync_control_text()
        self.update_title(force=True)
        print("[live] armed %s/%s hardpoints with %s (%s)" % (
            mounted,
            locator_count,
            weapon.get("name"),
            weapon.get("resourcePath"),
        ), file=sys.stderr)

    def fire_preview_weapons_once(self):
        target = self.ensure_dummy_target()
        if target is None:
            return
        for turret_set in list(self.armed_turret_sets):
            self.assign_turret_target(turret_set, target)
            self.safe_call(turret_set, "StartControllers")
            if not self.safe_call(turret_set, "EnterStateFiring"):
                self.safe_call(turret_set, "ForceStateTargeting")
                self.safe_call(turret_set, "EnterStateFiring")
            if (
                self.armed_weapon and
                self.armed_weapon.get("kind") == "launcher"
            ):
                self.spawn_authored_missile(turret_set, target)

    def start_dummy_fire(self):
        if not self.armed_turret_sets:
            self.arm_max_turrets()
        if not self.armed_turret_sets:
            return
        self.firing_dummy = True
        self.next_dummy_fire_at = 0.0
        self.fire_preview_weapons_once()
        self.sync_control_text()
        self.update_title(force=True)

    def stop_dummy_fire(self):
        if not self.firing_dummy and not self.armed_turret_sets:
            return
        self.firing_dummy = False
        for turret_set in list(self.armed_turret_sets):
            if not self.safe_call(turret_set, "EnterStateIdle"):
                self.safe_call(turret_set, "ForceStateTargeting")
        self.sync_control_text()
        self.update_title(force=True)

    def toggle_dummy_fire(self):
        if self.firing_dummy:
            self.stop_dummy_fire()
        else:
            self.start_dummy_fire()

    def reload_current_asset(self):
        self.current_asset = self.resolve_current_asset()
        if self.current_asset:
            self.type_id = int(self.current_asset.get("typeID") or self.type_id)
            self.dna = native_text(self.current_asset.get("dna") or self.dna)
            self.radius = float(self.current_asset.get("radius") or self.radius)
        self.clear_preview_weapons()
        self.clear_explosions()
        self.scene_paths = self.build_scene_paths()
        self.scene_index = 0
        self.space_object = None
        self.original_boosters = None
        self.activation_possible = False
        self.refresh_action_buttons()
        self.build_space_object()
        self.load_scene()
        if self.render_driver:
            self.render_driver.scene = self.scene
            self.apply_render_flags()
        self.update_camera()
        self.sync_control_text()
        self.update_title(force=True)

    def get_selected_list_index(self):
        listbox = self.controls.get(IDC_ASSET_LIST)
        if not listbox:
            return self.catalog_index
        selected = int(USER32.SendMessageA(listbox, LB_GETCURSEL, 0, 0))
        if 0 <= selected < len(self.displayed_catalog_indices):
            return self.displayed_catalog_indices[selected]
        return -1

    def select_catalog_index(self, index, load=False):
        if not self.catalog:
            return
        self.catalog_index = max(0, min(len(self.catalog) - 1, int(index)))
        listbox = self.controls.get(IDC_ASSET_LIST)
        if listbox:
            try:
                selected_row = self.displayed_catalog_indices.index(self.catalog_index)
            except ValueError:
                selected_row = -1
            if selected_row >= 0:
                USER32.SendMessageA(listbox, LB_SETCURSEL, selected_row, 0)
        if load:
            self.reload_current_asset()

    def load_selected_from_list(self):
        selected_index = self.get_selected_list_index()
        if selected_index >= 0:
            self.select_catalog_index(selected_index, load=True)

    def step_catalog(self, delta):
        if not self.catalog or not self.filtered_catalog_indices:
            return
        try:
            current_position = self.filtered_catalog_indices.index(self.catalog_index)
        except ValueError:
            current_position = 0 if delta >= 0 else len(self.filtered_catalog_indices) - 1
        next_position = (
            current_position + delta
        ) % len(self.filtered_catalog_indices)
        self.select_catalog_index(self.filtered_catalog_indices[next_position], load=True)

    def apply_render_flags(self):
        if not self.render_driver:
            return
        self.render_driver.aoQuality = 3 if self.after_effects_enabled else 0
        self.render_driver.volumetricQuality = 3 if self.after_effects_enabled else 0
        self.render_driver.postProcessingQuality = 2 if self.post_enabled else 0
        self.render_driver.enableDistortion = bool(self.after_effects_enabled)
        if self.after_effects_enabled and self.render_driver.SSAO is None:
            self.render_driver.SSAO = self.load_blue_object(
                "res:/dx9/default/ssao.black",
                "default SSAO",
                urgent=True,
            ) or self.tri.Tr2SSAO()
        elif not self.after_effects_enabled:
            self.render_driver.SSAO = None

    def set_ultra_quality(self):
        if not self.render_driver:
            return
        self.light_scale = max(self.light_scale, 1.25)
        self.post_enabled = True
        self.after_effects_enabled = True
        self.render_driver.shadowQuality = 3
        self.render_driver.antiAliasingQuality = 3
        self.apply_render_flags()
        self.load_scene()
        self.render_driver.scene = self.scene
        self.apply_render_flags()
        self.update_camera()
        self.sync_control_text()
        self.update_title(force=True)

    def toggle_post(self):
        self.post_enabled = not self.post_enabled
        self.apply_render_flags()
        self.sync_control_text()
        self.update_title(force=True)

    def toggle_after_effects(self):
        self.after_effects_enabled = not self.after_effects_enabled
        self.apply_render_flags()
        self.sync_control_text()
        self.update_title(force=True)

    def adjust_light(self, delta):
        self.light_scale = max(0.45, min(4.0, self.light_scale + delta))
        self.load_scene()
        if self.render_driver:
            self.render_driver.scene = self.scene
            self.apply_render_flags()
        self.update_camera()
        self.update_title(force=True)

    def current_explosion_options(self):
        asset = self.current_asset or {}
        options = asset.get("explosions") or []
        return [entry for entry in options if entry.get("filePath")]

    def load_authored_object(
        self,
        res_path,
        reason,
        diagnostics=False,
    ):
        resolved_path = native_text(res_path)
        candidates = []
        if str(resolved_path).lower().endswith(".red"):
            candidates.append(resolved_path[:-4] + ".black")
            candidates.append(resolved_path)
        elif str(resolved_path).lower().endswith(".black"):
            candidates.append(resolved_path)
            candidates.append(resolved_path[:-6] + ".red")
        else:
            candidates.append(resolved_path)
        diagnostics_rows = []
        for candidate in candidates:
            model = None
            exists = "unknown"
            try:
                exists = bool(self.blue.paths.exists(candidate))
            except Exception as exc:
                exists = "error:%s" % exc
            res_error = ""
            try:
                model = self.load_blue_object(
                    candidate,
                    reason,
                    non_cached=diagnostics,
                    urgent=True,
                )
            except Exception as exc:
                res_error = "%s: %s" % (exc.__class__.__name__, exc)
                model = None
            diagnostics_rows.append({
                "path": candidate,
                "exists": exists,
                "type": type(model).__name__ if model is not None else "None",
                "loadError": res_error,
            })
            if model is not None:
                if diagnostics:
                    print("[live] loaded %s diagnostics=%s" % (
                        candidate,
                        json.dumps(diagnostics_rows),
                    ), file=sys.stderr)
                return model, candidate
        if diagnostics:
            print("[live] load diagnostics=%s" % json.dumps(diagnostics_rows), file=sys.stderr)
        return None, resolved_path

    def get_explosion_locator_transforms(self, model, set_name):
        if model is None or not hasattr(model, "locatorSets"):
            return []
        locator_set = model.locatorSets.FindByName(set_name)
        if locator_set is None and set_name == "explosions":
            locator_set = model.locatorSets.FindByName("damage")
        locators = locator_set.locators if locator_set else []
        try:
            transformed = model.TransformLocators(locators)
            return [(entry[0], entry[1]) for entry in transformed]
        except Exception:
            return []

    def configure_child_explosions(self, explosion_model, explosion):
        geo2 = self.geo2

        explosion_children = (
            explosion_model.Find("trinity.EveChildExplosion", 2)
            if hasattr(explosion_model, "Find")
            else []
        )
        transforms = []
        global_explosion_offset = (0.0, 0.0, 0.0)
        local_locators = self.get_explosion_locator_transforms(
            self.space_object,
            "explosions",
        )
        damage_locators = self.get_explosion_locator_transforms(
            self.space_object,
            "damage",
        )
        global_offsets = self.get_explosion_locator_transforms(
            self.space_object,
            "globalExplosionOffset",
        )
        if global_offsets:
            global_explosion_offset = random.choice(global_offsets)[0]
        locators = list(local_locators)
        local_count = int(explosion.get("localExplosionCount") or -1)
        sorting = explosion.get("childExplosionType")
        if locators:
            if local_count != -1:
                random.shuffle(locators)
                locators = locators[:min(len(locators), max(0, local_count))]
            if sorting == 1:
                point = self.space_object.GetBoundingSphereCenter()
                radius = self.space_object.GetBoundingSphereRadius() * 0.2
                locators.sort(key=lambda entry: (
                    geo2.Vec3Distance(point, entry[0]) +
                    ((random.random() - random.random()) * radius)
                ))
            elif sorting == 2 and damage_locators:
                point = random.choice(damage_locators)
                locators.sort(key=lambda entry: geo2.Vec3Distance(point[0], entry[0]))
                locators.insert(0, point)
                locators = locators[:max(1, len(local_locators))]
            else:
                random.shuffle(locators)
            for position, direction in locators:
                transforms.append(geo2.MatrixTransformation(
                    (0, 0, 0),
                    (0, 0, 0, 1),
                    (1, 1, 1),
                    (0, 0, 0),
                    direction,
                    position,
                ))
        local_scale = float(explosion.get("localScale") or 1.0)
        global_scale = float(explosion.get("globalScale") or 1.0)
        wreck_switch = float(explosion.get("modelSwitchDelayInMs") or 0.0) * 0.001
        for child in explosion_children:
            if hasattr(child, "scaling"):
                child.scaling = (local_scale, local_scale, local_scale)
            if hasattr(child, "localScaling"):
                child.localScaling = (local_scale, local_scale, local_scale)
            if hasattr(child, "globalScaling"):
                child.globalScaling = (global_scale, global_scale, global_scale)
            if hasattr(child, "wreckSwitchOffsetFromGlobalStart"):
                child.wreckSwitchOffsetFromGlobalStart = wreck_switch
            if hasattr(child, "SetLocalExplosionTransforms"):
                child.SetLocalExplosionTransforms(transforms)
            if hasattr(child, "SetGlobalExplosionOffset"):
                child.SetGlobalExplosionOffset(global_explosion_offset)
        return explosion_children

    def play_explosion(self):
        options = self.current_explosion_options()
        if not options:
            self.refresh_action_buttons()
            self.update_title(force=True)
            print("[live] no explosion data for type %s" % self.type_id, file=sys.stderr)
            return
        random.shuffle(options)
        explosion = None
        model = None
        res_path = None
        failed_paths = []
        for candidate in options:
            model, res_path = self.load_authored_object(
                candidate.get("compiledFilePath") or candidate.get("filePath"),
                "explosion",
                diagnostics=os.environ.get("ELYSIAN_JESSICA_DEBUG_EFFECTS") == "1",
            )
            if model is not None:
                explosion = candidate
                break
            failed_paths.append(res_path)
        if model is None or explosion is None:
            print("[live] failed to load explosion %s" % ", ".join(failed_paths), file=sys.stderr)
            return
        try:
            if hasattr(model, "translationCurve") and hasattr(self.space_object, "translationCurve"):
                model.translationCurve = self.space_object.translationCurve
            if hasattr(model, "rotationCurve") and hasattr(self.space_object, "rotationCurve"):
                model.rotationCurve = self.space_object.rotationCurve
            scale = max(0.01, float(getattr(self.space_object, "modelScale", 1.0) or 1.0))
            if hasattr(model, "scaling"):
                model.scaling = (scale, scale, scale)
            child_explosions = self.configure_child_explosions(model, explosion)
            self.scene.objects.append(model)
            duration = 8.0
            if hasattr(model, "Start"):
                model.Start()
            if hasattr(model, "Play"):
                model.Play()
            for child in child_explosions:
                if hasattr(child, "Play"):
                    child.Play()
                duration = max(duration, float(getattr(child, "totalDuration", 0) or 0))
            global_explosion_start = max([
                float(getattr(child, "globalExplosionTime", 0) or 0)
                for child in child_explosions
            ] or [0.0])
            wreck_switch_delay = (
                global_explosion_start +
                (float(explosion.get("modelSwitchDelayInMs") or 0.0) * 0.001)
            )
            if hasattr(self.space_object, "display"):
                self.explosion_restore_display = bool(self.space_object.display)
                self.explosion_ship_hide_at = time.time() + max(
                    0.0,
                    wreck_switch_delay,
                )
            self.explosion_models.append(model)
            self.explosion_until = max(self.explosion_until, time.time() + min(18.0, duration + 1.0))
            print("[live] explosion %s" % res_path, file=sys.stderr)
            self.update_title(force=True)
        except Exception:
            print(traceback.format_exc(), file=sys.stderr)

    def resize(self):
        if not self.device or not self.render_driver:
            return
        width, height = get_client_size(self.hwnd)
        backbuffer = self.device.GetRenderContext().GetDefaultBackBuffer()
        if backbuffer and (backbuffer.width != width or backbuffer.height != height):
            self.device.ChangeBackBufferSize(width, height)
        self.execute_node.destinationTarget = (
            self.device.GetRenderContext().GetDefaultBackBuffer()
        )
        self.update_camera(width, height)

    def update_camera(self, width=None, height=None):
        tri = self.tri
        width, height = (width, height) if width and height else get_client_size(self.hwnd)
        model_radius = max(0.05, max(float(self.radius or 0.0), float(self.model_radius or 0.0)))
        distance = max(model_radius * 0.055, model_radius * 3.1 * max(0.015, self.zoom))
        near_plane = max(0.001, min(8.0, distance * 0.0015))
        far_plane = max(1000000.0, distance * 18.0, model_radius * 40.0)
        focus = (
            self.model_center[0] + self.camera_pan[0],
            self.model_center[1] + self.camera_pan[1],
            self.model_center[2] + self.camera_pan[2],
        )
        eye = (
            focus[0] + math.sin(self.yaw) * math.cos(self.pitch) * distance,
            focus[1] + math.sin(self.pitch) * distance,
            focus[2] + math.cos(self.yaw) * math.cos(self.pitch) * distance,
        )
        view = tri.TriView()
        view.SetLookAtPosition(eye, focus, (0.0, 1.0, 0.0))
        projection = tri.TriProjection()
        projection.PerspectiveFov(
            0.84,
            float(width) / float(max(1, height)),
            near_plane,
            far_plane,
        )
        self.render_driver.view = view
        self.render_driver.projection = projection
        self.render_driver.visualizeMethod = VISUAL_MODES[self.mode_index][1]
        if self.scene is not None:
            self.scene.sunDirection = (
                math.sin(self.yaw),
                0.32,
                math.cos(self.yaw),
            )

    def apply_booster_state(self, rebuild=False):
        if not self.space_object or not hasattr(self.space_object, "boosters"):
            return False
        boosters = self.space_object.boosters
        if boosters is None:
            return False
        enabled = bool(self.boosters_enabled)
        if hasattr(boosters, "alwaysOn"):
            boosters.alwaysOn = enabled
        if hasattr(boosters, "alwaysOnIntensity"):
            boosters.alwaysOnIntensity = 1.0 if enabled else 0.0
        if rebuild and hasattr(self.space_object, "RebuildBoosterSet"):
            self.space_object.RebuildBoosterSet()
        return True

    def toggle_boosters(self):
        self.boosters_enabled = not self.boosters_enabled
        if not self.apply_booster_state(rebuild=True):
            print("[live] no booster controller for type %s" % self.type_id, file=sys.stderr)
        self.sync_control_text()
        self.update_title(force=True)

    def safe_call(self, obj, method_name, *args):
        try:
            if not hasattr(obj, method_name):
                return False
            method = getattr(obj, method_name)
            method(*args)
            return True
        except Exception:
            return False

    def set_bool_attr(self, obj, attr_name, value):
        try:
            if not hasattr(obj, attr_name):
                return False
            setattr(obj, attr_name, bool(value))
            return True
        except Exception:
            return False

    def iter_known_children(self, obj):
        child_attrs = (
            "objects",
            "children",
            "curveSets",
            "controllers",
            "effectChildren",
            "backgroundObjects",
            "turretSets",
            "locators",
            "locatorSets",
        )
        for attr in child_attrs:
            try:
                children = getattr(obj, attr)
            except Exception:
                children = None
            if not children:
                continue
            try:
                for child in children:
                    if child is not None:
                        yield child
            except Exception:
                continue
        if hasattr(obj, "Find"):
            for class_name in (
                "trinity.TriCurveSet",
                "trinity.Tr2CurveSet",
                "trinity.Tr2Controller",
                "trinity.Tr2Effect",
                "trinity.EveChild",
                "trinity.EveChildContainer",
                "trinity.EveChildEffect",
                "trinity.EveTransform",
                "trinity.EveTurretSet",
            ):
                try:
                    for child in obj.Find(class_name, 2):
                        if child is not None:
                            yield child
                except Exception:
                    continue

    def has_nonempty_collection(self, obj, attr_name):
        try:
            children = getattr(obj, attr_name)
        except Exception:
            return False
        if not children:
            return False
        try:
            return len(children) > 0
        except Exception:
            try:
                for _child in children:
                    return True
            except Exception:
                return False
        return False

    def has_callable_hook(self, obj, method_names):
        for method_name in method_names:
            try:
                method = getattr(obj, method_name)
            except Exception:
                method = None
            if method is not None and callable(method):
                return True
        return False

    def detect_activation_possible(self):
        if self.space_object is None:
            return False
        asset_kind = native_text((self.current_asset or {}).get("assetKind")).lower()
        if asset_kind == "gate":
            return self.has_callable_hook(self.space_object, ("SetControllerVariable", "HandleControllerEvent", "StartControllers"))
        queue = [self.space_object]
        seen = set()
        scanned = 0
        activation_methods = (
            "Open",
            "Activate",
            "Online",
            "SetIsShooting",
        )
        activation_name_expression = re.compile(
            r"(activate|activation|online|offline|open|close|arrival|departure|jump|gate|fire|shoot|launch)",
            re.I,
        )
        while queue and scanned < 900:
            obj = queue.pop(0)
            try:
                marker = id(obj)
            except Exception:
                marker = None
            if marker is not None and marker in seen:
                continue
            if marker is not None:
                seen.add(marker)
            scanned += 1
            if self.has_callable_hook(obj, activation_methods):
                return True
            try:
                obj_name = native_text(getattr(obj, "name", "")).lower()
            except Exception:
                obj_name = ""
            class_name = type(obj).__name__.lower()
            if (
                (
                    "controller" in class_name or
                    "effect" in class_name or
                    "animation" in class_name
                ) and
                activation_name_expression.search("%s %s" % (class_name, obj_name)) and
                self.has_callable_hook(obj, ("Play", "Restart", "Start"))
            ):
                return True
            for child in self.iter_known_children(obj):
                queue.append(child)
        return False

    def activate_gate_model(self):
        if self.space_object is None:
            return 0
        hooks = 0
        for name, value in (
            ("ActivationState", 2.0),
            ("InvasionState", 0.0),
            ("enablePropaganda", 1.0),
            ("corruption", 0.0),
            ("suppression", 0.0),
            ("itemIdSeed", float((int(self.type_id) << 8) % 1000)),
        ):
            if self.safe_call(self.space_object, "SetControllerVariable", name, value):
                hooks += 1
        if self.safe_call(self.space_object, "StartControllers"):
            hooks += 1
        event_names = ("Arrival", "Departure")
        event_name = event_names[self.activation_step % len(event_names)]
        self.activation_step += 1
        if self.safe_call(self.space_object, "HandleControllerEvent", event_name):
            hooks += 1
        return hooks

    def activate_object_node(self, obj):
        count = 0
        for attr_name in (
            "display",
            "enabled",
            "isEnabled",
            "active",
            "isActive",
            "online",
            "playOnLoad",
        ):
            if self.set_bool_attr(obj, attr_name, True):
                count += 1
        for method_name in (
            "StartControllers",
            "Rebuild",
            "RebuildBoosterSet",
            "Start",
            "Play",
            "Restart",
            "Update",
            "Open",
            "Activate",
            "Online",
            "EnterStateFiring",
            "StartShooting",
            "Fire",
            "Shoot",
        ):
            if self.safe_call(obj, method_name):
                count += 1
        for state_value in (True, 1):
            if self.safe_call(obj, "SetIsShooting", state_value):
                count += 1
                break
        for state_value in ("active", "Active", "on", "On", 1, True):
            if self.safe_call(obj, "SetState", state_value):
                count += 1
                break
            if self.safe_call(obj, "EnterState", state_value):
                count += 1
                break
        for animation_name in ("active", "Active", "open", "Open", "online", "Online"):
            if self.safe_call(obj, "PlayAnimation", animation_name):
                count += 1
                break
            if self.safe_call(obj, "SetAnimationState", animation_name):
                count += 1
                break
        return count

    def activate_current_model(self):
        if not self.activation_possible:
            self.refresh_action_buttons()
            print("[live] no activatable controller/effect hooks for type %s" % self.type_id, file=sys.stderr)
            return
        if self.space_object is None:
            return
        if native_text((self.current_asset or {}).get("assetKind")).lower() == "gate":
            hooks = self.activate_gate_model()
            self.pump_resource_loads("activate gate %s" % self.type_id, 0.2)
            self.update_title(force=True)
            print("[live] gate activate hooks=%s type=%s" % (
                hooks,
                self.type_id,
            ), file=sys.stderr)
            return
        queue = [self.space_object]
        seen = set()
        hooks = 0
        scanned = 0
        while queue and scanned < 1600:
            obj = queue.pop(0)
            try:
                marker = id(obj)
            except Exception:
                marker = None
            if marker is not None and marker in seen:
                continue
            if marker is not None:
                seen.add(marker)
            scanned += 1
            hooks += self.activate_object_node(obj)
            for child in self.iter_known_children(obj):
                queue.append(child)
        self.apply_booster_state(rebuild=True)
        self.pump_resource_loads("activate %s" % self.type_id, 0.2)
        self.update_title(force=True)
        print("[live] activate scanned=%s hooks=%s type=%s" % (
            scanned,
            hooks,
            self.type_id,
        ), file=sys.stderr)

    def cycle_mode(self):
        self.mode_index = (self.mode_index + 1) % len(VISUAL_MODES)
        self.update_camera()
        self.sync_control_text()
        self.update_title(force=True)

    def cycle_scene(self):
        self.nebula_index = (self.nebula_index + 1) % len(self.nebula_cube_maps)
        self.apply_nebula_to_scene(self.scene)
        self.update_camera()
        self.sync_control_text()
        self.update_title(force=True)

    def cycle_light(self):
        self.adjust_light(0.25)

    def zoom_by(self, factor):
        self.zoom = max(0.015, min(12.0, self.zoom * factor))
        self.update_camera()
        self.update_title(force=True)

    def reset_camera(self):
        self.yaw = 0.0
        self.pitch = 0.22
        self.zoom = 1.0
        self.camera_pan = [0.0, 0.0, 0.0]
        self.update_camera()
        self.update_title(force=True)

    def handle_key(self, key):
        if key == VK_ESCAPE:
            self.running = False
            ctypes.windll.user32.PostQuitMessage(0)
            return 0
        if key == VK_RETURN:
            self.handle_search_changed()
            if self.filtered_catalog_indices:
                self.select_catalog_index(self.filtered_catalog_indices[0], load=False)
            return 0
        if key == VK_SPACE:
            self.paused = not self.paused
            self.update_title(force=True)
            return 0
        normalized = chr(int(key)).upper() if 32 <= int(key) <= 126 else ""
        if normalized == "B":
            self.toggle_boosters()
            return 0
        if normalized == "A":
            self.activate_current_model()
            return 0
        if normalized == "W":
            self.cycle_mode()
            return 0
        if normalized == "N":
            self.cycle_scene()
            return 0
        if normalized == "L":
            self.cycle_light()
            return 0
        if key in (VK_ADD, VK_OEM_PLUS):
            self.zoom_by(0.88)
            return 0
        if key in (VK_SUBTRACT, VK_OEM_MINUS):
            self.zoom_by(1.14)
            return 0
        return None

    def handle_command(self, wparam):
        control_id = loword(wparam)
        notification = hiword(wparam)
        if control_id == IDC_ASSET_LIST:
            if notification == LBN_DBLCLK:
                self.load_selected_from_list()
            return 0
        if control_id == IDC_SEARCH:
            if notification == EN_CHANGE:
                self.schedule_search_update()
            return 0
        if control_id in dict(FILTER_CONTROLS):
            self.handle_search_changed(force=True)
            return 0
        if control_id == IDC_LOAD:
            self.load_selected_from_list()
        elif control_id == IDC_PREV:
            self.step_catalog(-1)
        elif control_id == IDC_NEXT:
            self.step_catalog(1)
        elif control_id == IDC_MODE:
            self.cycle_mode()
        elif control_id == IDC_NEBULA:
            self.cycle_scene()
        elif control_id == IDC_LIGHT_UP:
            self.adjust_light(0.25)
        elif control_id == IDC_LIGHT_DOWN:
            self.adjust_light(-0.25)
        elif control_id == IDC_BOOSTERS:
            self.toggle_boosters()
        elif control_id == IDC_POST:
            self.toggle_post()
        elif control_id == IDC_AFTER:
            self.toggle_after_effects()
        elif control_id == IDC_EXPLODE:
            self.play_explosion()
        elif control_id == IDC_ACTIVATE:
            self.activate_current_model()
        elif control_id == IDC_ARM_MAX:
            self.arm_max_turrets()
        elif control_id == IDC_FIRE_DUMMY:
            self.toggle_dummy_fire()
        elif control_id == IDC_CLEAR_WEAPONS:
            self.clear_preview_weapons()
        elif control_id == IDC_PLAY_ANIMATION:
            self.play_selected_animation()
        elif control_id == IDC_RESET_CAMERA:
            self.reset_camera()
        elif control_id == IDC_WEAPON_LIST:
            if notification == CBN_SELCHANGE:
                self.selected_weapon_index = self.get_combo_selection(IDC_WEAPON_LIST)
                self.update_title(force=True)
        else:
            return None
        return 0

    def handle_mouse_down(self, lparam, button):
        self.dragging = True
        self.drag_button = button
        self.drag_distance = 0
        self.last_mouse = (loword(lparam), hiword_signed(lparam))
        ctypes.windll.user32.SetCapture(self.hwnd)
        return 0

    def handle_mouse_up(self, button):
        was_click = self.drag_button == button and self.drag_distance < 4
        self.dragging = False
        self.drag_button = None
        ctypes.windll.user32.ReleaseCapture()
        if button == "right" and was_click:
            self.toggle_panel()
        return 0

    def handle_mouse_move(self, lparam):
        if not self.dragging:
            return None
        x = loword(lparam)
        y = hiword_signed(lparam)
        last_x, last_y = self.last_mouse
        self.last_mouse = (x, y)
        delta_x = x - last_x
        delta_y = y - last_y
        self.drag_distance += abs(delta_x) + abs(delta_y)
        if self.drag_button == "left":
            self.yaw += delta_x * 0.008
            self.pitch = max(-1.1, min(1.1, self.pitch + delta_y * 0.006))
        elif self.drag_button == "right":
            pan_scale = max(
                0.01,
                float(self.model_radius or self.radius or 1.0) *
                max(0.02, self.zoom) *
                0.0025,
            )
            right = (math.cos(self.yaw), 0.0, -math.sin(self.yaw))
            up = (
                -math.sin(self.yaw) * math.sin(self.pitch),
                math.cos(self.pitch),
                -math.cos(self.yaw) * math.sin(self.pitch),
            )
            for index in range(3):
                self.camera_pan[index] += (
                    (-delta_x * right[index]) +
                    (delta_y * up[index])
                ) * pan_scale
        self.update_camera()
        return 0

    def handle_mouse_wheel(self, wparam):
        delta = hiword_signed(wparam)
        self.zoom_by(0.84 if delta > 0 else 1.18)
        return 0

    def update_title(self, force=False):
        now = time.time()
        if not force and now - self.last_title_at < 0.45:
            return
        self.last_title_at = now
        mode = VISUAL_MODES[self.mode_index][0]
        filter_summary = (
            " | filter %s/%s" % (len(self.filtered_catalog_indices), len(self.catalog))
            if self.search_text
            else ""
        )
        title = (
            "Elysian Jessica Live | type %s | %.0f FPS | %s | zoom %.0f%% | light %.2fx%s | %s | "
            "left orbit, right pan, wheel zoom"
        ) % (
            self.type_id,
            self.fps,
            mode,
            self.zoom * 100.0,
            self.light_scale,
            filter_summary,
            "panel" if self.panel_visible else "clean",
        )
        set_title(self.hwnd, title)

    def poll_external_commands(self):
        if not self.command_path:
            return
        now = time.time()
        if now - self.last_command_poll_at < 0.08:
            return
        self.last_command_poll_at = now
        try:
            if not os.path.exists(self.command_path):
                return
            with open(self.command_path, "r") as handle:
                handle.seek(self.command_offset)
                lines = handle.readlines()
                self.command_offset = handle.tell()
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    self.handle_external_command(json.loads(line))
                except Exception:
                    print(traceback.format_exc(), file=sys.stderr)
        except Exception:
            print(traceback.format_exc(), file=sys.stderr)

    def handle_external_command(self, payload):
        command = str(payload.get("command") or "").lower()
        if command == "explode":
            self.play_explosion()
        elif command == "activate":
            self.activate_current_model()
        elif command == "arm":
            self.arm_max_turrets()
        elif command == "weapon":
            if self.select_weapon_by_text(payload.get("value") or ""):
                self.arm_max_turrets()
        elif command == "fire":
            value = payload.get("value")
            if isinstance(value, bool):
                if value:
                    self.start_dummy_fire()
                else:
                    self.stop_dummy_fire()
            else:
                self.toggle_dummy_fire()
        elif command == "clearweapons":
            self.clear_preview_weapons()
        elif command == "boosters":
            value = payload.get("value")
            if isinstance(value, bool):
                self.boosters_enabled = value
                self.apply_booster_state(rebuild=True)
                self.sync_control_text()
                self.update_title(force=True)
            else:
                self.toggle_boosters()
        elif command == "nebula":
            self.cycle_scene()
        elif command == "mode":
            requested = str(payload.get("value") or "").lower()
            if requested:
                self.mode_index = self.resolve_mode_index(requested)
                self.update_camera()
                self.sync_control_text()
                self.update_title(force=True)
            else:
                self.cycle_mode()
        elif command == "post":
            value = payload.get("value")
            if isinstance(value, bool):
                self.post_enabled = value
                self.apply_render_flags()
                self.sync_control_text()
                self.update_title(force=True)
            else:
                self.toggle_post()
        elif command == "after":
            value = payload.get("value")
            if isinstance(value, bool):
                self.after_effects_enabled = value
                self.apply_render_flags()
                self.sync_control_text()
                self.update_title(force=True)
            else:
                self.toggle_after_effects()
        elif command == "light":
            self.adjust_light(float(payload.get("delta") or 0.25))
        elif command == "quality":
            self.set_ultra_quality()
        elif command == "next":
            self.step_catalog(1)
        elif command == "prev":
            self.step_catalog(-1)
        elif command == "pause":
            self.paused = not self.paused
            self.update_title(force=True)
        elif command == "panel":
            value = payload.get("value")
            self.panel_visible = bool(value) if isinstance(value, bool) else not self.panel_visible
            self.apply_panel_visibility()
            self.update_title(force=True)
        elif command == "resetcamera":
            self.reset_camera()
        elif command == "animation":
            requested = native_text(payload.get("value") or "").lower()
            for index, option in enumerate(self.animation_options):
                if requested in native_text(option.get("label")).lower():
                    USER32.SendMessageA(
                        self.controls.get(IDC_ANIMATION_LIST),
                        CB_SETCURSEL,
                        index,
                        0,
                    )
                    self.play_selected_animation()
                    break

    def tick(self):
        now = time.time()
        self.poll_external_commands()
        self.poll_search_text()
        if not self.paused:
            self.yaw += 0.0026
        if self.firing_dummy and now >= self.next_dummy_fire_at:
            self.fire_preview_weapons_once()
            self.next_dummy_fire_at = now + self.weapon_cycle_seconds
        self.update_weapon_projectiles(now)
        if (
            self.explosion_ship_hide_at and
            now >= self.explosion_ship_hide_at and
            self.space_object is not None and
            hasattr(self.space_object, "display")
        ):
            self.space_object.display = False
            self.explosion_ship_hide_at = 0.0
        if self.explosion_models and self.explosion_until and now >= self.explosion_until:
            self.clear_explosions()
        self.scene.UpdateScene(self.blue.os.GetSimTime())
        self.update_camera()
        self.device.Render()
        self.blue.os.Pump()
        self.frame_count += 1
        self.fps_window_frames += 1
        elapsed = now - self.fps_window_at
        if elapsed >= 0.5:
            self.fps = float(self.fps_window_frames) / elapsed
            self.fps_window_frames = 0
            self.fps_window_at = now
        self.update_title()

    def run(self):
        self.create_window()
        self.create_panel_window()
        self.initialize_trinity()
        self.build_space_object()
        self.load_scene()
        self.create_render_job()
        self.update_camera()
        self.update_title(force=True)

        msg = MSG()
        p_msg = ctypes.pointer(msg)
        translate_message = ctypes.windll.user32.TranslateMessage
        dispatch_message = ctypes.windll.user32.DispatchMessageA
        peek_message = ctypes.windll.user32.PeekMessageA
        while self.running:
            while peek_message(p_msg, NULL, 0, 0, PM_REMOVE):
                if msg.message == WM_QUIT:
                    self.running = False
                    break
                translate_message(p_msg)
                dispatch_message(p_msg)
            if self.running:
                self.tick()
        return 0


viewer = None


def window_proc(hwnd, message, wparam, lparam):
    global viewer
    if viewer is None:
        return USER32.DefWindowProcA(hwnd, message, wparam, lparam)
    is_panel = viewer.panel_hwnd and hwnd == viewer.panel_hwnd
    is_main = viewer.hwnd and hwnd == viewer.hwnd
    if message == WM_CLOSE:
        if is_panel:
            viewer.panel_visible = False
            viewer.apply_panel_visibility()
            viewer.update_title(force=True)
            return 0
        viewer.running = False
        USER32.PostQuitMessage(0)
        return 0
    if message == WM_DESTROY:
        if is_panel:
            viewer.panel_hwnd = None
            return 0
        viewer.running = False
        USER32.PostQuitMessage(0)
        return 0
    if message == WM_ERASEBKGND:
        return 0 if is_main else USER32.DefWindowProcA(hwnd, message, wparam, lparam)
    if message == WM_SIZE:
        if is_panel:
            viewer.position_controls()
        else:
            viewer.resize()
        return 0
    if message == WM_COMMAND:
        handled = viewer.handle_command(wparam)
        if handled is not None:
            return handled
    if message == WM_KEYDOWN:
        handled = viewer.handle_key(wparam)
        if handled is not None:
            return handled
    if message == WM_LBUTTONDOWN:
        if is_main:
            return viewer.handle_mouse_down(lparam, "left")
    if message == WM_RBUTTONDOWN:
        if is_main:
            return viewer.handle_mouse_down(lparam, "right")
    if message == WM_LBUTTONUP:
        if is_main:
            return viewer.handle_mouse_up("left")
    if message == WM_RBUTTONUP:
        if is_main:
            return viewer.handle_mouse_up("right")
    if message == WM_MOUSEMOVE:
        if is_main:
            handled = viewer.handle_mouse_move(lparam)
            if handled is not None:
                return handled
    if message == WM_MOUSEWHEEL:
        if is_main:
            return viewer.handle_mouse_wheel(wparam)
    return USER32.DefWindowProcA(hwnd, message, wparam, lparam)


def main():
    global viewer
    if len(sys.argv) < 7:
        raise RuntimeError(
            "usage: trinity_live_viewer.py TYPE_ID DNA RADIUS WIDTH HEIGHT [MODE] [CATALOG_JSON] [COMMAND_JSONL]"
        )
    catalog_path = sys.argv[7] if len(sys.argv) > 7 and not sys.argv[7].startswith("/") else None
    command_path = sys.argv[8] if len(sys.argv) > 8 and not sys.argv[8].startswith("/") else None
    viewer = LiveTrinityViewer(
        int(sys.argv[1]),
        sys.argv[2],
        float(sys.argv[3]),
        int(sys.argv[4]),
        int(sys.argv[5]),
        sys.argv[6] if len(sys.argv) > 6 else "white",
        catalog_path,
        command_path,
    )
    return viewer.run()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        print(traceback.format_exc(), file=sys.stderr)
        raise
