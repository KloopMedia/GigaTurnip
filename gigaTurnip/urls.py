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

    path(r'api/v1/allcampaigns/', turnip_app.AllCampaigns.as_view()),
    re_path(r'api/v1/campaign/(?P<pk>\d+)', turnip_app.CampaignView.as_view()),

    path(r'api/v1/allchains/', turnip_app.AllChains.as_view()),
    re_path(r'api/v1/chain/(?P<pk>\d+)', turnip_app.ChainView.as_view()),

    # path(r'api/v1/allstages/', turnip_app.AllStages.as_view()),
    # re_path(r'api/v1/stage/(?P<pk>\d+)', turnip_app.StageView.as_view()),

    path(r'api/v1/alltaskstages/', turnip_app.AllTaskStageFillers.as_view()),
    re_path(r'api/v1/taskstage/(?P<pk>\d+)', turnip_app.TaskStageFillerView.as_view()),

    path(r'api/v1/allwebhookstages/', turnip_app.AllWebHookStageFillers.as_view()),
    re_path(r'api/v1/webhookstage/(?P<pk>\d+)', turnip_app.WebHookStageFillerView.as_view()),

    path(r'api/v1/allconditionalstages/', turnip_app.AllConditionalStageFillers.as_view()),
    re_path(r'api/v1/conditionalstage/(?P<pk>\d+)', turnip_app.ConditionalStageFillerView.as_view()),

    path(r'api/v1/allcases/', turnip_app.AllCases.as_view()),
    re_path(r'api/v1/case/(?P<pk>\d+)', turnip_app.CaseView.as_view()),

    path(r'api/v1/alltasks/', turnip_app.AllTasks.as_view()),
    re_path(r'api/v1/task/(?P<pk>\d+)', turnip_app.TaskView.as_view()),

]
