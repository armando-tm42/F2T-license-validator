"""Modern styling and QSS theme for the License Manager application."""

MODERN_STYLE = """
/* Global Window & Fonts */
QWidget {
    font-family: 'Segoe UI', 'SF Pro Text', -apple-system, Arial, sans-serif;
    font-size: 13px;
    color: #1e293b;
    background-color: #f8fafc;
}

QMainWindow {
    background-color: #f1f5f9;
}

/* Header & Cards */
QFrame#HeaderCard {
    background-color: #ffffff;
    border-radius: 10px;
    border: 1px solid #e2e8f0;
    padding: 12px;
}

QFrame#StatCard {
    background-color: #ffffff;
    border-radius: 8px;
    border: 1px solid #e2e8f0;
    padding: 10px;
}

QFrame#StatCard:hover {
    border: 1px solid #cbd5e1;
}

QLabel#StatTitle {
    color: #64748b;
    font-size: 12px;
    font-weight: 500;
}

QLabel#StatValue {
    color: #0f172a;
    font-size: 22px;
    font-weight: 700;
}

QLabel#HeaderTitle {
    color: #0f172a;
    font-size: 20px;
    font-weight: 700;
}

QLabel#HeaderSubtitle {
    color: #64748b;
    font-size: 13px;
}

/* Push Buttons */
QPushButton {
    background-color: #ffffff;
    color: #1e293b;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #f1f5f9;
    border-color: #94a3b8;
}

QPushButton:pressed {
    background-color: #e2e8f0;
}

QPushButton:disabled {
    background-color: #f8fafc;
    color: #94a3b8;
    border-color: #e2e8f0;
}

QPushButton#PrimaryButton {
    background-color: #2563eb;
    color: #ffffff;
    border: 1px solid #1d4ed8;
}

QPushButton#PrimaryButton:hover {
    background-color: #1d4ed8;
}

QPushButton#PrimaryButton:pressed {
    background-color: #1e40af;
}

QPushButton#SuccessButton {
    background-color: #10b981;
    color: #ffffff;
    border: 1px solid #059669;
}

QPushButton#SuccessButton:hover {
    background-color: #059669;
}

QPushButton#DangerButton {
    background-color: #ef4444;
    color: #ffffff;
    border: 1px solid #dc2626;
}

QPushButton#DangerButton:hover {
    background-color: #dc2626;
}

/* Inputs & Form Controls */
QLineEdit, QComboBox, QDateEdit, QSpinBox {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 10px;
    color: #1e293b;
    selection-background-color: #2563eb;
}

QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus {
    border: 1px solid #2563eb;
    background-color: #ffffff;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #e2e8f0;
}

QTextEdit, QPlainTextEdit {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 8px;
    color: #1e293b;
}

/* Table View */
QTableWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    gridline-color: #f1f5f9;
    selection-background-color: #e0e7ff;
    selection-color: #1e1b4b;
}

QTableWidget::item {
    padding: 6px 10px;
    border-bottom: 1px solid #f1f5f9;
}

QTableWidget::item:selected {
    background-color: #e0e7ff;
    color: #1e1b4b;
}

QHeaderView::section {
    background-color: #f8fafc;
    color: #475569;
    padding: 8px 10px;
    font-weight: 600;
    border: none;
    border-bottom: 2px solid #e2e8f0;
}

/* Status Badges */
.badge-active {
    background-color: #dcfce7;
    color: #15803d;
    font-weight: 600;
    border-radius: 4px;
    padding: 3px 8px;
}

.badge-expiring {
    background-color: #fef3c7;
    color: #b45309;
    font-weight: 600;
    border-radius: 4px;
    padding: 3px 8px;
}

.badge-expired {
    background-color: #fee2e2;
    color: #b91c1c;
    font-weight: 600;
    border-radius: 4px;
    padding: 3px 8px;
}

/* Scrollbars */
QScrollBar:vertical {
    background: #f1f5f9;
    width: 10px;
    margin: 0px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background: #cbd5e1;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #94a3b8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Tooltips */
QToolTip {
    background-color: #1e293b;
    color: #ffffff;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 5px 8px;
    font-size: 12px;
}
"""


def get_status_badge_html(status: str, days: int) -> str:
    """Returns an HTML formatted badge for table/detail views."""
    if status == "Activa":
        return f'<span style="background-color: #dcfce7; color: #15803d; font-weight: 600; padding: 2px 8px; border-radius: 4px;">● Activa ({days}d)</span>'
    elif status == "Por expirar":
        return f'<span style="background-color: #fef3c7; color: #b45309; font-weight: 600; padding: 2px 8px; border-radius: 4px;">▲ Expirando ({days}d)</span>'
    else:
        return f'<span style="background-color: #fee2e2; color: #b91c1c; font-weight: 600; padding: 2px 8px; border-radius: 4px;">✕ Expirada</span>'
