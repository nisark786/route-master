from django.contrib import admin
from .models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'role', 'company', 'is_active')
    list_filter = ('role', 'company')
    search_fields = ('email',)

    def save_model(self, request, obj, form, change):
        if not request.user.is_platform_admin and request.user.company:
            obj.company = request.user.company
        super().save_model(request, obj, form, change)