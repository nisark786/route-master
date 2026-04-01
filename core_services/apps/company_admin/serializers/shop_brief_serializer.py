from rest_framework import serializers

from apps.company_admin.models import Shop


class ShopBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = [
            "id",
            "name",
            "owner_name",
        ]
