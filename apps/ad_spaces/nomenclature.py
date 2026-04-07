"""
Nomenclatura fase 1 para códigos de toma: {código_centro}-T{número}[sufijo_letras].
Ejemplos: SCC-T1, SCC-T2, SLC-T1A, SLC-T1B.
"""

from __future__ import annotations

import re

from django.core.exceptions import ValidationError


def normalize_toma_code(code: str) -> str:
    return (code or "").strip().upper()


def validate_toma_code_for_center(code: str, shopping_center_code: str) -> str:
    """
    Devuelve el código normalizado (mayúsculas) o lanza ValidationError.
    El prefijo debe coincidir exactamente con el código del centro comercial.
    """
    normalized = normalize_toma_code(code)
    cc = normalize_toma_code(shopping_center_code)
    if not cc:
        raise ValidationError("El centro comercial no tiene un código válido.")
    if not normalized:
        raise ValidationError("Indica el código de la toma.")
    pattern = re.compile(r"^" + re.escape(cc) + r"-T(\d+)([A-Z]*)$")
    if not pattern.fullmatch(normalized):
        raise ValidationError(
            "El código debe seguir «%(cc)s-T» más un número y, si aplica, letras "
            "(ej. %(ex1)s o %(ex2)s).",
            params={"cc": cc, "ex1": f"{cc}-T1", "ex2": f"{cc}-T1A"},
        )
    return normalized
