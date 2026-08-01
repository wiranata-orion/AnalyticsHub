"""Utilitas bersama untuk seluruh modul engine.

Berisi hal-hal yang dibutuhkan setiap modul tetapi bukan bagian dari analisis:
membentuk balasan, dan yang paling penting membersihkan nilai yang tidak sah
dalam JSON.

NaN, Infinity, dan tipe numpy adalah hasil yang lumrah dari pandas/sklearn,
tetapi ketiganya bukan JSON yang valid — `json.dumps` akan menghasilkan token
`NaN` yang membuat `json_decode` di PHP mengembalikan null tanpa pesan apa pun.
Karena itu setiap hasil wajib melewati `clean()` sebelum dikirim.
"""

from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd


def clean(value: Any) -> Any:
    """Ubah nilai apa pun menjadi bentuk yang aman untuk JSON."""
    if value is None:
        return None

    # Tipe numpy tidak dikenali json.dumps; diturunkan ke tipe Python dulu.
    if isinstance(value, (np.integer,)):
        return int(value)

    if isinstance(value, (np.floating,)):
        value = float(value)

    if isinstance(value, (np.bool_,)):
        return bool(value)

    if isinstance(value, float):
        # NaN dan tak hingga menjadi null: keduanya berarti "tidak ada nilai"
        # bagi pembacanya, dan itu yang paling jujur untuk ditampilkan.
        return None if (math.isnan(value) or math.isinf(value)) else value

    if isinstance(value, (np.ndarray,)):
        return [clean(item) for item in value.tolist()]

    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()

    if isinstance(value, pd.Series):
        return [clean(item) for item in value.tolist()]

    if isinstance(value, dict):
        return {str(key): clean(item) for key, item in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [clean(item) for item in value]

    if value is pd.NaT:
        return None

    if isinstance(value, (str, int, bool)):
        return value

    # Sisanya (objek sklearn, tipe tak terduga) dijadikan teks agar hasil tetap
    # terkirim alih-alih seluruh permintaan gagal karena satu nilai.
    return str(value)


def ok(data: Any) -> dict:
    return {"ok": True, "data": clean(data)}


def fail(message: str) -> dict:
    return {"ok": False, "error": message}


class EngineError(Exception):
    """Kesalahan yang pesannya memang ditujukan untuk pengguna aplikasi."""


def require(params: dict, *names: str) -> tuple:
    """Ambil parameter wajib; menaikkan EngineError bila ada yang kosong."""
    missing = [name for name in names if params.get(name) in (None, "", [])]

    if missing:
        raise EngineError("Parameter wajib belum diisi: " + ", ".join(missing))

    return tuple(params[name] for name in names)
