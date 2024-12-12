# app/management/commands/create_mock_data.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from app.models import Drug, Invoice, StockMovement
from datetime import timedelta
import random

class Command(BaseCommand):
    help = 'Creates mock data for testing'

    def handle(self, *args, **kwargs):
        # Create mock drugs
        drugs = [
            {
                'name': 'Amoxicillin',
                'barcode': 'AMX001',
                'category': 'ANT',
                'descriptionType': 'Antibiotic for bacterial infections',
                'in_Stock': 0,  # Start with 0 stock
                'minimum_stock': 20,
                'price': 9.99,
                'expiry_Date': timezone.now().date() + timedelta(days=365)
            },
            {
                'name': 'Paracetamol',
                'barcode': 'PCM002',
                'category': 'ANL',
                'descriptionType': 'Pain reliever and fever reducer',
                'in_Stock': 0,  # Start with 0 stock
                'minimum_stock': 30,
                'price': 5.99,
                'expiry_Date': timezone.now().date() + timedelta(days=730)
            },
            {
                'name': 'Cetirizine',
                'barcode': 'CTR003',
                'category': 'ANTH',
                'descriptionType': 'Antihistamine for allergies',
                'in_Stock': 0,  # Start with 0 stock
                'minimum_stock': 15,
                'price': 7.99,
                'expiry_Date': timezone.now().date() + timedelta(days=545)
            }
        ]

        created_drugs = []
        for drug_data in drugs:
            drug, created = Drug.objects.get_or_create(
                barcode=drug_data['barcode'],
                defaults=drug_data
            )
            created_drugs.append(drug)
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created drug: {drug.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Drug already exists: {drug.name}')
                )

        # Create initial stock movements (IN only)
        for drug in created_drugs:
            # First, add initial stock
            initial_stock = random.randint(100, 200)
            StockMovement.objects.create(
                drug=drug,
                quantity_changed=initial_stock,
                movement_type='IN',
                reason='Initial Stock',
                reference_number=f'INIT-{drug.barcode}-{timezone.now().strftime("%Y%m%d")}'
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'Added initial stock: {initial_stock} units for {drug.name}'
                )
            )

        # Create additional stock movements
        for drug in created_drugs:
            current_stock = drug.in_Stock
            
            # Create IN movements
            for _ in range(2):
                quantity = random.randint(10, 50)
                StockMovement.objects.create(
                    drug=drug,
                    quantity_changed=quantity,
                    movement_type='IN',
                    reason='Regular Restock',
                    reference_number=f'REF-IN-{drug.barcode}-{timezone.now().strftime("%Y%m%d")}-{random.randint(1000, 9999)}'
                )
                current_stock += quantity
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created stock IN movement: {quantity} units for {drug.name}'
                    )
                )

            # Create OUT movements
            for _ in range(2):
                max_out = min(50, current_stock)  # Don't take out more than we have
                if max_out > 0:
                    quantity = random.randint(1, max_out)
                    StockMovement.objects.create(
                        drug=drug,
                        quantity_changed=quantity,
                        movement_type='OUT',
                        reason='Sale',
                        reference_number=f'REF-OUT-{drug.barcode}-{timezone.now().strftime("%Y%m%d")}-{random.randint(1000, 9999)}'
                    )
                    current_stock -= quantity
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Created stock OUT movement: {quantity} units for {drug.name}'
                        )
                    )

        # Create mock invoices
        payment_statuses = ['PENDING', 'PAID', 'CANCELLED']
        
        for drug in created_drugs:
            for _ in range(2):  # Create 2 invoices per drug
                max_quantity = min(10, drug.in_Stock)  # Don't sell more than available
                if max_quantity > 0:
                    quantity = random.randint(1, max_quantity)
                    status = random.choice(payment_statuses)
                    
                    invoice = Invoice.objects.create(
                        drug=drug,
                        product_Description=f'Sale of {drug.name}',
                        quantity=quantity,
                        unit_Price=drug.price,
                        invoice_date=timezone.now().date() - timedelta(days=random.randint(0, 30)),
                        payment_status=status
                    )
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Created invoice: {invoice.invoice_number} for {drug.name}'
                        )
                    )

        self.stdout.write(self.style.SUCCESS('Successfully created mock data'))
