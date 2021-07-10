from rest_access_policy import AccessPolicy

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
        },
        {
            "action": ["destroy"],
            "principal": ["group:campaign_creator"],
            "effect": "allow"
        },
        {
            "action": ["partial_update"],
            "principal": ["*"],
            "effect": "allow",
            "condition": "is_manager"
        }
    ]

    def is_manager(self, request, view, action) -> bool:
        campaign = view.get_object()
        managers = campaign.managers.all()

        return request.user in managers

class ChainAccessPolicy(AccessPolicy):
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
            "action": ["update"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "is_assignee" and "not_complete"
        },
        {
            "action": ["partial_update"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "is_assignee" and "not_complete"
        }
    ]
    def is_assignee(self, request, view, action):
        task = view.get_object()
        return request.user == task.assignee

    def not_complete(self, request, view, action):
        task = view.get_object()
        return task.complete is False
