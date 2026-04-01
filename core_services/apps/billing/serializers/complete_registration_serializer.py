from rest_framework import serializers


class CompleteRegistrationSerializer(serializers.Serializer):
    registration_id = serializers.UUIDField()
    razorpay_order_id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    razorpay_payment_id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    razorpay_signature = serializers.CharField(max_length=255, required=False, allow_blank=True)
