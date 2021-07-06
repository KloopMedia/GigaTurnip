"""newJournal URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, re_path
from rest_framework.routers import DefaultRouter

import api.views as turnip_app

api_v1 = r'api/v1/'

router = DefaultRouter()
router.register(api_v1 + r'campaigns',
                turnip_app.CampaignViewSet,
                basename='campaign')
router.register(api_v1 + r'chains',
                turnip_app.TaskViewSet,
                basename='chain')
router.register(api_v1 + r'chains',
                turnip_app.ChainViewSet,
                basename='chain')
router.register(api_v1 + r'taskstages',
                turnip_app.TaskStageViewSet,
                basename='taskstage')
router.register(api_v1 + r'webhookstages',
                turnip_app.WebHookStageViewSet,
                basename='webhookstage')
router.register(api_v1 + r'conditionalstages',
                turnip_app.ConditionalStageViewSet,
                basename='conditionalstage')
router.register(api_v1 + r'cases',
                turnip_app.CaseViewSet,
                basename='case')
router.register(api_v1 + r'tasks',
                turnip_app.TaskViewSet,
                basename='task')

urlpatterns = [path('admin/', admin.site.urls), ] + router.urls
