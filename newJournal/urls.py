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
import journalAPI.views as journal_app

urlpatterns = [
    path('admin/', admin.site.urls),
    path(r'v1/allcampaigns/', journal_app.AllCampaigns.as_view()),
    re_path(r'v1/campaign/(?P<pk>\d+)', journal_app.CampaignView.as_view()),
    path(r'v1/allchains/', journal_app.AllChains.as_view()),
    re_path(r'v1/chain/(?P<pk>\d+)', journal_app.ChainView.as_view()),
    path(r'v1/allstages/', journal_app.AllStages.as_view()),
    re_path(r'v1/stage/(?P<pk>\d+)', journal_app.StageView.as_view()),
    path(r'v1/alltaskstagefillers/', journal_app.AllTaskStageFillers.as_view()),
    re_path(r'v1/taskstagefiller/(?P<pk>\d+)', journal_app.TaskStageFillerView.as_view()),
    path(r'v1/allwebhookfillers/', journal_app.AllWebHookStageFillers.as_view()),
    re_path(r'v1/webhookfiller/(?P<pk>\d+)', journal_app.WebHookStageFillerView.as_view()),
    path(r'v1/allconditionalstagefillers/', journal_app.AllConditionalStageFillers.as_view()),
    re_path(r'v1/conditionalstagefillers/(?P<pk>\d+)', journal_app.ConditionalStageFillerView.as_view()),
    path(r'v1/allcases/', journal_app.AllCases.as_view()),
    re_path(r'v1/case/(?P<pk>\d+)', journal_app.CaseView.as_view()),
    path(r'v1/alltasks/', journal_app.AllTasks.as_view()),
    re_path(r'v1/task/(?P<pk>\d+)', journal_app.TaskView.as_view()),

]
