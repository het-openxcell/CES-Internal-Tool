from fastapi import APIRouter

from src.api.routes.v1.auth import router as auth_router
from src.api.routes.v1.corrections import router as corrections_router
from src.api.routes.v1.ddr import router as ddr_router
from src.api.routes.v1.export import router as export_router
from src.api.routes.v1.health import router as health_router
from src.api.routes.v1.history import router as history_router
from src.api.routes.v1.keywords import router as keywords_router
from src.api.routes.v1.monitor import router as monitor_router
from src.api.routes.v1.occurrences import router as occurrences_router
from src.api.routes.v1.pipeline import router as pipeline_router
from src.api.routes.v1.query import router as query_router
from src.api.routes.v1.users import router as users_router

router = APIRouter()


router.include_router(router=auth_router)
router.include_router(router=corrections_router)
router.include_router(router=ddr_router)
router.include_router(router=pipeline_router)
router.include_router(router=keywords_router)
router.include_router(router=monitor_router)
router.include_router(router=occurrences_router)
router.include_router(router=history_router)
router.include_router(router=query_router)
router.include_router(router=export_router)
router.include_router(router=health_router)
router.include_router(router=users_router)
