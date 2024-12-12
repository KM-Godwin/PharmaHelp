from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
import os
from django.contrib.auth.models import User


class Drug(models.Model):
    CATEGORY_CHOICES = [
        ('ANT', 'Antibiotic'),
        ('ANA', 'Anesthesia'),
        ('ANTH', 'AntiHistamine'),
        ('ANL', 'Analgesic'),
        ('ANT', 'Antiviral'),
        ('CAR', 'Cardiac'),
        ('OTH', 'Other'),
    ]

    # Basic Information
    barcode = models.CharField(max_length=100, unique=True, null=True, blank=True)
    name = models.CharField(max_length=100)
    category = models.CharField(
        max_length=4,
        choices=CATEGORY_CHOICES,
        default='OTH',
    )
    descriptionType = models.TextField(verbose_name="Description")

    # Stock and Price Information
    in_Stock = models.IntegerField(default=0, verbose_name="In Stock")
    minimum_stock = models.IntegerField(default=10, verbose_name="Minimum Stock Level")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    expiry_Date = models.DateField(verbose_name="Expiry Date")

    # Tracking Information
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reorder_level = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=10.00,
        help_text="Minimum stock level before reordering"
    )

    class Meta:
        verbose_name_plural = 'Drugs'
        ordering = ['category', 'name']
        indexes = [
            models.Index(fields=['barcode']),
            models.Index(fields=['name']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.name} ({self.barcode})"

    def clean(self):
        if self.in_Stock < 0:
            raise ValidationError("Stock cannot be negative")
        if self.expiry_Date < timezone.now().date():
            raise ValidationError("Expiry date cannot be in the past")

    def is_low_stock(self):
        """Check if drug is running low on stock"""
        return self.in_Stock <= self.minimum_stock

    def get_stock_value(self):
        """Calculate total value of stock"""
        return self.in_Stock * self.price

class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ('IN', 'Stock In'),
        ('OUT', 'Stock Out'),
    ]

    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='stock_movements')
    quantity_changed = models.IntegerField()
    movement_type = models.CharField(max_length=3, choices=MOVEMENT_TYPES)
    date = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=200, blank=True, null=True)
    reference_number = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['movement_type']),
        ]

    def clean(self):
        if self.quantity_changed <= 0:
            raise ValidationError("Quantity must be positive")
        if self.movement_type == 'OUT' and self.drug.in_Stock < self.quantity_changed:
            raise ValidationError("Insufficient stock available")

    def save(self, *args, **kwargs):
        self.clean()
        if self.movement_type == 'IN':
            self.drug.in_Stock += self.quantity_changed
        else:
            self.drug.in_Stock -= self.quantity_changed
        self.drug.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.movement_type} - {self.drug.name} - {self.quantity_changed}"

class Invoice(models.Model):
    ID = models.AutoField(primary_key=True)
    invoice_date = models.DateField(default=timezone.now)
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='invoices')
    product_Description = models.TextField()
    quantity = models.IntegerField()
    unit_Price = models.DecimalField(max_digits=10, decimal_places=2)
    totalPrice = models.DecimalField(max_digits=10, decimal_places=2)
    
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('CANCELLED', 'Cancelled'),
    ]
    payment_status = models.CharField(
        max_length=10,
        choices=PAYMENT_STATUS_CHOICES,
        default='PENDING'
    )

    class Meta:
        ordering = ['-invoice_date']
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'

    def save(self, *args, **kwargs):
        # Calculate total price
        self.totalPrice = self.unit_Price * self.quantity
        
        # Save first to get the ID
        super().save(*args, **kwargs)
        
        # Create stock movement after saving
        if not hasattr(self, '_stock_movement_created') and self.payment_status != 'CANCELLED':
            StockMovement.objects.create(
                drug=self.drug,
                quantity_changed=self.quantity,
                movement_type='OUT',
                reason=f'Invoice {self.invoice_number}',
                reference_number=self.invoice_number
            )
            self._stock_movement_created = True

    def formatted_total_Price(self):
        return "{:,.2f}".format(self.totalPrice)

    @property
    def invoice_number(self):
        if self.ID is None or self.invoice_date is None:
            return "New Invoice"
        return f"INV-{self.invoice_date.strftime('%Y%m%d')}-{self.ID:04d}"

    def __str__(self):
        return self.invoice_number


class Sale(models.Model):
    PAYMENT_CHOICES = [
        ('CASH', 'Cash'),
        ('MPESA', 'M-Pesa'),
    ]
    
    drug = models.ForeignKey(Drug, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ('CASH', 'Cash'),
            ('MPESA', 'MPESA'),
            # Add other payment methods as needed
        ],
        default='CASH'
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    
    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['-date']),
            models.Index(fields=['payment_method']),
        ]

    def save(self, *args, **kwargs):
        # Calculate total amount
        self.total_amount = self.drug.price * self.quantity
        
        # Validate stock availability
        if self.drug.in_Stock < self.quantity:
            raise ValidationError("Insufficient stock available")
        
        # Update drug stock
        self.drug.in_Stock -= self.quantity
        self.drug.save()
        
        # Save the sale
        super().save(*args, **kwargs)
        
        # Create stock movement record
        StockMovement.objects.create(
            drug=self.drug,
            quantity_changed=self.quantity,
            movement_type='OUT',
            reason=f'Sale #{self.id}'
        )

    def __str__(self):
        return f"Sale {self.id} - {self.drug.name} - {self.quantity} units"
