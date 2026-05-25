from __future__ import annotations


def build_nav_options(role: str) -> list[str]:
    if role == "user":
        return ["dashboard", "profile", "upload", "ads"]
    if role == "analyst":
        return ["dashboard", "profile", "analytics", "reports", "upload"]
    if role == "admin":
        return ["dashboard", "analytics", "upload", "user_management", "admin"]
    return ["dashboard", "profile"]


def nav_label(key: str) -> str:
    icons = {
        "dashboard": "🏠",
        "profile": "👤",
        "ads": "📊",
        "analytics": "📈",
        "reports": "🧾",
        "upload": "📁",
        "user_management": "👥",
        "admin": "🛡️",
    }
    labels = {
        "dashboard": "Bảng điều khiển",
        "profile": "Hồ sơ",
        "ads": "Dữ liệu quảng cáo",
        "analytics": "Phân tích",
        "reports": "Báo cáo",
        "upload": "Quản lý dữ liệu",
        "user_management": "Quản lý người dùng",
        "admin": "Phiên đăng nhập",
    }
    return f"{icons.get(key, '')} {labels.get(key, key)}"