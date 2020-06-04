from django.contrib import admin
from django.urls import path

from . import views

urlpatterns = [
    path('', views.index),
    path('network', views.reply_network),
    path('subswitch', views.subswitch),
    path('json_graph', views.get_graph),
    path('json_switch', views.get_switch_graph)
]
