from collections import defaultdict
from datetime import date, datetime, timedelta, timezone


LEVEL_ORDER = {"beginner": 0, "intermediate": 1, "advanced": 2}
STATUS_CATEGORY_POINTS = {
    "enrolled": 15,
    "in_progress": 30,
    "completed": 40,
}


def _as_utc_datetime(value):
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time(), tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            return _as_utc_datetime(datetime.fromisoformat(value.replace("Z", "+00:00")))
        except ValueError:
            return None
    return None


def _timestamp(value):
    parsed = _as_utc_datetime(value)
    return parsed.timestamp() if parsed is not None else float("-inf")


def _recent_bonus(created_at, now):
    created = _as_utc_datetime(created_at)
    if created is None:
        return 0

    age = now - created
    if age < timedelta(days=30):
        return 10
    if age <= timedelta(days=90):
        return 5
    return 0


def _popularity_points(enrollment_count, maximum_enrollment_count):
    if maximum_enrollment_count <= 0:
        return 0
    return 20 * enrollment_count / maximum_enrollment_count


def _format_score(score):
    rounded_score = round(float(min(score, 100)), 2)
    return int(rounded_score) if rounded_score.is_integer() else rounded_score


def _join_reasons(reasons):
    if not reasons:
        return "Aucune règle de personnalisation applicable."
    if len(reasons) == 1:
        return f"{reasons[0]}."
    if len(reasons) == 2:
        return f"{reasons[0]} et {reasons[1]}."
    return f"{', '.join(reasons[:-1])} et {reasons[-1]}."


def _recommendation_payload(course, score, reasons):
    return {
        "course_id": course["id"],
        "title": course["title"],
        "category": course["category"],
        "level": course["level"],
        "enrollment_count": int(course.get("enrollment_count", 0)),
        "score": _format_score(score),
        "reason": _join_reasons(reasons),
    }


def _cold_start_recommendations(courses, limit, maximum_enrollment_count):
    ordered_courses = sorted(
        courses,
        key=lambda course: (
            -int(course.get("enrollment_count", 0)),
            0 if course.get("level") == "beginner" else 1,
            -_timestamp(course.get("created_at")),
            int(course["id"]),
        ),
    )

    recommendations = []
    for course in ordered_courses[:limit]:
        popularity = _popularity_points(
            int(course.get("enrollment_count", 0)),
            maximum_enrollment_count,
        )
        reasons = ["classement de démarrage selon les inscriptions"]
        if course.get("level") == "beginner":
            reasons.append("niveau débutant privilégié en cas d’égalité")
        recommendations.append(_recommendation_payload(course, popularity, reasons))
    return recommendations


def build_recommendations(courses, history, limit=5, now=None):
    """Score available courses using explicit business rules."""
    if not history:
        maximum_enrollment_count = max(
            (int(course.get("enrollment_count", 0)) for course in courses),
            default=0,
        )
        return True, _cold_start_recommendations(
            courses,
            limit,
            maximum_enrollment_count,
        )

    current_time = now or datetime.now(timezone.utc)
    current_time = _as_utc_datetime(current_time)

    history_by_category = defaultdict(list)
    completed_levels = set()
    for enrollment in history:
        history_by_category[enrollment.get("category")].append(enrollment)
        if enrollment.get("status") == "completed":
            completed_levels.add(enrollment.get("level"))

    maximum_enrollment_count = max(
        (int(course.get("enrollment_count", 0)) for course in courses),
        default=0,
    )
    scored_courses = []

    for course in courses:
        category_history = history_by_category.get(course.get("category"), [])
        category_points = max(
            (
                STATUS_CATEGORY_POINTS.get(enrollment.get("status"), 0)
                for enrollment in category_history
            ),
            default=0,
        )

        course_level = LEVEL_ORDER.get(course.get("level"))
        next_level = any(
            course_level is not None
            and LEVEL_ORDER.get(enrollment.get("level")) is not None
            and course_level == LEVEL_ORDER[enrollment["level"]] + 1
            for enrollment in category_history
        )
        same_completed_level = course.get("level") in completed_levels
        popularity = _popularity_points(
            int(course.get("enrollment_count", 0)),
            maximum_enrollment_count,
        )
        recent_points = _recent_bonus(course.get("created_at"), current_time)

        score = 0
        reasons = []
        if category_points:
            category_reason = {
                40: "même catégorie qu’une formation terminée",
                30: "même catégorie qu’une formation en cours",
                15: "même catégorie qu’une inscription existante",
            }
            reasons.append(category_reason[category_points])
            score += category_points
        if next_level:
            score += 25
            reasons.append("niveau immédiatement supérieur dans la même catégorie")
        if same_completed_level:
            score += 10
            reasons.append("même niveau qu’une formation terminée")
        if popularity:
            score += popularity
            reasons.append("formation populaire")
        if recent_points:
            score += recent_points
            if recent_points == 10:
                reasons.append("formation créée depuis moins de 30 jours")
            else:
                reasons.append("formation créée entre 30 et 90 jours")

        scored_courses.append(
            {
                "course": course,
                "score": min(score, 100),
                "enrollment_count": int(course.get("enrollment_count", 0)),
                "created_at": _timestamp(course.get("created_at")),
                "reasons": reasons,
            }
        )

    scored_courses.sort(
        key=lambda item: (
            -item["score"],
            -item["enrollment_count"],
            -item["created_at"],
            int(item["course"]["id"]),
        )
    )

    return False, [
        _recommendation_payload(item["course"], item["score"], item["reasons"])
        for item in scored_courses[:limit]
    ]
