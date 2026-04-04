import enum


class QuestionnaireStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"
    needs_revision = "needs_revision"
    approved = "approved"


class ValidationStatus(str, enum.Enum):
    pending = "pending"
    valid = "valid"
    invalid = "invalid"


class EnvironmentType(str, enum.Enum):
    IT = "IT"
    OT = "OT"


class CriticalityLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class RiskLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class PolicyDocumentStatus(str, enum.Enum):
    draft = "draft"
    generated = "generated"
    approved = "approved"
    archived = "archived"
