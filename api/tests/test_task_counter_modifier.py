from api.models import TaskStage, Task, RankLimit
from api.models.modifiers import CountTasksModifier
from api.tests import GigaTurnipTestHelper


class TaskCounterTest(GigaTurnipTestHelper):

    def test_task_count(self):
        verification_task_stage = self.initial_stage.add_stage(TaskStage())

        CountTasksModifier.objects.create(
            task_stage=verification_task_stage,
            stage_to_count_tasks_from=self.initial_stage,
            field_to_write_count_to="task_count"
        )

        task = self.create_task(self.initial_stage)

        self.create_task(self.initial_stage)
        self.create_task(self.initial_stage)

        self.complete_task(task)

        task_to_check = Task.objects.get(case=task.case, stage=verification_task_stage)

        self.assertEqual(task_to_check.responses["task_count"], 3)


    def test_task_count_unique_users(self):
            verification_task_stage = self.initial_stage.add_stage(TaskStage())

            CountTasksModifier.objects.create(
                task_stage=verification_task_stage,
                stage_to_count_tasks_from=self.initial_stage,
                field_to_write_count_to="task_count",
                count_unique_users=True,
            )

            task = self.create_task(self.initial_stage)

            self.create_task(self.initial_stage)

            client = self.prepare_client(
                self.initial_stage,
                self.employee,
                RankLimit(is_creation_open=True))
            self.create_task(self.initial_stage, client=client)
            

            self.complete_task(task)

            task_to_check = Task.objects.get(case=task.case, stage=verification_task_stage)

            self.assertEqual(task_to_check.responses["task_count"], 2)