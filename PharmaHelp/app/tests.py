from django.test import TestCase, Client
from django.urls import reverse
from .models import Drug, StockMovement
from decimal import Decimal
from datetime import date

class DrugEndpointTests(TestCase):
    def setUp(self):
        # Create test drug
        self.drug = Drug.objects.create(
            barcode="123456789",
            name="Test Paracetamol",
            category="ANL",
            descriptionType="500mg tablets",
            in_Stock=100,
            price=Decimal("5.99"),
            expiry_Date=date(2024, 12, 31)
        )
        self.client = Client()

    def test_scan_barcode(self):
        # Test scanning existing barcode
        url = reverse('scan_barcode', args=[self.drug.barcode])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['name'], "Test Paracetamol")
        self.assertEqual(response.json()['in_stock'], 100)

    def test_scan_nonexistent_barcode(self):
        # Test scanning non-existent barcode
        url = reverse('scan_barcode', args=['nonexistent'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_update_stock(self):
        # Test stock update
        url = reverse('update_stock', args=[self.drug.barcode])
        data = {
            'quantity': 50,
            'movement_type': 'IN',
            'reason': 'New stock arrival'
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['new_stock'], 150)

        # Verify stock movement was created
        movement = StockMovement.objects.last()
        self.assertEqual(movement.quantity_changed, 50)
        self.assertEqual(movement.movement_type, 'IN')
