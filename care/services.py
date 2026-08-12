from django.conf import settings
from openai import OpenAI
from .models import DailyLog, VoiceMemo

openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)


def upload_and_transcribe(daily_log: DailyLog, audio_file) -> VoiceMemo:
    voice_memo = VoiceMemo.objects.create(
        daily_log=daily_log,
        audio_file=audio_file,
        status=VoiceMemo.Status.PENDING,
    )

    try:
        with voice_memo.audio_file.open('rb') as f:
            transcript = openai_client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",  # 예산 넉넉하면 gpt-4o-transcribe로 교체
                file=f,
                language="ko",
            )
        voice_memo.transcript_text = transcript.text
        voice_memo.status = VoiceMemo.Status.DONE
    except Exception as e:
        voice_memo.status = VoiceMemo.Status.FAILED
        print(f"음성 변환 실패: {e}")

    voice_memo.save()
    return voice_memo