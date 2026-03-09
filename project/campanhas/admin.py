from django.contrib import admin

from .models import CampanhaMetric, UploadCampanha

admin.site.register(UploadCampanha)
admin.site.register(CampanhaMetric)

