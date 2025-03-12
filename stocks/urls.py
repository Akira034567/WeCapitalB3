from django.urls import path
from .views import stock_selection_view, stock_analysis_view, export_csv  # Substitua 'your_app'

urlpatterns = [
    path("", stock_selection_view, name="stock_selection"),  # Formulário inicial
    path("analyze/", stock_analysis_view, name="stock_analysis"),  # Página de análise
    path("export_csv/", export_csv, name="export_csv"),  # Exportação CSV
]
