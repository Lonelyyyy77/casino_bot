from aiogram import Router

router = Router()


async def missions_routers_func() -> Router:
    from .mission1 import router as mission1_router

    router.include_router(mission1_router)
    return router
