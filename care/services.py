from django.conf import settings
from openai import OpenAI
from .models import DailyLog, VoiceMemo, Episode, RecoveryPlan, Todo
import json
from datetime import date, timedelta
from django.db import transaction
from pydantic import BaseModel, Field
from groups.models import Membership, Group
from typing import Optional
from rest_framework.exceptions import NotFound

openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

WEEKDAY_KR = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']

def upload_and_transcribe(daily_log: DailyLog, audio_file) -> VoiceMemo:
    voice_memo = VoiceMemo.objects.create(
        daily_log=daily_log,
        audio_file=audio_file,
        status=VoiceMemo.Status.PENDING,
    )

    try:
        with voice_memo.audio_file.open('rb') as f:
            transcript = openai_client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",  
                file=f,
                language="ko",
            )
        voice_memo.transcript_text = transcript.text
        voice_memo.status = VoiceMemo.Status.DONE
        voice_memo.save()
        
        # 텍스트 변환 성공했으면 daily_log 자동 채움 시도
        try:
            extracted = extract_fields_from_voice(transcript.text)
            apply_extracted_fields_to_log(daily_log, extracted)
        except Exception as e:
            # 자동 채움 실패해도 전사 결과 자체는 살려둠 (필수 기능 아님)
            print(f"필드 자동 추출 실패: {e}")
            
    except Exception as e:
        voice_memo.status = VoiceMemo.Status.FAILED
        voice_memo.save()
        print(f"음성 변환 실패: {e}")

    return voice_memo

# ─────────────────────────────────────────
# 1. 데이터 수집 + 결측 방어
# ─────────────────────────────────────────

def get_recent_logs_summary(episode: Episode) -> list[dict]:
    """최근 7일 daily_log를 가져오되, null 필드는 JSON에서 아예 제외 (없는 값을 지어내지 않도록)"""
    logs = DailyLog.objects.filter(episode=episode).order_by('-log_date')[:7]

    summary = []
    for log in logs:
        entry = {"date": str(log.log_date)}
        # None이 아닌 필드만 포함
        field_map = {
            "emotion": log.emotion,
            "sleep_hours": float(log.sleep_hours) if log.sleep_hours is not None else None,
            "pain_score": log.pain_score,
            "pain_area": log.pain_area or None,
            "breastfeeding": log.breastfeeding,
            "activity_hours": float(log.activity_hours) if log.activity_hours is not None else None,
            "activity_type": log.activity_type or None,
            "breast_milk_amount": log.breast_milk_amount,
            "breastfeeding_pain_score": log.breastfeeding_pain_score,
            "skin_self_score": log.skin_self_score,
            "skin_symptom_tags": log.skin_symptom_tags,
            "hair_loss_status": log.hair_loss_status,
            "pelvic_floor_symptoms": log.pelvic_floor_symptoms,
            "diet": log.diet,
            "memo": log.memo or None,
        }
        for key, value in field_map.items():
            if value is not None and value != "":
                entry[key] = value

        voice_texts = [vm.transcript_text for vm in log.voice_memos.filter(status='done') if vm.transcript_text]
        if voice_texts:
            entry["voice_transcript"] = " ".join(voice_texts)

        # 비공개로 지정된 "필드 이름 리스트"를 그대로 들고 있음 (예: ["emotion", "memo"])
        entry["_private_fields"] = log.private_fields or []

        summary.append(entry)

    return summary


def get_public_logs_summary(episode: Episode) -> list[dict]:
    """가족용 프롬프트용 — 산모가 비공개 지정한 필드만 골라서 제거"""
    full_summary = get_recent_logs_summary(episode)
    public_summary = []
    for entry in full_summary:
        entry = dict(entry)
        private_field_names = entry.pop("_private_fields", [])  # 마킹용 키는 무조건 제거

        for field_name in private_field_names:
            entry.pop(field_name, None)

        # memo를 비공개로 잡으면 음성메모(voice_transcript)도 같이 가려주는 게 자연스러움
        if "memo" in private_field_names:
            entry.pop("voice_transcript", None)

        public_summary.append(entry)
    return public_summary


def get_primary_caregivers(episode: Episode) -> list[Membership]:
    """주 보호자(is_primary=True)만 가져옴 — 담당자 배정은 주 보호자 중에서만"""
    try:
        group = Group.objects.get(owner_user=episode.user)
    except Group.DoesNotExist:
        return []

    return list(
        Membership.objects.filter(
            group=group, role=Membership.Role.MEMBER, is_primary=True, is_active=True
        )
    )


def build_caregiver_info(caregivers: list[Membership]) -> list[dict]:
    return [
        {
            "membership_id": c.pk,
            "relation": c.relation,
            "is_cohabiting": c.is_cohabiting,
            "available_time": c.available_time,
        }
        for c in caregivers
    ]


# ─────────────────────────────────────────
# 2. 출력 스키마
# ─────────────────────────────────────────

class MotherTodo(BaseModel):
    content: str
    reason: str

class MotherPlanOutput(BaseModel):
    ai_summary: str = Field(description="거시적 관점 2~3문장, 의학적 진단명 금지")
    bottleneck: str = Field(description="오늘의 핵심 병목 한 줄. [원인]으로 인한 [위험요소] 방지 및 [핵심액션] 형태")
    reasoning: str = Field(description="bottleneck을 그렇게 판단한 근거 1~2문장")
    tomorrow_goal: str = Field(description="내일의 회복 목표 한 줄")
    mother_todos: list[MotherTodo] = Field(description="정확히 3개, 비용 발생 금지, 하루 안에 완료 가능, 행동 단위")


class FamilyTodo(BaseModel):
    content: str
    reason: str
    assignee_membership_id: int = Field(description="입력으로 제공된 membership_id 중 하나여야 함")

class FamilyPlanOutput(BaseModel):
    family_todos: list[FamilyTodo] = Field(description="정확히 10개, 카테고리 중복 금지, 보호자별 균형 배정")


# ─────────────────────────────────────────
# 3. 프롬프트 빌더
# ─────────────────────────────────────────
def build_pain_area_text(episode: Episode) -> str:
    """initial_pain_areas(리스트) + custom text를 사람이 읽을 수 있는 문자열로 변환"""
    areas = episode.initial_pain_areas or []
    if not areas:
        return "기록 없음"

    labels = []
    for area in areas:
        if area == Episode.PainArea.CUSTOM:
            custom_text = episode.initial_pain_area_custom_text
            labels.append(custom_text if custom_text else "직접 입력(내용 없음)")
        else:
            # choice value -> 한글 label 변환 (예: 'perineum' -> '회음부')
            labels.append(Episode.PainArea(area).label)

    return ", ".join(labels)

def build_mother_prompt(episode: Episode, logs_summary: list[dict]) -> str:
    today = date.today()
    weekday_str = WEEKDAY_KR[today.weekday()]
    has_enough_data = len(logs_summary) >= 6

    trend_note = (
        "충분한 기록이 쌓여있으니 최근 며칠간의 변화 흐름(추세)을 짚어주세요."
        if has_enough_data else
        f"아직 기록이 {len(logs_summary)}일치뿐이라 뚜렷한 추세 판단은 어렵습니다. "
        "무리하게 추세를 단정하지 말고, 최근 기록된 상태 위주로만 요약해주세요."
    )
    
    pain_area_text = build_pain_area_text(episode)

    return f"""당신은 10년 차 베테랑 산후 회복 케어 코디네이터입니다.
의학적 진단이 아니라, 산모의 최근 생활 기록을 바탕으로 오늘 하루의 셀프케어 플랜을 제안합니다.

[오늘 날짜] {today.isoformat()} ({weekday_str})

[산모 상태 프로필]
- 출산 방식: {episode.get_delivery_type_display()}
- 산후 주차: {episode.postpartum_week}주차
- 초기 통증 부위: {pain_area_text}
- 회복 장소: {episode.recovery_location or '기록 없음'}

[최근 {len(logs_summary)}일간 기록]
{json.dumps(logs_summary, ensure_ascii=False, indent=2)}

[데이터 관련 안내]
{trend_note}

[작성 규칙]
1. ai_summary: 수면/통증/식사/감정의 변화 흐름을 2~3문장으로. "~한 것으로 보여요", "~하는 흐름이에요" 톤 유지.
   의학적 진단명(산후우울증, 감염증 등) 절대 사용 금지. 변화 없는 항목은 "안정적으로 유지되고 있다"고 표현.
2. bottleneck: 우선순위 판단 기준은 수면 > 통증 > 감정 > 식사 > 활동량 순으로, 가장 신경 써야 할 요인 하나만 한 줄로.
3. reasoning: bottleneck을 그렇게 판단한 근거를 1~2문장으로. (참고: UI에서는 버튼을 눌러야 노출되는 상세 설명이므로 bottleneck보다 조금 더 설명적으로 써도 됨)
4. tomorrow_goal: 내일 지향할 목표 한 줄.
5. mother_todos: 정확히 3개. 비용 발생 금지, 하루 안에 끝낼 수 있는 구체적 행동 단위로.
   - content 좋은 예: "침대에서 일어나기 전 5분간 가벼운 스트레칭 하기"
   - content 나쁜 예: "충분히 휴식하기" (너무 추상적)
   - reason은 산모에게 직접 말을 건네듯 부드러운 구어체로, "~해요/~것 같아요/~줄 거예요" 톤으로 한 문장 작성.
     명사형 종결("~위해.", "~해서.")은 금지.
     reason 좋은 예: "지금 몸에 필요한 영양을 든든하게 채워줄 수 있어요."
     reason 나쁜 예: "충분한 영양 섭취로 회복을 지원하기 위해."
"""


def build_family_prompt(episode: Episode, bottleneck: str, public_logs_summary: list[dict], caregiver_info: list[dict]) -> str:
    today = date.today()
    weekday_str = WEEKDAY_KR[today.weekday()]
    valid_ids = [c["membership_id"] for c in caregiver_info]

    return f"""당신은 산후 회복 케어 코디네이터입니다.
아래 산모의 상태와, 곁에서 돕는 주 보호자들의 현실적인 가용 환경을 고려해
오늘 하루 보호자들이 할 일 10개를 설계합니다.

[오늘 날짜] {today.isoformat()} ({weekday_str})

[산모 상태 요약]
- 산후 주차: {episode.postpartum_week}주차
- 오늘의 병목: {bottleneck}

[최근 기록 (민감 정보 제외)]
{json.dumps(public_logs_summary, ensure_ascii=False, indent=2)}

[지원 가능한 주 보호자 목록 (총 {len(caregiver_info)}명)]
{json.dumps(caregiver_info, ensure_ascii=False, indent=2)}
※ assignee_membership_id는 반드시 위 목록에 있는 membership_id({valid_ids}) 중 하나여야 합니다.
   목록에 없는 값을 만들어내지 마세요.

[family_todos 구성 규칙]
- 정확히 10개, 비슷하거나 겹치는 항목 생성 금지
- 카테고리를 최소 1개 이상씩 고려: 수면 지원 / 식사 지원 / 수분 섭취 지원 / 가사 부담 감소 /
  정서적 지지 / 신생아 케어 분담 / 이동·외출 지원 / 환경 정리
- 배정 규칙:
  a) available_time에 맞지 않는 시간대의 업무를 배정하지 마세요 (예: 저녁에만 가능한 보호자에게 오전 업무 배정 금지)
  b) is_cohabiting=true인 보호자에게 가사/밀착 케어 비중을 더 높게
  c) 보호자가 여러 명이면 10개를 균형 있게 분산 배정 (한 명에게 몰아주지 말 것)
- "집안일 돕기"처럼 모호하게 쓰지 말고 "오후 2시경 거실 환기 10분 하고 청소기 돌리기"처럼 즉시 실행 가능한 구체적 문장으로
- 단순 심부름이 아니라 오늘의 병목({bottleneck}) 해결에 실질적으로 기여하는 케어여야 함
- 산모의 민감한 감정/메모 내용이 있었더라도 절대 직접 언급하거나 유추 가능하게 쓰지 마세요
  (예: "산모가 우울해하니 위로해주기" 금지 → "산모가 좋아하는 따뜻한 차 타주며 가벼운 대화 나누기"처럼 우회 표현)
- reason은 보호자에게 말을 건네듯 부드러운 구어체로, "~해요/~것 같아요/~줄 거예요" 톤으로 한 문장 작성.
  명사형 종결("~위해.", "~해서.")은 금지.
"""


# ─────────────────────────────────────────
# 4. 후검증
# ─────────────────────────────────────────

def validate_mother_output(result: MotherPlanOutput):
    if len(result.mother_todos) != 3:
        raise ValueError(f"mother_todos는 3개여야 하는데 {len(result.mother_todos)}개 반환됨")


def validate_family_output(result: FamilyPlanOutput, valid_ids: list[int]):
    if len(result.family_todos) != 10:
        raise ValueError(f"family_todos는 10개여야 하는데 {len(result.family_todos)}개 반환됨")
    for t in result.family_todos:
        if t.assignee_membership_id not in valid_ids:
            raise ValueError(f"존재하지 않는 assignee_membership_id: {t.assignee_membership_id}")


# ─────────────────────────────────────────
# 5. 메인 함수
# ─────────────────────────────────────────

def generate_daily_plan(episode: Episode) -> RecoveryPlan:
    logs_summary = get_recent_logs_summary(episode)
    if not logs_summary:
        raise ValueError("분석할 daily_log 데이터가 없습니다. 오늘 기록을 먼저 남겨주세요.")

    # ── 1차 호출: 산모용 (private 포함) ──
    mother_prompt = build_mother_prompt(episode, logs_summary)
    mother_completion = openai_client.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "당신은 산후 케어 플랜 생성 도우미입니다."},
            {"role": "user", "content": mother_prompt},
        ],
        response_format=MotherPlanOutput,
    )
    mother_result: MotherPlanOutput = mother_completion.choices[0].message.parsed
    validate_mother_output(mother_result)

    with transaction.atomic():
        plan, _ = RecoveryPlan.objects.update_or_create(
            episode=episode,
            plan_date=date.today(),
            defaults={
                "ai_summary": mother_result.ai_summary,
                "bottleneck": mother_result.bottleneck,
                "reasoning": mother_result.reasoning,
                "tomorrow_goal": mother_result.tomorrow_goal,
            }
        )
        plan.todos.filter(status=Todo.Status.DRAFT).delete()

        for idx, t in enumerate(mother_result.mother_todos):
            Todo.objects.create(
                recovery_plan=plan, content=t.content, reason=t.reason,
                order_index=idx, assignee_membership=None,
            )

    # ── 2차 호출: 가족용 (private 제외) ──
    caregivers = get_primary_caregivers(episode)
    if not caregivers:
        # 보호자가 없으면 가족용 파트는 생성하지 않고 여기서 종료
        return plan

    caregiver_info = build_caregiver_info(caregivers)
    public_logs_summary = get_public_logs_summary(episode)
    family_prompt = build_family_prompt(episode, mother_result.bottleneck, public_logs_summary, caregiver_info)

    family_completion = openai_client.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "당신은 산후 케어 가족 할 일 배정 도우미입니다."},
            {"role": "user", "content": family_prompt},
        ],
        response_format=FamilyPlanOutput,
    )
    family_result: FamilyPlanOutput = family_completion.choices[0].message.parsed
    valid_ids = [c["membership_id"] for c in caregiver_info]
    validate_family_output(family_result, valid_ids)

    with transaction.atomic():
        for idx, t in enumerate(family_result.family_todos):
            Todo.objects.create(
                recovery_plan=plan, content=t.content, reason=t.reason,
                order_index=idx,
                assignee_membership_id=t.assignee_membership_id,
            )

    return plan

def calculate_week_trend(episode: Episode) -> dict:
    """최근 7일 데이터를 그래프용 배열 + 위험 배너 문구로 정리"""
    logs = list(
        DailyLog.objects.filter(episode=episode).order_by('log_date')[:7]
    )

    dates, sleep_values, pain_values, emotion_values = [], [], [], []
    for log in logs:
        dates.append(str(log.log_date))
        sleep_values.append(float(log.sleep_hours) if log.sleep_hours is not None else None)
        pain_values.append(log.pain_score)
        emotion_values.append(log.emotion)

    banners = []

    def trend_banner(values: list, label: str, direction_down_msg: str, direction_up_msg: str, threshold_ratio: float | None = None, threshold_abs: float | None = None):
        # None 제외하고 최근 3일 vs 직전 3일 비교
        clean = [(i, v) for i, v in enumerate(values) if v is not None]
        if len(clean) < 6:
            return  # 데이터 부족하면 배너 생성 안 함 (억지 판단 방지)

        recent_vals = [v for i, v in clean[-3:]]
        prev_vals = [v for i, v in clean[-6:-3]]
        if len(recent_vals) < 3 or len(prev_vals) < 3:
            return

        recent_avg = sum(recent_vals) / len(recent_vals)
        prev_avg = sum(prev_vals) / len(prev_vals)

        if prev_avg == 0:
            return

        diff = recent_avg - prev_avg
        ratio = diff / prev_avg

        # 기준치 미달인 경우 triggered = False 되서 banners 리스트에 아무것도 append 되지 않음!!

        triggered = False
        if threshold_ratio is not None and abs(ratio) >= threshold_ratio:
            triggered = True
        if threshold_abs is not None and abs(diff) >= threshold_abs:
            triggered = True

        if triggered:
            msg = direction_down_msg if diff < 0 else direction_up_msg
            banners.append({
                "type": label,
                "message": msg,
                "recent_avg": round(recent_avg, 1),
                "prev_avg": round(prev_avg, 1),
            })

    # 수면 ±15% 이상
    trend_banner(
        sleep_values, "sleep",
        direction_down_msg="최근 수면시간이 감소하고 있어요",
        direction_up_msg="최근 수면시간이 늘어나고 있어요",
        threshold_ratio=0.15,
    )

    # 통증 ±1점 이상
    trend_banner(
        pain_values, "pain",
        direction_down_msg="통증이 완화되고 있어요",
        direction_up_msg="통증이 심해지고 있어요",
        threshold_abs=1,
    )

    return {
        "dates": dates,
        "sleep": sleep_values,
        "pain": pain_values,
        "emotion": emotion_values,
        "banners": banners,
    }
    
#음성 메모-> daily_log 자동 채움

class ExtractedDailyLogFields(BaseModel):
    emotion: Optional[str] = Field(None, description="happy/angry/low_energy/sad/depressed/confused/calm/moody/irritated/worried/active 중 하나. 언급 없으면 null")
    sleep_hours: Optional[float] = Field(None, description="수면 시간(시간 단위, 소수 가능). 언급 없으면 null")
    pain_score: Optional[int] = Field(None, description="통증 강도 1~5. 언급 없으면 null")
    pain_area: Optional[str] = Field(None, description="통증 부위(자유텍스트). 언급 없으면 null")
    activity_hours: Optional[float] = Field(None, description="활동 시간. 언급 없으면 null")
    activity_type: Optional[str] = Field(None, description="활동 종류(예: 산책). 언급 없으면 null")
    memo_summary: Optional[str] = Field(None, description="위 구조화 필드로 안 잡히는 나머지 내용을 1문장으로 요약. 없으면 null")


def extract_fields_from_voice(transcript_text: str) -> ExtractedDailyLogFields:
    completion = openai_client.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "당신은 산모의 음성 기록에서 구조화된 정보를 추출하는 도우미입니다."},
            {"role": "user", "content": f"""
다음은 산모가 오늘 상태에 대해 말한 음성 기록입니다. 언급된 내용만 추출하고,
언급되지 않은 항목은 반드시 null로 두세요. 없는 정보를 추측해서 채우지 마세요.

[음성 기록 텍스트]
{transcript_text}
"""},
        ],
        response_format=ExtractedDailyLogFields,
    )
    return completion.choices[0].message.parsed


EMOTION_VALID_VALUES = [c.value for c in DailyLog.Emotion]


def apply_extracted_fields_to_log(daily_log: DailyLog, extracted: ExtractedDailyLogFields):
    """AI가 음성에서 값을 찾아낸 필드만 덮어씀 (기존 값 유무와 무관하게 최신 상태로 갱신)"""
    updated_fields = []

    if extracted.emotion in EMOTION_VALID_VALUES:
        daily_log.emotion = extracted.emotion
        updated_fields.append('emotion')

    if extracted.sleep_hours is not None:
        daily_log.sleep_hours = extracted.sleep_hours
        updated_fields.append('sleep_hours')

    if extracted.pain_score is not None and 1 <= extracted.pain_score <= 5: # 통증 강도 혹시 몰라서 1~5로 강제
        daily_log.pain_score = extracted.pain_score
        updated_fields.append('pain_score')

    if extracted.pain_area:
        daily_log.pain_area = extracted.pain_area
        updated_fields.append('pain_area')

    if extracted.activity_hours is not None:
        daily_log.activity_hours = extracted.activity_hours
        updated_fields.append('activity_hours')

    if extracted.activity_type:
        daily_log.activity_type = extracted.activity_type
        updated_fields.append('activity_type')
        
        
    # memo는 덮어쓰지 않고 이어붙임 (기존 텍스트 입력 메모 보존)
    if extracted.memo_summary:
        daily_log.memo = f"{daily_log.memo}\n{extracted.memo_summary}".strip() if daily_log.memo else extracted.memo_summary
        updated_fields.append('memo')

    if updated_fields:
        daily_log.save(update_fields=updated_fields)

    return updated_fields

def get_episode_and_membership(user):
    """
    로그인한 유저가 산모(owner)든 보호자(member)든 관계없이
    그 유저가 속한 그룹의 episode와 membership을 함께 반환.
    """
    membership = (
        Membership.objects
        .filter(user=user, is_active=True)
        .order_by('-joined_at')
        .first()
    )
    if not membership:
        raise NotFound("가입된 그룹이 없습니다.")

    episode = (
        Episode.objects
        .filter(user=membership.group.owner_user, is_active=True)
        .order_by('-created_at')
        .first()
    )
    if not episode:
        raise NotFound("진행 중인 episode가 없습니다.")

    return episode, membership