from rest_access_policy import AccessPolicy

from api.models import Stage
from api.utils import filter_for_user_creatable_stages


class CampaignAccessPolicy(AccessPolicy):
    statements = [
        {
            "action": ["list"],
            "principal": "authenticated",
            "effect": "allow"
        },
        {
            "action": ["create"],
            "principal": ["group:campaign_creator"],
            "effect": "allow"
        }
    ]


class TaskAccessPolicy(AccessPolicy):
    statements = [
        {
            "action": ["update",
                       "partial_update",
                       "release_assignment"],
            "principal": "authenticated",
            "effect": "allow",
            "condition_expression": "is_assignee and not is_complete"
        },
        {
            "action": ["request_assignment"],
            "principal": "authenticated",
            "effect": "allow",
            "condition_expression": "not is_assigned and not is_complete"
        },
        {
            "action": ["create"],
            "principal": "authenticated",
            "effect": "allow",
            "condition_expression": "is_creatable"
        },

    ]

    def is_assignee(self, request, view, action):
        task = view.get_object()
        return request.user == task.assignee

    def is_assigned(self, request, view, action):
        task = view.get_object()
        return task.assignee is not None

    def is_complete(self, request, view, action):
        task = view.get_object()
        return task.complete

    def is_user_creatable(self, request, view, action):
        try:
            stage = Stage.objects.filter(id=request.POST.get('stage'))
            filtered_stage = filter_for_user_creatable_stages(stage)
            return len(filtered_stage) == 1
        except:
            return False