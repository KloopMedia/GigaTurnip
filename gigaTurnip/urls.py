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
from rest_framework.routers import DefaultRouter
from rest_framework.documentation import include_docs_urls
from .yasg import urlpatterns as doc_urls
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

import api.views as turnip_app
import dictionary.views as dictionary_app

api_v1 = r"api/v1/"

router = DefaultRouter()
router.register(api_v1 + r"users", turnip_app.UserViewSet, basename="user"),
router.register(api_v1 + r"campaigns", turnip_app.CampaignViewSet, basename="campaign"),
router.register(api_v1 + r"chains", turnip_app.ChainViewSet, basename="chain")
router.register(
    api_v1 + r"taskstages", turnip_app.TaskStageViewSet, basename="taskstage"
)
router.register(
    api_v1 + r"taskawards", turnip_app.TaskAwardViewSet, basename="taskaward"
)
# router.register(api_v1 + r'webhookstages',
#                 turnip_app.WebHookStageViewSet,
#                 basename='webhookstage')
router.register(
    api_v1 + r"conditionalstages",
    turnip_app.ConditionalStageViewSet,
    basename="conditionalstage",
)
router.register(api_v1 + r"cases", turnip_app.CaseViewSet, basename="case")
router.register(api_v1 + r"tasks", turnip_app.TaskViewSet, basename="task")
router.register(api_v1 + r"ranks", turnip_app.RankViewSet, basename="rank")
router.register(
    api_v1 + r"ranklimits", turnip_app.RankLimitViewSet, basename="ranklimit"
)
router.register(api_v1 + r"tracks", turnip_app.TrackViewSet, basename="track")
router.register(
    api_v1 + r"rankrecords", turnip_app.RankRecordViewSet, basename="rankrecord"
)
# router.register(api_v1 + r'campaignmanagements',
#                 turnip_app.CampaignManagementViewSet,
#                 basename='campaignmanagement')
router.register(
    api_v1 + r"notifications", turnip_app.NotificationViewSet, basename="notification"
)
router.register(
    api_v1 + r"responseflatteners",
    turnip_app.ResponseFlattenerViewSet,
    basename="responseflattener",
)
router.register(
    api_v1 + r"dynamicjsons", turnip_app.DynamicJsonViewSet, basename="dynamicjson"
)
router.register(
    api_v1 + r"testwebhook", turnip_app.TestWebhookViewSet, basename="testwebhook"
)
router.register(
    api_v1 + r"numberranks", turnip_app.NumberRankViewSet, basename="numberrank"
)
router.register(
    api_v1 + r"users_statistics",
    turnip_app.UserStatisticViewSet,
    basename="user_statistic",
)
router.register(api_v1 + r"categories", turnip_app.CategoryViewSet, basename="category")
router.register(api_v1 + r"languages", turnip_app.LanguageViewSet, basename="language")
router.register(api_v1 + r"countries", turnip_app.CountryViewSet, basename="country")
router.register(api_v1 + r"auth", turnip_app.AuthViewSet, basename="auth")
router.register(api_v1 + r"fcm", turnip_app.FCMTokenViewSet, basename="fcm")
router.register(api_v1 + r"volumes", turnip_app.VolumeViewSet, basename="volume")

router.register(api_v1 + r"words", dictionary_app.WordViewSet, basename="word")
router.register(
    api_v1 + r"dictionary_catergories",
    dictionary_app.CategoryViewSet,
    basename="word_category",
)
router.register(
    api_v1 + r"levels", dictionary_app.ProficiencyLevelViewSet, basename="level"
)

urlpatterns = (
    static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    + [
        path("admin/", admin.site.urls),
        # path('__debug__/', include('debug_toolbar.urls')),
        path("docs/", include_docs_urls(title="Giga Turnip API Documentation")),
    ]
    + router.urls
)

urlpatterns += doc_urls
