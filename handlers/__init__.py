from aiogram import Dispatcher
from .start import router as start_router
from .admin import router as admin_router
from .employee import router as employee_router
from .reasons import router as reasons_router

def setup_routers(dp: Dispatcher):
    """Register all modular routers into the main Dispatcher."""
    dp.include_router(start_router)
    dp.include_router(admin_router)
    dp.include_router(employee_router)
    dp.include_router(reasons_router)
