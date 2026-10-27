from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('tracker.urls')),
]

# Customize admin header and titles for academic project
admin.site.site_header = "StudyTrack Administration"
admin.site.site_title = "StudyTrack Admin Portal"
admin.site.index_title = "Welcome to StudyTrack Database & Records Manager"
