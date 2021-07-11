from rest_access_policy import AccessPolicy

from api.models import Stage

#
# class CampaignAccessPolicy(AccessPolicy):
#     statements = [
#         {
#             "action": ["list"],
#             "principal": "authenticated",
#             "effect": "allow"
#         },
#         {
#             "action": ["create"],
#             "principal": ["group:campaign_creator"],
#             "effect": "allow"
#         }
#     ]
#
#
# class TaskAccessPolicy(AccessPolicy):
#     statements = [
#         {
#             "action": ["update",
#                        "partial_update",
#                        "release_assignment"],
#             "principal": "authenticated",
#             "effect": "allow",
#             "condition_expression": "is_assignee and not is_complete"
#         },
#         {
#             "action": ["request_assignment"],
#             "principal": "authenticated",
#             "effect": "allow",
#             "condition_expression": "not is_assigned and not is_complete"
#         },
#         {
#             "action": ["request_assignment"],
#             "principal": "authenticated",
#             "effect": "allow",
#             "condition_expression": "not is_assigned and not is_complete"
#         },
#
#     ]
#
#     def is_assignee(self, request, view, action):
#         task = view.get_object()
#         return request.user == task.assignee
#
#     def is_assigned(self, request, view, action):
#         task = view.get_object()
#         return task.assignee is not None
#
#     def is_complete(self, request, view, action):
#         task = view.get_object()
#         return task.complete
#
#     def is_creatable(self, request, view, action):
#         try:
#             stage = Stage.objects.get(id=request.POST.get('stage'))
#             return stage.is_creatable
#         except:
#             return False
