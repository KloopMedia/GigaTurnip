import json

from rest_framework import status

from api.models import Rank, TaskAward
from api.tests import GigaTurnipTestHelper


class TrackTest(GigaTurnipTestHelper):
    def test_track_map(self):
        track = self.user.ranks.all()[0].track
        prize_rank_1 = Rank.objects.create(name='Good', track=track)
        prize_rank_2 = Rank.objects.create(name='Best', track=track)
        prize_rank_3 = Rank.objects.create(name='Superman', track=track)
        prize_rank_3.prerequisite_ranks.add(prize_rank_1)
        prize_rank_3.prerequisite_ranks.add(prize_rank_2)

        schema = {"type": "object", "properties": {"foo": {"type": "string", "title": "what is ur name"}}}

        self.initial_stage.json_schema = json.dumps(schema)
        self.initial_stage.save()
        TaskAward.objects.create(
            task_stage_completion=self.initial_stage,
            task_stage_verified=self.initial_stage,
            rank=prize_rank_1,
            count=5
        )

        response = self.get_objects("track-get-map", pk=track.id)

        print(response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)