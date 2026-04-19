"""
Signals for the payments app.
Handles automatic email sending when payment status changes.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.mail import EmailMultiAlternatives
from .models import Payment
import logging

logger = logging.getLogger(__name__)


# Track the previous state of the payment fields
_payment_state = {}


@receiver(pre_save, sender=Payment)
def track_payment_status_changes(sender, instance, **kwargs):
    """
    Track whether payment status fields are being changed.
    This runs before the save to capture the old state.
    """
    if instance.pk:  # Only for existing records being updated
        try:
            old_instance = Payment.objects.get(pk=instance.pk)
            _payment_state[instance.pk] = {
                'old_approved': old_instance.approved,
                'old_rejection_reason': old_instance.rejection_reason,
            }
        except Payment.DoesNotExist:
            _payment_state[instance.pk] = {
                'old_approved': False,
                'old_rejection_reason': None,
            }


@receiver(post_save, sender=Payment)
def send_payment_email_on_status_change(sender, instance, created, **kwargs):
    """
    Send email notifications when payment status changes.
    
    - Sends approval email when approved changes from False to True
    - Sends rejection email when rejection_reason is newly set
    """
    if not created:  # Only for existing payments being updated
        state = _payment_state.get(instance.pk, {})
        old_approved = state.get('old_approved', False)
        old_rejection_reason = state.get('old_rejection_reason', None)
        new_approved = instance.approved
        new_rejection_reason = instance.rejection_reason
        
        logger.debug(
            f"Payment {instance.pk} - approved: {old_approved}→{new_approved}, "
            f"rejection_reason: {bool(old_rejection_reason)}→{bool(new_rejection_reason)}"
        )
        
        # If approval status changed from False to True, send approval email
        if not old_approved and new_approved:
            try:
                instance.send_approval_email()
                logger.info(f"✓ Approval email sent for payment {instance.pk}")
            except Exception as e:
                logger.error(f"✗ Failed to send approval email for payment {instance.pk}: {str(e)}", exc_info=True)
        
        # If rejection reason was newly set (wasn't set before), send rejection email
        if not old_rejection_reason and new_rejection_reason:
            try:
                instance.send_rejection_email(new_rejection_reason)
                logger.info(f"✓ Rejection email sent for payment {instance.pk}")
            except Exception as e:
                logger.error(f"✗ Failed to send rejection email for payment {instance.pk}: {str(e)}", exc_info=True)
        
        # Clean up the tracking dict
        if instance.pk in _payment_state:
            del _payment_state[instance.pk]
