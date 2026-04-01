from apps.main_admin.serializers import CompanyListQuerySerializer, PaginationQuerySerializer


def test_pagination_query_serializer_defaults():
    serializer = PaginationQuerySerializer(data={})

    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["page"] == 1
    assert serializer.validated_data["page_size"] == 10


def test_company_list_query_serializer_validates_status_choices():
    serializer = CompanyListQuerySerializer(data={"status": "invalid"})

    assert not serializer.is_valid()
    assert "status" in serializer.errors
