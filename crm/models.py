from django.db import models
from django.core.validators import MinValueValidator


class Lead(models.Model):
    """CRM Lead model for storing customer lead information"""
    
    LEAD_STATUS_CHOICES = [
        ('not_connected', 'Not Connected'),
        ('connected', 'Connected'),
        ('visit_scheduled', 'Visit Scheduled'),
        ('visit_done_not_purchased', 'Visit Done Not Purchased'),
        ('purchased', 'Purchased'),
        ('not_interested', 'Not Interested'),
    ]
    
    lead_id = models.CharField(max_length=50, unique=True, db_index=True)
    lead_name = models.CharField(max_length=200)
    email = models.EmailField()
    country_code = models.CharField(max_length=10)
    phone = models.CharField(max_length=20)
    project_name = models.CharField(max_length=200, db_index=True)
    unit_type = models.CharField(max_length=50, db_index=True)
    min_budget = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0)]
    )
    max_budget = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0)]
    )
    lead_status = models.CharField(
        max_length=50, 
        choices=LEAD_STATUS_CHOICES,
        db_index=True
    )
    last_conversation_date = models.DateField(null=True, blank=True, db_index=True)
    last_conversation_summary = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'leads'
        indexes = [
            models.Index(fields=['project_name', 'lead_status']),
            models.Index(fields=['unit_type', 'lead_status']),
            models.Index(fields=['last_conversation_date']),
        ]
    
    def __str__(self):
        return f"{self.lead_id} - {self.lead_name}"
