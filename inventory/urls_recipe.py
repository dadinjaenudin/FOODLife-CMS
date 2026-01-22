from django.urls import path
from inventory.views import recipe_views

app_name = 'recipe'

urlpatterns = [
    path('', recipe_views.recipe_list, name='list'),
    path('create/', recipe_views.recipe_create, name='create'),
    path('<uuid:pk>/edit/', recipe_views.recipe_update, name='edit'),
    path('<uuid:pk>/delete/', recipe_views.recipe_delete, name='delete'),
]
