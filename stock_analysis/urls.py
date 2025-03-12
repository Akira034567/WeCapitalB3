from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('stocks.urls')),  # Inclui as rotas do app "stocks"
]