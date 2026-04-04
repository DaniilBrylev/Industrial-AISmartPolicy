from fastapi import APIRouter

from app.api import health
from app.api.analysis import router as analysis_router
from app.api.assets import router as assets_router
from app.api.business_processes import router as business_processes_router
from app.api.departments import router as departments_router
from app.api.files import router as files_router
from app.api.policies import router as policies_router
from app.api.policy_generation import router as policy_generation_router
from app.api.policy_versions import router as policy_versions_router
from app.api.questionnaires import router as questionnaires_router
from app.api.versioning import router as versioning_router

api_router = APIRouter()

api_router.include_router(health.router, prefix="")
api_router.include_router(files_router)
api_router.include_router(departments_router)
api_router.include_router(questionnaires_router)
api_router.include_router(assets_router)
api_router.include_router(business_processes_router)
api_router.include_router(policies_router)
api_router.include_router(policy_versions_router)
api_router.include_router(analysis_router)
api_router.include_router(policy_generation_router)
api_router.include_router(versioning_router)
