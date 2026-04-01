from rest_framework import serializers

from apps.company.models import Company


class CompanyProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["name", "official_email", "phone", "address"]

    def validate_official_email(self, value):
        company = self.instance
        if (
            value
            and Company.objects.exclude(id=company.id).filter(official_email__iexact=value.strip()).exists()
        ):
            raise serializers.ValidationError("A company with this official email already exists.")
        return value.strip() if value else value
