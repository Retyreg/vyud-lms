from fastapi import APIRouter

from app.api.v1 import courses, cron, demo, admin, feedback, health, nodes, orgs, quiz, sops, streaks, templates

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(courses.router)
api_router.include_router(nodes.router)
api_router.include_router(orgs.router)
api_router.include_router(streaks.router)
api_router.include_router(sops.router)
api_router.include_router(quiz.router)
api_router.include_router(feedback.router)
api_router.include_router(templates.router)
api_router.include_router(demo.router)
api_router.include_router(admin.router)
api_router.include_router(cron.router)
