from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse
from .models import Drug, StockMovement, Sale
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F, Q
from .forms import SaleForm
from django.views.decorators.http import require_POST
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta

@login_required
def sales_page(request):
    query = request.GET.get('search', '')
    drugs = Drug.objects.all()
    
    if query:
        drugs = drugs.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query)
        )
    
    context = {
        'drugs': drugs,
        'search_query': query,
    }
    return render(request, 'sales/sales_page.html', context)

@login_required
@require_POST
def process_sale(request):
    if request.method == 'POST':
        form = SaleForm(request.POST)
        if form.is_valid():
            sale = form.save(commit=False)
            sale.user = request.user
            
            # Check if enough stock is available
            if sale.quantity > sale.drug.in_Stock:
                messages.error(request, 'Insufficient stock!')
                return redirect('sales_page')
            
            try:
                sale.save()
                return JsonResponse({
            'status': 'success',
            'message': 'Sale processed successfully!'
        })
            except Exception as e:
                return JsonResponse({
            'status': 'error',
            'message': f'Error processing sale: {str(e)}'
        })




@login_required
def inventory(request):
    # Calculate total inventory value
    total_value = Drug.objects.aggregate(
        total=Sum(F('price') * F('in_Stock')))['total'] or 0  # Note: using in_Stock instead of quantity

    # Get low stock items count
    low_stock_threshold = 10  # Adjust this value based on your needs
    low_stock_items = Drug.objects.filter(in_Stock__lte=low_stock_threshold).count()

    # Get expired items count
    from django.utils import timezone
    expired_items = Drug.objects.filter(expiry_Date__lt=timezone.now()).count()

    # Get category summary
    category_summary = Drug.objects.values('category').annotate(
        count=Count('id'),
        value=Sum(F('price') * F('in_Stock'))
    ).order_by('category')

    context = {
        'total_value': total_value,
        'low_stock_items': low_stock_items,
        'expired_items': expired_items,
        'category_summary': category_summary,
    }

    return render(request, 'inventory_report.html', context)

def login_view(request):
    # Redirect if user is already logged in
    if request.user.is_authenticated:
        return redirect('sales/sales_page')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username and password:
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                # Get the next URL or default to sales page
                next_url = request.GET.get('next', 'home')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Please fill in all fields.')
    
    return render(request, 'app/login.html')

@login_required
def home_view(request):
    context = {}
    
    # Get recent sales
    if request.user.is_staff:
        recent_sales = Sale.objects.all()[:5]
        # Get system statistics
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        context.update({
            'today_sales_count': Sale.objects.filter(date__gte=today_start).count(),
            'total_products': Drug.objects.count(),
            'low_stock_items': Drug.objects.filter(in_Stock__lte=10),  # Adjust threshold as needed
            'low_stock_count': Drug.objects.filter(in_Stock__lte=10).count(),
        })
    else:
        recent_sales = Sale.objects.filter(user=request.user)[:5]

    context['recent_sales'] = recent_sales
    return render(request, 'app/home.html', context)

@login_required
def inventory(request):
    return render(request, 'app/inventory_report.html')

def scan_barcode(request, barcode):
    drug = get_object_or_404(Drug, barcode=barcode)
    return JsonResponse({
        'id': drug.id,
        'name': drug.name,
        'in_stock': drug.in_Stock,
        'price': str(drug.price),
        'expiry_date': drug.expiry_Date
    })

def update_stock(request, barcode):
    drug = get_object_or_404(Drug, barcode=barcode)
    quantity = int(request.POST.get('quantity', 0))
    movement_type = request.POST.get('movement_type', 'IN')
    
    StockMovement.objects.create(
        drug=drug,
        quantity_changed=quantity,
        movement_type=movement_type,
        reason=request.POST.get('reason', '')
    )
    
    return JsonResponse({'success': True, 'new_stock': drug.in_Stock})


class saleHistoryView(LoginRequiredMixin, ListView):
    template_name = 'transactions/sale_history.html'
    model = Sale
    context_object_name = 'sales'
    paginate_by = 20

    def get_queryset(self):
        queryset = Sale.objects.all()
        user_id = self.request.GET.get('user_id')
        payment_method = self.request.GET.get('payment_method')
        
        # Filter by user if applicable
        if self.request.user.is_staff and user_id:
            queryset = queryset.filter(user_id=user_id)
        elif not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        
        # Filter MPESA sales if selected
        if payment_method == 'mpesa':
            queryset = queryset.filter(payment_method='MPESA')
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_admin'] = self.request.user.is_staff
        
        # Get the current queryset
        queryset = self.get_queryset()
        
        # Calculate total sales for the filtered queryset
        total_sales = queryset.aggregate(
            total=Sum(F('quantity') * F('drug__price'))
        )['total'] or 0
        
        context['total_sales'] = total_sales
        
        if self.request.user.is_staff:
            context['users'] = User.objects.all()
            user_id = self.request.GET.get('user_id')
            if user_id:
                context['selected_user'] = get_object_or_404(User, id=user_id)
                
        # Add payment method to context
        context['payment_method'] = self.request.GET.get('payment_method')
        
        return context
