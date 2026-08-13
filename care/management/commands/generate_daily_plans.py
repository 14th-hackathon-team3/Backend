from django.core.management.base import BaseCommand
from care.models import Episode
from care.services import generate_daily_plan


class Command(BaseCommand):
    help = "모든 활성 episode에 대해 오늘의 AI 플랜을 생성한다 (매일 아침 7시 cron 실행용)"

    def handle(self, *args, **options):
        episodes = Episode.objects.filter(is_active=True)
        success, failed = 0, 0

        for episode in episodes:
            try:
                generate_daily_plan(episode)
                success += 1
            except ValueError as e:
                # daily_log가 없는 등 정상적인 스킵 사유
                self.stdout.write(f"[스킵] episode {episode.pk}: {e}")
                failed += 1
            except Exception as e:
                self.stderr.write(f"[에러] episode {episode.pk}: {e}")
                failed += 1

        self.stdout.write(self.style.SUCCESS(f"완료: 성공 {success}건, 스킵/실패 {failed}건"))