from fastapi import APIRouter

from src.api.routes.v1.auth import router as auth_router
from src.api.routes.v1.ddr import router as ddr_router
from src.api.routes.v1.health import router as health_router
from src.api.routes.v1.keywords import router as keywords_router
from src.api.routes.v1.monitor import router as monitor_router
from src.api.routes.v1.pipeline import router as pipeline_router
from src.api.routes.v1.user import router as user_router

router = APIRouter()

router.include_router(router=user_router)
router.include_router(router=auth_router)
router.include_router(router=ddr_router)
router.include_router(router=pipeline_router)
router.include_router(router=keywords_router)
router.include_router(router=monitor_router)
router.include_router(router=health_router)
