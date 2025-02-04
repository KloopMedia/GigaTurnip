from rest_framework import status
from api.tests.api_helper import GigaTurnipTestHelper
from api.models import Volume, Track, Rank, CustomUser, RankRecord

class VolumeTest(GigaTurnipTestHelper):
    def test_volume_rank_access(self):
        """Test volume access based on user ranks (default, opening, and closing ranks)"""
        self.default_track.default_rank = self.default_rank
        self.default_track.save()
        
        # Create different ranks for testing
        opening_rank = Rank.objects.create(
            name="Opening Rank",
            track=self.default_track
        )
        closing_rank = Rank.objects.create(
            name="Closing Rank",
            track=self.default_track
        )

        # Create a volume with specific rank requirements
        volume = Volume.objects.create(
            name="Test Volume",
            track_fk=self.default_track,
            order=1
        )
        volume.opening_ranks.add(opening_rank)
        volume.closing_ranks.add(closing_rank)

        # Test with user without default rank for this track
        response = self.get_objects("volume-list", 
                                  params={'track_fk': self.default_track.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)
        
        # Add default rank to user
        RankRecord.objects.create(
            user=self.user,
            rank=self.default_rank
        )
        
        response = self.get_objects("volume-list", 
                                  params={'track_fk': self.default_track.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        volume_data = response.data['results'][0]
        self.assertTrue(volume_data["user_has_default_rank"])
        self.assertFalse(volume_data["user_has_opening_ranks"])
        self.assertFalse(volume_data["user_has_closing_ranks"])

        
        # Add opening rank to user
        RankRecord.objects.create(
            user=self.user,
            rank=opening_rank
        )

        # Test with user having default and opening ranks
        response = self.get_objects("volume-list",
                                  params={'track_fk': self.default_track.id})
        volume_data = response.data['results'][0]
        self.assertTrue(volume_data["user_has_default_rank"])
        self.assertTrue(volume_data["user_has_opening_ranks"])
        self.assertFalse(volume_data["user_has_closing_ranks"])

        # Add closing rank to user
        RankRecord.objects.create(
            user=self.user,
            rank=closing_rank
        )

        # Test with user having all ranks
        response = self.get_objects("volume-list",
                                  params={'track_fk': self.default_track.id})
        volume_data = response.data['results'][0]
        self.assertTrue(volume_data["user_has_default_rank"])
        self.assertTrue(volume_data["user_has_opening_ranks"])
        self.assertTrue(volume_data["user_has_closing_ranks"])
