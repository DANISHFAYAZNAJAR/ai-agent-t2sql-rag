"""
URL configuration for app project.
"""
from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI
from api.auth import router as auth_router
from api.query import router as query_router
from api.documents import router as documents_router

# Create Django Ninja API instance
api = NinjaAPI(
    title="AI Agent API",
    description="Intelligent agent API for Text-to-SQL and Document RAG",
    version="1.0.0",
)

# Include routers
api.add_router("/auth", auth_router, tags=["Authentication"])
api.add_router("", query_router, tags=["Agent"])
api.add_router("/documents", documents_router, tags=["Documents"])

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
]
