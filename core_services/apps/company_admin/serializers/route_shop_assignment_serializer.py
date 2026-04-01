from rest_framework import serializers

from apps.company_admin.models import RouteShop

from .shop_brief_serializer import ShopBriefSerializer


class RouteShopAssignmentSerializer(serializers.ModelSerializer):
    shop = ShopBriefSerializer(read_only=True)

    class Meta:
        model = RouteShop
        fields = ["id", "position", "shop"]
