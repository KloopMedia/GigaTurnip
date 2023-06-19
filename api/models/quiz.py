from django.db import models

from api.models import BaseDatesModel


class Quiz(BaseDatesModel):
    task_stage = models.OneToOneField(
        "TaskStage",
        primary_key=True,
        on_delete=models.CASCADE,
        related_name="quiz",
        help_text="Stage of the task that will be published")
    correct_responses_task = models.OneToOneField(
        "Task",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="quiz",
        help_text="Task containing correct responses to the quiz"
    )
    threshold = models.FloatField(
        blank=True,
        null=True,
        help_text="If set, task will not be closed with "
                  "quiz scores lower than this threshold"
    )

    class ShowAnswers(models.TextChoices):
        NEVER = 'NE', 'Never'
        ALWAYS = 'AL', 'Always'
        ON_FAIL = 'FA', 'On Fail'
        ON_PASS = 'PS', 'On Pass'

    show_answer = models.CharField(
        max_length=2,
        choices=ShowAnswers.choices,
        default=ShowAnswers.ON_FAIL,
    )
    SCORE = 'meta_quiz_score'
    INCORRECT_QUESTIONS = 'meta_quiz_incorrect_questions'
    provide_answers = models.BooleanField(
        default=False,
        help_text="If set as true then with questions title users will "
                  "see correct answers."
    )

    def is_ready(self):
        return bool(self.correct_responses_task)

    def check_score(self, responses):
        score, incorrect_questions = self.compare_with_correct_answers(responses)
        if self.show_answer == Quiz.ShowAnswers.ALWAYS:
            return score, incorrect_questions
        if self.show_answer == Quiz.ShowAnswers.NEVER:
            return score, []
        if self.threshold is not None:
            if ((self.show_answer == Quiz.ShowAnswers.ON_FAIL
                 and score <= self.threshold)
                    or (self.show_answer == Quiz.ShowAnswers.ON_PASS
                        and score >= self.threshold)):
                return score, incorrect_questions

        return score, []

    def compare_with_correct_answers(self, responses):
        correct_answers = self.correct_responses_task.responses
        correct = 0
        questions = eval(self.task_stage.json_schema).get('properties')
        incorrect_questions = []
        for key, answer in correct_answers.items():
            if str(responses.get(key)) == str(answer):
                correct += 1
            else:
                title = questions.get(key).get('title')
                if self.provide_answers:
                    incorrect_questions.append(f"{title}: {answer}")
                else:
                    incorrect_questions.append(title)

        len_correct_answers = len(correct_answers)
        unnecessary_keys = [Quiz.SCORE, Quiz.INCORRECT_QUESTIONS]
        for k in unnecessary_keys:
            if correct_answers.get(k):
                len_correct_answers -= 1

        correct_ratio = int(correct * 100 / len_correct_answers)
        return correct_ratio, "\n".join(incorrect_questions)
