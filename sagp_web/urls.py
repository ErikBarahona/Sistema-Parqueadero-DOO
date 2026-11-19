from django.urls import include, path

urlpatterns = [
    path('', include('parqueadero.urls')),
]
