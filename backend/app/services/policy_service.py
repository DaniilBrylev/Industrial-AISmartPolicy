"""
Генерация текста политики ИБ из анкеты и analysis_result (rules + AI).

CRUD сущностей PolicyDocument см. policy_document_service.
"""

from __future__ import annotations

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

        assets_lines = self._lines_from_report_list(analysis_result.get("assets"), "asset")
        class_lines = self._lines_classified(analysis_result.get("classified_assets"))
        risk_lines = self._lines_from_report_list(analysis_result.get("risks"), "risk")
        req_lines = self._string_list(analysis_result.get("requirements"))
        meas_lines = self._string_list(analysis_result.get("measures"))

        if not assets_lines and isinstance(response_data.get("assets"), list):
            assets_lines = self._lines_from_raw_assets(response_data["assets"])

        conclusion = (
            "Политика носит рамочный характер; конкретные регламенты и сроки внедрения "
            "определяются локальными актами на основе результатов анализа рисков."
        )

        return {
            "general": general,
            "scope": scope,
            "assets": assets_lines,
            "classification": class_lines,
            "risks": risk_lines,
            "requirements": req_lines,
            "measures": meas_lines,
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
                out[key] = (generated or draft).strip() or draft
            except Exception as e:  # noqa: BLE001
                logger.warning("AI section %s failed: %s", key, e)
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
                logger.warning("AI section %s failed: %s", key, e)
                out[key] = list(items)

        return out

    def _text_to_bullet_list(self, text: str, *, fallback: list[str]) -> list[str]:
        if not (text or "").strip():
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
