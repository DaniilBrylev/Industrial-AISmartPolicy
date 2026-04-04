from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import QuestionnaireStatus
from app.models.questionnaire import Questionnaire
from app.schemas.questionnaire import QuestionnaireCreate, QuestionnaireUpdate

from app.services import department_service


def list_questionnaires(
    db: Session,
    *,
    skip: int,
    limit: int,
    department_id: int | None = None,
    status: QuestionnaireStatus | None = None,
) -> list[Questionnaire]:
    stmt = select(Questionnaire).order_by(Questionnaire.id)
    if department_id is not None:
        stmt = stmt.where(Questionnaire.department_id == department_id)
    if status is not None:
        stmt = stmt.where(Questionnaire.status == status)
    stmt = stmt.offset(skip).limit(limit)
    return list(db.scalars(stmt).all())


def get_questionnaire(db: Session, questionnaire_id: int) -> Questionnaire | None:
    return db.get(Questionnaire, questionnaire_id)


def create_questionnaire(db: Session, data: QuestionnaireCreate) -> Questionnaire | None:
    if department_service.get_department(db, data.department_id) is None:
        return None
    obj = Questionnaire(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_questionnaire(
    db: Session, questionnaire_id: int, data: QuestionnaireUpdate
) -> Questionnaire | None:
    obj = get_questionnaire(db, questionnaire_id)
    if obj is None:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete_questionnaire(db: Session, questionnaire_id: int) -> bool:
    obj = get_questionnaire(db, questionnaire_id)
    if obj is None:
        return False
    db.delete(obj)
    db.commit()
    return True
