from api.models import TaskStage, Task, RankLimit


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
