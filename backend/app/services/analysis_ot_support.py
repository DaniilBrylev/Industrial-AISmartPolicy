"""
OT-специфика анализа: компенсирующие меры при отсутствии MFA/патчинга, расширенные списки мер.
Используется rule-based ядром; не заменяет классификацию целиком.
"""

from __future__ import annotations

import re
from typing import Any, Literal

Environment = Literal["IT", "OT"]

COMPENSATING_PREFIX = "(компенсирующая мера) "

_OT_PROTOCOL_RE = re.compile(
    r"\b(modbus|opc\s*ua?|profinet|profinet\b|dnp3|iec\s*61850|ethernet/ip|bacnet|"
    r"mqtt|hart|foundation\s*fieldbus|модбас|опс|профинет)\b",
    re.IGNORECASE,
)
_OT_ZONE_RE = re.compile(
    r"\b(ot|technolog|production|field|plant|цех|асутп|телеметр|prom|segment|vlan|"
    r"технологическ|производственн)\b",
    re.IGNORECASE,
)


def parse_bool_field(raw: Any) -> bool | None:
    """True/False/None(не задано)."""
    if raw is None:
        return None
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        s = raw.strip().lower()
        if s in ("true", "1", "yes", "да"):
            return True
        if s in ("false", "0", "no", "нет"):
            return False
    return None


def asset_extended_text(asset: dict[str, Any]) -> str:
    parts = [
        str(asset.get("name", "") or ""),
        str(asset.get("asset_type", "") or ""),
        str(asset.get("network_zone", "") or ""),
        str(asset.get("protocols", "") or ""),
        str(asset.get("vendor", "") or ""),
    ]
    return " ".join(parts)


def has_ot_protocol_hint(asset: dict[str, Any]) -> bool:
    return bool(_OT_PROTOCOL_RE.search(asset_extended_text(asset)))


def has_ot_zone_hint(asset: dict[str, Any]) -> bool:
    z = str(asset.get("network_zone", "") or "")
    return bool(z and _OT_ZONE_RE.search(z))


def is_safety_critical(asset: dict[str, Any]) -> bool:
    return parse_bool_field(asset.get("safety_critical")) is True


def supports_mfa(asset: dict[str, Any]) -> bool | None:
    return parse_bool_field(asset.get("supports_mfa"))


def supports_patching(asset: dict[str, Any]) -> bool | None:
    return parse_bool_field(asset.get("supports_patching"))


def asset_type_matches(asset: dict[str, Any], pattern: re.Pattern[str]) -> bool:
    t = f"{asset.get('asset_type', '')} {asset.get('name', '')}"
    return bool(pattern.search(t))


def is_plc_like(asset: dict[str, Any]) -> bool:
    return asset_type_matches(asset, _OT_TYPE_PLC)


def is_sensor_like(asset: dict[str, Any]) -> bool:
    return asset_type_matches(asset, _OT_TYPE_SENSOR)


def is_scada_hmi_like(asset: dict[str, Any]) -> bool:
    return asset_type_matches(asset, _OT_TYPE_SCADA_HMI)


def is_historian_like(asset: dict[str, Any]) -> bool:
    return asset_type_matches(asset, _OT_TYPE_HISTORIAN)


def is_ot_network_like(asset: dict[str, Any]) -> bool:
    return asset_type_matches(asset, _OT_TYPE_NETWORK)


def is_ot_gateway_like(asset: dict[str, Any]) -> bool:
    return asset_type_matches(asset, _OT_TYPE_GATEWAY)


def is_engineering_station_like(asset: dict[str, Any]) -> bool:
    return asset_type_matches(asset, _OT_TYPE_ENGINEERING)


_OT_TYPE_PLC = re.compile(
    r"\b(plc|плк|controller|контроллер|cpu\s*15|s7[- ]?|logix|schneider)\b",
    re.IGNORECASE,
)
_OT_TYPE_SENSOR = re.compile(
    r"\b(sensor|датчик|transmitter|field\s*device|telemetry\s*input|и\.\s*к\.\s*)\b",
    re.IGNORECASE,
)
_OT_TYPE_SCADA_HMI = re.compile(
    r"\b(scada|hmi|wincc|ignition|wonderware|ifx|operator|операторск)\b",
    re.IGNORECASE,
)
_OT_TYPE_HISTORIAN = re.compile(
    r"\b(historian|телеметр|archive\s*server|data\s*diode)\b",
    re.IGNORECASE,
)
_OT_TYPE_NETWORK = re.compile(
    r"\b(network|сегмент|vlan|технологическ\w*\s+сет|industrial\s*ethernet|"
    r"технологическ\w*\s+контур)\b",
    re.IGNORECASE,
)
_OT_TYPE_GATEWAY = re.compile(
    r"\b(gateway|шлюз|firewall\s*ot|промышленн\w*\s+шлюз)\b",
    re.IGNORECASE,
)
_OT_TYPE_ENGINEERING = re.compile(
    r"\b(engineering|инженерн|es\s*workstation|разработк\w*\s+станц)\b",
    re.IGNORECASE,
)


def response_suggests_remote_ot_access(response_data: dict[str, Any]) -> bool:
    """Подрядчики / матрица доступа намекают на удалённый доступ в OT."""
    remote_re = re.compile(
        r"\b(vpn|rdp|teamviewer|anydesk|удалён|удален|remote|jump|bastion|"
        r"интегратор|подрядчик)\b",
        re.IGNORECASE,
    )

    def scan_block(val: Any) -> bool:
        if isinstance(val, str):
            return bool(remote_re.search(val))
        if isinstance(val, list):
            for row in val:
                if isinstance(row, dict):
                    for v in row.values():
                        if isinstance(v, str) and remote_re.search(v):
                            return True
                elif isinstance(row, str) and remote_re.search(row):
                    return True
        return False

    if scan_block(response_data.get("contractors")):
        return True
    if scan_block(response_data.get("access_matrix")):
        return True
    if scan_block(response_data.get("incidents")):
        return True
    return False


def questionnaire_has_both_environments(classified_envs: list[str]) -> bool:
    return "IT" in classified_envs and "OT" in classified_envs


def measures_for_requirement_key(
    req_key: str,
    *,
    environment: Environment,
    asset: dict[str, Any],
) -> list[str]:
    """
    Подбор мер с учётом IT/OT и ограничений актива (MFA, патчинг).
    Компенсирующие меры помечаются префиксом COMPENSATING_PREFIX.
    """
    smfa = supports_mfa(asset)
    spatch = supports_patching(asset)
    ot_no_mfa = environment == "OT" and smfa is False
    ot_no_patch = environment == "OT" and spatch is False

    # --- Доступ ---
    if req_key == "REQ_ACCESS_CONTROL":
        if environment == "IT":
            base = [
                "RBAC / принцип наименьших привилегий",
                "Многофакторная аутентификация для критичных систем",
            ]
            return base
        out = [
            "RBAC и разграничение ролей в OT (оператор / инженер / администратор)",
            "Физический контроль доступа к шкафам автоматики и панелям оператора",
        ]
        if ot_no_mfa:
            out.append(
                f"{COMPENSATING_PREFIX}Сегментация и jump host / bastion для удалённого доступа "
                "(MFA на bastion, не на ПЛК)"
            )
            out.append(
                f"{COMPENSATING_PREFIX}Ограничение времени и IP для сеансов подрядчиков"
            )
        else:
            out.append(
                "Многофакторная аутентификация на jump host / bastion при удалённом доступе в OT"
            )
        return out

    # --- Журналы ---
    if req_key == "REQ_LOGGING":
        if environment == "OT":
            return [
                "Централизованный сбор журналов с ПЛК, SCADA и сетевого оборудования OT",
                "Корреляция событий с промышленными протоколами (Modbus/OPC/Profinet и др.)",
            ]
        return [
            "Централизованный сбор и хранение журналов",
            "Корреляция событий безопасности",
        ]

    # --- Данные ---
    if req_key == "REQ_DATA_PROTECTION":
        if environment == "OT":
            return [
                "Классификация технологических данных и ограничение экспорта за контур OT",
                "Шифрование каналов администрирования (VPN, защищённые сессии к jump host)",
            ]
        return [
            "Классификация данных и шифрование",
            "DLP-контроль каналов утечки",
        ]

    # --- ИТ доступность ---
    if req_key == "REQ_AVAILABILITY":
        return [
            "Резервирование критичных компонентов",
            "Регламенты восстановления (RTO/RPO)",
        ]

    # --- Мониторинг ---
    if req_key == "REQ_MONITORING":
        if environment == "OT":
            return [
                "Непрерывный мониторинг OT-сегмента и промышленных протоколов",
                "Оповещение о аномалиях уставок и сессий инженерного доступа",
            ]
        return [
            "Непрерывный мониторинг состояния и событий",
            "Оповещение ответственных лиц",
        ]

    # --- OT доступность процессов ---
    if req_key == "REQ_OT_AVAILABILITY":
        out = [
            "Резервирование критичных узлов SCADA / связи с ПЛК",
            "Регламенты аварийного переключения и восстановления технологического контура",
        ]
        if is_safety_critical(asset):
            out.append(
                "Проектирование отказоустойчивости с переводом процесса в безопасное состояние"
            )
        return out

    # --- Целостность OT ---
    if req_key == "REQ_OT_INTEGRITY":
        out = [
            "Контроль изменений конфигураций контроллеров и логики (версионирование, согласование)",
            "Проверка целостности проектов ПЛК/SCADA перед загрузкой в оборудование",
        ]
        if ot_no_patch:
            out.append(
                f"{COMPENSATING_PREFIX}Изоляция устройств без регулярного патчинга "
                "(сегментация, ACL, отключение ненужных сервисов)"
            )
            out.append(
                f"{COMPENSATING_PREFIX}Усиленный мониторинг и контроль физического доступа "
                "вместо классического patch-management"
            )
        return out

    # --- Сегментация IT/OT ---
    if req_key == "REQ_OT_SEGMENTATION":
        return [
            "Сегментация IT и OT (DMZ, межсетевые экраны, однонаправленные шлюзы при необходимости)",
            "Запрет прямого доступа из корпоративной сети к ПЛК; только через bastion",
        ]

    # --- Удалённый доступ подрядчиков ---
    if req_key == "REQ_OT_REMOTE_ACCESS":
        out = [
            "Jump host / bastion для удалённой поддержки OT",
            "Регистрация и аудит сеансов подрядчиков, принцип наименьших привилегий",
        ]
        if ot_no_mfa:
            out.append(
                f"{COMPENSATING_PREFIX}Жёсткая привязка удалённого доступа к календарю работ "
                "и двухфакторная проверка на шлюзе доступа"
            )
        return out

    # --- Безопасное состояние ---
    if req_key == "REQ_OT_SAFE_STATE":
        return [
            "Процедуры перевода установки в безопасное состояние при сбоях АСУ ТП",
            "Резервирование сигналов безопасности и контроль их приоритета над управлением",
        ]

    # --- Компенсирующий «зонтичный» ключ ---
    if req_key == "REQ_OT_COMPENSATING":
        items = [
            f"{COMPENSATING_PREFIX}Комплексный контроль: сеть, физический доступ, изменения конфигураций",
        ]
        if ot_no_patch:
            items.append(
                f"{COMPENSATING_PREFIX}Периодический осмотр и инвентаризация legacy-узлов без ОС-патчинга"
            )
        return items

    # --- Контроль изменений конфигураций ---
    if req_key == "REQ_OT_CHANGE_CONTROL":
        out = [
            "Версионирование проектов ПЛК/SCADA и согласование изменений",
            "Резервное копирование логики и регламент отката конфигурации",
        ]
        if ot_no_patch:
            out.append(
                f"{COMPENSATING_PREFIX}Периодическая верификация прошивок и логики без онлайн-обновления"
            )
        return out

    # Fallback (неизвестный ключ)
    return []


def is_compensating_measure(measure_title: str) -> bool:
    return (measure_title or "").strip().startswith(COMPENSATING_PREFIX.strip())


def ot_constraints_summary(asset: dict[str, Any]) -> str | None:
    """Краткое rule-based описание ограничений OT-актива для traceability."""
    parts: list[str] = []
    smfa = supports_mfa(asset)
    if smfa is False:
        parts.append("MFA на устройстве не поддерживается")
    elif smfa is True:
        parts.append("MFA поддерживается")
    sp = supports_patching(asset)
    if sp is False:
        parts.append("регулярный патчинг недоступен или не применим")
    elif sp is True:
        parts.append("патчинг применим")
    if is_safety_critical(asset):
        parts.append("safety-critical")
    if not parts:
        return None
    return "; ".join(parts)
