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
import api.views as turnip_app

urlpatterns = [
    path('admin/', admin.site.urls),

    path(r'api/v1/campaigns/', turnip_app.CampaignList.as_view()),
    re_path(r'api/v1/campaigns/(?P<pk>\d+)', turnip_app.CampaignDetail.as_view()),

    path(r'api/v1/chains/', turnip_app.ChainList.as_view()),
    re_path(r'api/v1/chains/(?P<pk>\d+)', turnip_app.ChainDetail.as_view()),

    path(r'api/v1/taskstages/', turnip_app.TaskStageList.as_view()),
    re_path(r'api/v1/taskstages/(?P<pk>\d+)', turnip_app.TaskStageDetail.as_view()),

    path(r'api/v1/webhookstages/', turnip_app.WebHookStageList.as_view()),
    re_path(r'api/v1/webhookstages/(?P<pk>\d+)', turnip_app.WebHookStageDetail.as_view()),

    path(r'api/v1/conditionalstages/', turnip_app.ConditionalStageList.as_view()),
    re_path(r'api/v1/conditionalstages/(?P<pk>\d+)', turnip_app.ConditionalStageDetail.as_view()),

    path(r'api/v1/cases/', turnip_app.CaseList.as_view()),
    re_path(r'api/v1/cases/(?P<pk>\d+)', turnip_app.CaseDetail.as_view()),

    path(r'api/v1/tasks/', turnip_app.TaskList.as_view()),
    re_path(r'api/v1/tasks/(?P<pk>\d+)', turnip_app.TaskDetail.as_view()),

]
