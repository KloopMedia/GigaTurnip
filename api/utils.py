from api.models import TaskStage, Task, RankLimit, Campaign


def filter_managed_campaigns(request):
	managed_campaigns = Campaign.objects.all() \
		.filter(campaign_managements__user=request.user)
	return managed_campaigns


def filter_for_user_creatable_stages(queryset, request):
	stages = queryset \
		.filter(is_creatable=True) \
		.filter(ranks__users=request.user.id) \
		.filter(ranklimits__is_creation_open=True) \
		.distinct()
	filtered_stages = TaskStage.objects.none()
	for stage in stages:
		tasks = Task.objects.filter(assignee=request.user.id) \
			.filter(stage=stage).distinct()
		total = len(tasks)
		print(total)
		incomplete = len(tasks.filter(complete=False))
		print(incomplete)
		ranklimits = RankLimit.objects.filter(stage=stage) \
			.filter(rank__rankrecord__user__id=request.user.id)
		for ranklimit in ranklimits:
			print(ranklimit.total_limit)
			print(ranklimit.open_limit)
			if ((ranklimit.open_limit > incomplete and ranklimit.total_limit > total) or
				(ranklimit.open_limit == 0 and ranklimit.total_limit > total) or
				(ranklimit.open_limit > incomplete and ranklimit.total_limit == 0) or
				(ranklimit.open_limit == 0 and ranklimit.total_limit == 0)
			):
				filtered_stages |= TaskStage.objects.filter(pk=stage.pk)

	return filtered_stages.distinct()


def filter_for_user_selectable_tasks(queryset, request):
	tasks = queryset \
		.filter(complete=False) \
		.filter(assignee__isnull=True) \
		.filter(stage__ranks__users=request.user.id) \
		.filter(stage__ranklimits__is_selection_open=True) \
		.filter(stage__ranklimits__is_listing_allowed=True) \
		.distinct()
	return tasks


def filter_tasks_for_manager(queryset, request):
	managed_campaigns = filter_managed_campaigns(request)
	queryset = queryset \
		.filter(stage__chain__campaign__in=managed_campaigns.values_list('id'))
	return queryset


def filter_assignee_tasks(queryset, request):
	return queryset.filter(assignee=request.user)