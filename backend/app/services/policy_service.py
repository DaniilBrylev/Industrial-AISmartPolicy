"""
Генерация текста политики ИБ из анкеты и analysis_result (rules + AI).

CRUD сущностей PolicyDocument см. policy_document_service.
"""

from __future__ import annotations

import copy
import html
import json
import logging
import re
from pathlib import Path
from typing import Any

from app.core.config import Settings, settings as default_settings
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)

_BULLET_LINE = re.compile(r"^\s*[-*•]\s+(.+)$")

# Ответы LLM, которые нельзя подставлять вместо фактических данных из analysis_result
_INSUFFICIENT_RE = re.compile(
    r"^\s*«?\s*недостаточно\s+данных\s*»?\s*\.?\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _line_without_bullet_prefix(ln: str) -> str:
    s = ln.strip()
    m = _BULLET_LINE.match(s)
    if m:
        return m.group(1).strip()
    if re.match(r"^\d+[\.)]\s+", s):
        return re.sub(r"^\d+[\.)]\s+", "", s).strip()
    return s


def _is_insufficient_llm_response(text: str) -> bool:
    """True, если модель вернула только шаблонную отбивку без содержания."""
    if not (text or "").strip():
        return True
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        return True
    for ln in lines:
        core = _line_without_bullet_prefix(ln)
        if not core:
            continue
        if _INSUFFICIENT_RE.match(core) is None:
            return False
    return True


def _list_len(val: Any) -> int:
    return len(val) if isinstance(val, list) else 0


def normalize_analysis_result(raw: Any) -> dict[str, Any]:
    """
    Приводит значение response_data['analysis_result'] к плоскому dict для генерации политики.

    Поддерживает:
    - JSON-строку вместо объекта;
    - вложенный объект report (как в QuestionnaireAnalyzeResponse: {\"report\": {...}});
    - опционально camelCase classifiedAssets → classified_assets.
    """
    if raw is None:
        return {}
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return {}
        try:
            raw = json.loads(s)
        except json.JSONDecodeError:
            logger.warning("analysis_result: не удалось разобрать JSON-строку")
            return {}
    if not isinstance(raw, dict):
        return {}

    base = copy.deepcopy(raw)
    rep = base.get("report")
    if isinstance(rep, dict):
        for k in (
            "assets",
            "classified_assets",
            "risks",
            "requirements",
            "measures",
            "links",
            "warnings",
        ):
            if k in rep:
                base[k] = rep[k]

    if "classified_assets" not in base and isinstance(base.get("classifiedAssets"), list):
        base["classified_assets"] = base["classifiedAssets"]

    logger.info(
        "normalize_analysis_result: len(assets)=%s len(classified_assets)=%s len(risks)=%s "
        "len(requirements)=%s len(measures)=%s",
        _list_len(base.get("assets")),
        _list_len(base.get("classified_assets")),
        _list_len(base.get("risks")),
        _list_len(base.get("requirements")),
        _list_len(base.get("measures")),
    )
    return base


def transform_analysis_to_policy_sections(
    normalized_analysis: dict[str, Any],
    policy_svc: PolicyService | None = None,
) -> dict[str, list[str]]:
    """
    Плоские списки строк для разделов политики (вход — результат normalize_analysis_result).

    Маппинг: assets, classified_assets → classification, risks, requirements, measures.
    """
    svc = policy_svc or PolicyService()
    return {
        "assets": svc._lines_from_report_list(normalized_analysis.get("assets"), "asset"),
        "classification": svc._lines_classified(normalized_analysis.get("classified_assets")),
        "risks": svc._lines_from_report_list(normalized_analysis.get("risks"), "risk"),
        "requirements": svc._string_list(normalized_analysis.get("requirements")),
        "measures": svc._string_list(normalized_analysis.get("measures")),
    }


class PolicyService:
    """Сборка структуры политики, вызов AI по разделам, HTML и DOCX."""

    def __init__(self, app_settings: Settings | None = None) -> None:
        self._settings = app_settings or default_settings
        raw = getattr(self._settings, "policy_export_dir", "var/generated_policies")
        self._export_dir = Path(raw)

    def docx_filename(self, questionnaire_id: int) -> str:
        return f"policy_q{questionnaire_id}.docx"

    def docx_path(self, questionnaire_id: int) -> Path:
        return self._export_dir / self.docx_filename(questionnaire_id)

    def build_policy_structure(
        self, response_data: dict[str, Any], analysis_result: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Собирает черновую структуру до вызова LLM.
        Списки — краткие строки; general/scope/conclusion — текстовые наброски.
        """
        dp = response_data.get("department_profile")
        if not isinstance(dp, dict):
            dp = {}

        notes = response_data.get("additional_notes")
        notes_str = notes if isinstance(notes, str) else ""

        general = (
            f"Подразделение: описание — {dp.get('description', '')}; "
            f"руководитель — {dp.get('manager_name', '')}; "
            f"контакты — {dp.get('contact_info', '')}."
        ).strip()

        scope = (
            "Область действия политики формируется на основе учтённых активов, "
            "бизнес-процессов и заявленного контекста организации. "
            f"Дополнительные сведения: {notes_str or 'не указаны'}."
        )

        analysis_norm = normalize_analysis_result(analysis_result)
        sections = transform_analysis_to_policy_sections(analysis_norm, self)
        assets_lines = list(sections["assets"])
        class_lines = list(sections["classification"])
        risk_lines = list(sections["risks"])
        req_lines = list(sections["requirements"])
        meas_lines = list(sections["measures"])

        if not assets_lines and isinstance(response_data.get("assets"), list):
            assets_lines = self._lines_from_raw_assets(response_data["assets"])

        conclusion = (
            "Политика носит рамочный характер; конкретные регламенты и сроки внедрения "
            "определяются локальными актами на основе результатов анализа рисков."
        )

        def _or_missing(lines: list[str]) -> list[str]:
            return lines if lines else ["данные отсутствуют"]

        return {
            "general": general,
            "scope": scope,
            "assets": _or_missing(assets_lines),
            "classification": _or_missing(class_lines),
            "risks": _or_missing(risk_lines),
            "requirements": _or_missing(req_lines),
            "measures": _or_missing(meas_lines),
            "conclusion": conclusion,
        }

    def _string_list(self, val: Any) -> list[str]:
        if isinstance(val, list):
            return [str(x).strip() for x in val if str(x).strip()]
        return []

    def _lines_from_report_list(self, val: Any, kind: str) -> list[str]:
        if not isinstance(val, list):
            return []
        out: list[str] = []
        for i, item in enumerate(val):
            if isinstance(item, dict):
                if kind == "asset":
                    out.append(
                        f"{item.get('id', i)}: {item.get('name', '')} "
                        f"({item.get('asset_type', '')}), критичность {item.get('criticality', '')}"
                    )
                elif kind == "risk":
                    out.append(
                        f"{item.get('risk_code', '')} — {item.get('title', '')} "
                        f"(актив {item.get('asset_id', '')}, severity {item.get('severity', '')})"
                    )
                else:
                    out.append(json.dumps(item, ensure_ascii=False))
            else:
                out.append(str(item))
        return out

    def _lines_classified(self, val: Any) -> list[str]:
        if not isinstance(val, list):
            return []
        lines: list[str] = []
        for item in val:
            if not isinstance(item, dict):
                lines.append(str(item))
                continue
            aid = item.get("asset_id", "")
            lines.append(
                f"{aid}: среда {item.get('environment', '')}, "
                f"критичность исх. {item.get('original_criticality', '')} → "
                f"эфф. {item.get('effective_criticality', '')}, "
                f"процессов: {item.get('usage_count', 0)}"
            )
        return lines

    def _lines_from_raw_assets(self, assets: list[Any]) -> list[str]:
        lines: list[str] = []
        for a in assets:
            if not isinstance(a, dict):
                continue
            lines.append(
                f"{a.get('id')}: {a.get('name', '')} ({a.get('asset_type', '')}) "
                f"— {a.get('criticality', '')}"
            )
        return lines

    async def generate_policy_text(
        self, structure: dict[str, Any], ai_service: AIService
    ) -> dict[str, Any]:
        """
        Для каждого логического раздела вызывает AIService.generate_policy_section.
        При сбое AI для раздела — fallback на исходные черновики из structure.
        """
        out: dict[str, Any] = {}

        text_keys = ("general", "scope", "conclusion")
        list_keys = ("assets", "classification", "risks", "requirements", "measures")

        for key in text_keys:
            draft = str(structure.get(key, "") or "")
            payload = {
                "section": key,
                "draft": draft,
                "full_context": structure,
            }
            try:
                generated = await ai_service.generate_policy_section(payload)
                g = (generated or "").strip()
                if _is_insufficient_llm_response(g):
                    out[key] = draft
                else:
                    out[key] = g or draft
            except Exception as e:  # noqa: BLE001
                logger.error("AI section %s failed, using draft: %s", key, e)
                out[key] = draft

        for key in list_keys:
            items = structure.get(key)
            if not isinstance(items, list):
                items = []
            payload = {
                "section": key,
                "items": items,
                "full_context": {k: structure[k] for k in text_keys if k in structure},
            }
            try:
                generated = await ai_service.generate_policy_section(payload)
                out[key] = self._text_to_bullet_list(generated, fallback=items)
            except Exception as e:  # noqa: BLE001
                logger.error("AI section %s failed, using structure items: %s", key, e)
                out[key] = list(items)

        return out

    def _text_to_bullet_list(self, text: str, *, fallback: list[str]) -> list[str]:
        if not (text or "").strip() or _is_insufficient_llm_response(text):
            return list(fallback)
        lines = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            m = _BULLET_LINE.match(line)
            if m:
                lines.append(m.group(1).strip())
            elif re.match(r"^\d+[\.)]\s+", line):
                lines.append(re.sub(r"^\d+[\.)]\s+", "", line).strip())
            else:
                lines.append(line)
        return lines if lines else list(fallback)

    def render_html_preview(self, policy: dict[str, Any]) -> str:
        """Простой HTML для предпросмотра (экранирование текста)."""
        parts: list[str] = [
            "<!DOCTYPE html><html><head><meta charset=\"utf-8\"><title>Политика ИБ</title></head><body>"
        ]
        parts.append("<h1>Проект политики информационной безопасности</h1>")

        sections = [
            ("general", "1. Общие положения"),
            ("scope", "2. Область применения"),
            ("assets", "3. Активы"),
            ("classification", "4. Классификация и среда"),
            ("risks", "5. Риски"),
            ("requirements", "6. Требования"),
            ("measures", "7. Меры защиты"),
            ("conclusion", "8. Заключение"),
        ]

        for key, title in sections:
            parts.append(f"<h2>{html.escape(title)}</h2>")
            val = policy.get(key)
            if isinstance(val, list):
                parts.append("<ul>")
                for item in val:
                    parts.append(f"<li>{html.escape(str(item))}</li>")
                parts.append("</ul>")
            else:
                text = str(val or "")
                for para in text.split("\n\n"):
                    p = para.strip()
                    if p:
                        parts.append(f"<p>{html.escape(p)}</p>")

        parts.append("</body></html>")
        return "\n".join(parts)

    def export_docx(self, policy: dict[str, Any], file_path: str) -> None:
        try:
            from docx import Document
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("Установите пакет python-docx") from e

        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        doc = Document()
        doc.add_heading("Политика информационной безопасности", level=0)

        sections = [
            ("general", "1. Общие положения"),
            ("scope", "2. Область применения"),
            ("assets", "3. Активы"),
            ("classification", "4. Классификация и среда"),
            ("risks", "5. Риски"),
            ("requirements", "6. Требования"),
            ("measures", "7. Меры защиты"),
            ("conclusion", "8. Заключение"),
        ]

        for key, heading in sections:
            doc.add_heading(heading, level=1)
            val = policy.get(key)
            if isinstance(val, list):
                for item in val:
                    p = doc.add_paragraph(style="List Bullet")
                    p.add_run(str(item))
            else:
                text = str(val or "")
                for para in text.split("\n\n"):
                    p = para.strip()
                    if p:
                        doc.add_paragraph(p)

        doc.save(str(path))
        logger.info("DOCX exported: %s", path)


def get_policy_service() -> PolicyService:
    return PolicyService()
