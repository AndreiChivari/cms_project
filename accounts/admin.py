from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    # Cum arată lista de utilizatori
    list_display = ('username', 'email', 'first_name', 'last_name', 'rol', 'unitate', 'is_staff')
    
    # Filtre laterale
    list_filter = ('rol', 'is_staff', 'is_superuser', 'is_active')
    
    # Câmpurile personalizate trebuie adăugate în 'fieldsets' pentru a putea fi editate din Admin
    fieldsets = UserAdmin.fieldsets + (
        ('Informații Profesionale', {'fields': ('rol', 'grad_profesional', 'unitate')}),
    )

# Înregistrăm modelul
admin.site.register(CustomUser, CustomUserAdmin)