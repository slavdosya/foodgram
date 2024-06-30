from django.contrib import admin

from users.models import User, Subscribe


class UserAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'username',
        'email',
        'first_name',
        'last_name'
    )
    list_filter = ('email', 'first_name')


class SubscribeAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'author'
    )


admin.site.register(User, UserAdmin)
admin.site.register(Subscribe, SubscribeAdmin)
