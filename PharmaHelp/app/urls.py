from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .views import saleHistoryView


urlpatterns = [
    # Leave empty for now, but the list must exist
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('inventory_report/', views.inventory, name='inventoryr'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('scan/<str:barcode>/', views.scan_barcode, name='scan_barcode'),
    path('update-stock/<str:barcode>/', views.update_stock, name='update_stock'),
    path('sales/', views.sales_page, name='sales_page'),
    path('process-sale/', views.process_sale, name='process_sale'),
    path('transactions/', saleHistoryView.as_view(), name='sale_history')
    
]
