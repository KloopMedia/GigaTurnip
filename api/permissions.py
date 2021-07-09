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
