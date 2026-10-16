import os
import sys
from pathlib import Path
from typing import Dict, Optional

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import (
    QIcon,
    QPixmap,
    QPainter,
    QPen,
    QBrush,
    QColor,
    QPainterPath,
    QPolygonF,
)


def _resolve_assets_dir() -> Path:
    # Soporte para ejecutables congelados con PyInstaller (onefile / onedir)
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        meipass = Path(sys._MEIPASS)
        for cand in [
            meipass / "license_validator" / "gui" / "assets",
            meipass / "gui" / "assets",
            meipass / "assets",
        ]:
            if cand.is_dir():
                return cand
    return Path(__file__).resolve().parent / "assets"


ASSETS_DIR = _resolve_assets_dir()
_icon_cache: Dict[str, QIcon] = {}


def get_icon(name: str, color: Optional[str] = None, size: int = 24) -> QIcon:
    """
    Returns a crisp QIcon by name ('plus', 'minus', 'save', 'copy', 'key', 'lock', 'edit', 'verify').
    Uses SVG file if available and valid; otherwise renders a high-quality vector fallback via QPainter.
    """
    cache_key = f"{name}_{color}_{size}"
    if cache_key in _icon_cache:
        return _icon_cache[cache_key]

    svg_path = ASSETS_DIR / f"{name}.svg"
    icon = QIcon()

    # If color is specified, we can generate a tinted SVG or use the QPainter vector renderer
    if color is None and svg_path.is_file():
        icon = QIcon(str(svg_path))

    # If icon is null (e.g., QtSvg plugin not installed or colored icon requested)
    if icon.isNull() or color is not None:
        pixmap = render_vector_pixmap(name, color=color or "#475569", size=size)
        icon = QIcon(pixmap)

    _icon_cache[cache_key] = icon
    return icon


def get_app_icon() -> QIcon:
    """
    Searches and returns the application main icon if present in gui/assets or project root.
    Supports .ico, .png, .svg, and .jpg formats under names like app_icon, icon, or logo.
    """
    candidates = [
        ASSETS_DIR / "app_icon.ico",
        ASSETS_DIR / "app_icon.png",
        ASSETS_DIR / "logo.png",
        ASSETS_DIR / "icon.png",
        ASSETS_DIR / "app_icon.svg",
        ASSETS_DIR / "app_icon.jpg",
        Path("app_icon.ico"),
        Path("app_icon.png"),
        Path("logo.png"),
        Path("icon.png"),
    ]
    for path in candidates:
        if path.is_file():
            icon = QIcon(str(path))
            if not icon.isNull() and not icon.pixmap(32, 32).isNull():
                return icon
            # Secondary check: if it's an .ico file, load via PIL to extract PNG pixmap
            try:
                from PIL import Image
                import io
                with Image.open(str(path)) as img:
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    pix = QPixmap()
                    pix.loadFromData(buf.getvalue(), "PNG")
                    if not pix.isNull():
                        return QIcon(pix)
            except Exception:
                pass

    # Fallback to shield icon
    return get_icon("verify", color="#2563eb", size=64)



def render_vector_pixmap(name: str, color: str = "#475569", size: int = 24) -> QPixmap:
    """Renders a vector icon using QPainter directly onto a QPixmap with antialiasing."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    qcolor = QColor(color)
    pen = QPen(qcolor, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)

    s = size / 24.0  # Scale factor relative to 24x24 viewBox

    if name == "plus":
        # Signo de más (+)
        pen.setWidthF(2.6 * s)
        painter.setPen(pen)
        painter.drawLine(QPointF(12 * s, 5 * s), QPointF(12 * s, 19 * s))
        painter.drawLine(QPointF(5 * s, 12 * s), QPointF(19 * s, 12 * s))

    elif name == "minus":
        # Signo de menos (-)
        pen.setWidthF(2.6 * s)
        painter.setPen(pen)
        painter.drawLine(QPointF(5 * s, 12 * s), QPointF(19 * s, 12 * s))

    elif name == "save":
        # Rectángulo con puntas / disquete
        pen.setWidthF(1.8 * s)
        painter.setPen(pen)
        # Outer body with cut corner at top-right
        path = QPainterPath()
        path.moveTo(4.5 * s, 20 * s)
        path.lineTo(4.5 * s, 5.5 * s)
        path.lineTo(16 * s, 5.5 * s)
        path.lineTo(19.5 * s, 9 * s)
        path.lineTo(19.5 * s, 20 * s)
        path.closeSubpath()
        painter.drawPath(path)

        # Top shutter
        painter.drawRect(QRectF(7.5 * s, 5.5 * s, 7 * s, 4.5 * s))
        # Bottom label
        painter.drawRect(QRectF(7.5 * s, 13 * s, 9 * s, 7 * s))

    elif name == "copy":
        # Hoja de papel con esquina doblada
        pen.setWidthF(1.8 * s)
        painter.setPen(pen)

        path = QPainterPath()
        path.moveTo(5.5 * s, 20.5 * s)
        path.lineTo(5.5 * s, 4 * s)
        path.lineTo(13.5 * s, 4 * s)
        path.lineTo(18.5 * s, 9 * s)
        path.lineTo(18.5 * s, 20.5 * s)
        path.closeSubpath()
        painter.drawPath(path)

        # Flap de la esquina doblada
        fold = QPainterPath()
        fold.moveTo(13.5 * s, 4 * s)
        fold.lineTo(13.5 * s, 9 * s)
        fold.lineTo(18.5 * s, 9 * s)
        painter.drawPath(fold)

        # Líneas de contenido en la hoja
        painter.drawLine(QPointF(8.5 * s, 13 * s), QPointF(15.5 * s, 13 * s))
        painter.drawLine(QPointF(8.5 * s, 16.5 * s), QPointF(13.5 * s, 16.5 * s))

    elif name in ("key", "lock"):
        # Llave o Candado
        pen.setWidthF(1.8 * s)
        painter.setPen(pen)

        # Dibujo de Candado
        # Cuerpo
        body_rect = QRectF(4.5 * s, 10.5 * s, 15 * s, 10 * s)
        painter.drawRoundedRect(body_rect, 2.5 * s, 2.5 * s)

        # Arco superior
        shackle = QPainterPath()
        shackle.moveTo(7.5 * s, 10.5 * s)
        shackle.lineTo(7.5 * s, 7 * s)
        shackle.arcTo(QRectF(7.5 * s, 3.5 * s, 9 * s, 7 * s), 180, -180)
        shackle.lineTo(16.5 * s, 10.5 * s)
        painter.drawPath(shackle)

        # Ojo de la cerradura
        painter.setBrush(QBrush(qcolor))
        painter.drawEllipse(QPointF(12 * s, 14.5 * s), 1.5 * s, 1.5 * s)
        painter.drawLine(QPointF(12 * s, 15 * s), QPointF(12 * s, 17.5 * s))

    elif name == "edit":
        # Lápiz de edición
        pen.setWidthF(1.8 * s)
        painter.setPen(pen)
        # Pad / box
        painter.drawRoundedRect(QRectF(4 * s, 5 * s, 11 * s, 14 * s), 1.5 * s, 1.5 * s)
        # Pencil angled
        painter.drawLine(QPointF(11 * s, 17 * s), QPointF(19 * s, 9 * s))
        painter.drawLine(QPointF(19 * s, 9 * s), QPointF(20 * s, 6 * s))
        painter.drawLine(QPointF(20 * s, 6 * s), QPointF(17 * s, 5 * s))
        painter.drawLine(QPointF(17 * s, 5 * s), QPointF(9 * s, 13 * s))
        painter.drawLine(QPointF(9 * s, 13 * s), QPointF(8.5 * s, 17.5 * s))
        painter.drawLine(QPointF(8.5 * s, 17.5 * s), QPointF(11 * s, 17 * s))

    elif name == "verify":
        # Escudo de verificación con check
        pen.setWidthF(1.8 * s)
        painter.setPen(pen)
        shield = QPainterPath()
        shield.moveTo(12 * s, 3 * s)
        shield.lineTo(19 * s, 5.5 * s)
        shield.lineTo(19 * s, 12 * s)
        shield.quadTo(19 * s, 18 * s, 12 * s, 21 * s)
        shield.quadTo(5 * s, 18 * s, 5 * s, 12 * s)
        shield.lineTo(5 * s, 5.5 * s)
        shield.closeSubpath()
        painter.drawPath(shield)

        # Checkmark
        check = QPainterPath()
        check.moveTo(9 * s, 12 * s)
        check.lineTo(11 * s, 14.5 * s)
        check.lineTo(15.5 * s, 9.5 * s)
        painter.drawPath(check)

    elif name == "search":
        # Lupa de búsqueda
        pen.setWidthF(2.0 * s)
        painter.setPen(pen)
        # Aro de la lupa
        painter.drawEllipse(QPointF(10.5 * s, 10.5 * s), 5.5 * s, 5.5 * s)
        # Mango de la lupa
        painter.drawLine(QPointF(14.5 * s, 14.5 * s), QPointF(20.0 * s, 20.0 * s))

    elif name == "refresh":
        # Flechas circulares de refrescar
        pen.setWidthF(1.8 * s)
        painter.setPen(pen)
        painter.drawArc(QRectF(5 * s, 5 * s, 14 * s, 14 * s), 45 * 16, 270 * 16)
        painter.drawLine(QPointF(12 * s, 3 * s), QPointF(15 * s, 5 * s))
        painter.drawLine(QPointF(15 * s, 5 * s), QPointF(12 * s, 8 * s))

    elif name in ("user", "users"):
        # Silueta de usuario
        pen.setWidthF(1.8 * s)
        painter.setPen(pen)
        # Cabeza
        painter.drawEllipse(QPointF(12 * s, 8 * s), 3.5 * s, 3.5 * s)
        # Hombros
        body = QPainterPath()
        body.moveTo(5.5 * s, 20.5 * s)
        body.quadTo(5.5 * s, 15 * s, 12 * s, 15 * s)
        body.quadTo(18.5 * s, 15 * s, 18.5 * s, 20.5 * s)
        painter.drawPath(body)

    elif name == "logout":
        # Puerta con flecha de salir
        pen.setWidthF(1.8 * s)
        painter.setPen(pen)
        door = QPainterPath()
        door.moveTo(9 * s, 20 * s)
        door.lineTo(5 * s, 20 * s)
        door.lineTo(5 * s, 4 * s)
        door.lineTo(9 * s, 4 * s)
        painter.drawPath(door)
        # Flecha salir
        painter.drawLine(QPointF(9 * s, 12 * s), QPointF(19 * s, 12 * s))
        painter.drawLine(QPointF(15 * s, 8 * s), QPointF(19 * s, 12 * s))
        painter.drawLine(QPointF(15 * s, 16 * s), QPointF(19 * s, 12 * s))

    else:
        # Fallback circle
        painter.drawEllipse(QRectF(4 * s, 4 * s, 16 * s, 16 * s))

    painter.end()
    return pixmap
