"""F7 Owner's Weekly Hindi Voice Briefing (Req 22).

At the configured weekly schedule we build a Hindi script covering:

* the rating change week-over-week,
* the top improving + top declining Aspect,
* new Changepoints,
* the open P1/P2 complaint count, and
* one recommended action.

Every number comes from computed PahadPulse metrics (the shared analytics panel
+ the Sentinel service). The LLM adapter is used only for phrasing with the
template fallback otherwise (Req 22.5). The script is converted to speech of at
most 60 seconds via the TTS adapter (stub/placeholder offline, Req 22.3) and the
audio + script text are sent to opted-in owners through the WhatsApp mock
(Req 22.4).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from app.adapters.llm import LLMClient, get_llm_client
from app.adapters.voice import (
    MAX_BRIEFING_SECONDS,
    SpeechArtifact,
    TextToSpeech,
    estimate_speech_seconds,
    get_tts,
)
from app.adapters.whatsapp import WhatsAppGateway, get_default_gateway
from app.models.review import Aspect, SentimentLabel
from app.services.market_radar.analytics_dataset import (
    HOME_PROPERTY_ID,
    MentionObservation,
    generate_observations,
    property_name,
)
from app.services.market_radar.trends import _week_start

# Hindi aspect labels for the script (numbers remain computed metrics).
_ASPECT_HI: dict[str, str] = {
    "Food": "खाना",
    "Room": "कमरा",
    "Housekeeping": "हाउसकीपिंग",
    "Staff": "स्टाफ़",
    "Location": "स्थान",
    "Service": "सेवा",
    "Value_for_Money": "कीमत",
    "Cleanliness": "सफ़ाई",
    "Booking_Experience": "बुकिंग",
}


@dataclass
class BriefingMetrics:
    """The computed numbers that populate the Hindi script (Req 22.5)."""

    week_rating: float
    prev_week_rating: float
    rating_change: float
    top_improving_aspect: str | None
    top_improving_delta: float
    top_declining_aspect: str | None
    top_declining_delta: float
    new_changepoints: int
    open_p1_p2: int
    recommended_action: str

    def to_dict(self) -> dict:
        return {
            "week_rating": round(self.week_rating, 2),
            "prev_week_rating": round(self.prev_week_rating, 2),
            "rating_change": round(self.rating_change, 2),
            "top_improving_aspect": self.top_improving_aspect,
            "top_improving_delta": round(self.top_improving_delta, 3),
            "top_declining_aspect": self.top_declining_aspect,
            "top_declining_delta": round(self.top_declining_delta, 3),
            "new_changepoints": self.new_changepoints,
            "open_p1_p2": self.open_p1_p2,
            "recommended_action": self.recommended_action,
        }


@dataclass
class Briefing:
    """A generated weekly voice briefing."""

    property_id: str
    property_name: str
    week_of: str
    language: str
    script: str
    metrics: BriefingMetrics
    estimated_seconds: float
    within_cap: bool
    template_generated: bool
    audio_is_placeholder: bool
    audio_note: str | None
    delivered_to: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "property_id": self.property_id,
            "property_name": self.property_name,
            "week_of": self.week_of,
            "language": self.language,
            "script": self.script,
            "metrics": self.metrics.to_dict(),
            "estimated_seconds": self.estimated_seconds,
            "max_seconds": MAX_BRIEFING_SECONDS,
            "within_cap": self.within_cap,
            "template_generated": self.template_generated,
            "audio_is_placeholder": self.audio_is_placeholder,
            "audio_note": self.audio_note,
            "delivered_to": self.delivered_to,
        }


class BriefingGenerator:
    """Build + deliver the owner's weekly Hindi voice briefing (Req 22)."""

    def __init__(
        self,
        observations: tuple[MentionObservation, ...] | None = None,
        home_property_id: str = HOME_PROPERTY_ID,
        llm: LLMClient | None = None,
        tts: TextToSpeech | None = None,
        gateway: WhatsAppGateway | None = None,
    ) -> None:
        self._obs = observations if observations is not None else generate_observations()
        self._home = home_property_id
        self._llm = llm or get_llm_client()
        self._tts = tts or get_tts()
        self._gateway = gateway or get_default_gateway()

    def _week_rating(self, week_start: date) -> tuple[float, int]:
        """Mean score (1..5) for the home property in the given week."""
        labels: list[int] = []
        for o in self._obs:
            if o.property_id != self._home:
                continue
            if _week_start(o.date) != week_start:
                continue
            labels.append(1 if o.label is SentimentLabel.POSITIVE else 0)
        if not labels:
            return 0.0, 0
        p = sum(labels) / len(labels)
        return 1.0 + 4.0 * p, len(labels)

    def _aspect_week_share(self, aspect: Aspect, week_start: date) -> float | None:
        pos = tot = 0
        for o in self._obs:
            if o.property_id != self._home or o.aspect is not aspect:
                continue
            if _week_start(o.date) != week_start:
                continue
            tot += 1
            if o.label is SentimentLabel.POSITIVE:
                pos += 1
        return (pos / tot) if tot else None

    def compute_metrics(
        self, as_of: date | None = None, open_p1_p2: int = 0, new_changepoints: int = 0
    ) -> BriefingMetrics:
        latest = max((o.date for o in self._obs), default=date.today())
        as_of = as_of or latest
        this_week = _week_start(as_of)
        last_week = this_week - timedelta(days=7)

        week_rating, _ = self._week_rating(this_week)
        prev_rating, _ = self._week_rating(last_week)
        rating_change = week_rating - prev_rating

        best_aspect = worst_aspect = None
        best_delta = -1e9
        worst_delta = 1e9
        for aspect in Aspect:
            cur = self._aspect_week_share(aspect, this_week)
            prev = self._aspect_week_share(aspect, last_week)
            if cur is None or prev is None:
                continue
            delta = cur - prev
            if delta > best_delta:
                best_delta, best_aspect = delta, aspect.value
            if delta < worst_delta:
                worst_delta, worst_aspect = delta, aspect.value

        action = self._recommend_action(worst_aspect)
        return BriefingMetrics(
            week_rating=week_rating,
            prev_week_rating=prev_rating,
            rating_change=rating_change,
            top_improving_aspect=best_aspect,
            top_improving_delta=max(0.0, best_delta) if best_aspect else 0.0,
            top_declining_aspect=worst_aspect,
            top_declining_delta=worst_delta if worst_aspect else 0.0,
            new_changepoints=new_changepoints,
            open_p1_p2=open_p1_p2,
            recommended_action=action,
        )

    def _recommend_action(self, declining_aspect: str | None) -> str:
        if not declining_aspect:
            return "इस सप्ताह सेवा की गुणवत्ता पर ध्यान बनाए रखें।"
        label = _ASPECT_HI.get(declining_aspect, declining_aspect)
        return f"इस सप्ताह {label} पर टीम के साथ समीक्षा बैठक करें।"

    def _build_script(self, metrics: BriefingMetrics, prop_name: str) -> str:
        change_word = "बढ़ी" if metrics.rating_change >= 0 else "घटी"
        imp_key = metrics.top_improving_aspect or ""
        dec_key = metrics.top_declining_aspect or ""
        imp = _ASPECT_HI.get(imp_key, imp_key or "कोई")
        dec = _ASPECT_HI.get(dec_key, dec_key or "कोई")
        return (
            f"नमस्ते! {prop_name} की साप्ताहिक रिपोर्ट। "
            f"इस सप्ताह रेटिंग {metrics.week_rating:.1f} रही, जो पिछले सप्ताह से "
            f"{abs(metrics.rating_change):.1f} अंक {change_word}। "
            f"सबसे बेहतर पहलू {imp} रहा और सबसे कमज़ोर पहलू {dec}। "
            f"इस सप्ताह {metrics.new_changepoints} नए बदलाव बिंदु मिले। "
            f"{metrics.open_p1_p2} गंभीर (P1/P2) शिकायतें अभी खुली हैं। "
            f"सुझाव: {metrics.recommended_action}"
        )

    def generate(
        self,
        *,
        as_of: date | None = None,
        open_p1_p2: int = 0,
        new_changepoints: int = 0,
        opted_in_owners: list[str] | None = None,
        deliver: bool = True,
    ) -> Briefing:
        metrics = self.compute_metrics(
            as_of=as_of, open_p1_p2=open_p1_p2, new_changepoints=new_changepoints
        )
        prop_name = property_name(self._home)
        script = self._build_script(metrics, prop_name)

        # LLM only polishes phrasing; template fallback otherwise (Req 22.5).
        response = self._llm.generate(
            "Polish this Hindi weekly owner briefing script; keep every number.",
            context={"script": script},
        )
        template_generated = response.template_generated

        # Trim to the 60s cap if needed by dropping the least-critical sentence.
        estimated = estimate_speech_seconds(script)
        if estimated > MAX_BRIEFING_SECONDS:
            parts = script.split("। ")
            while (
                estimate_speech_seconds("। ".join(parts)) > MAX_BRIEFING_SECONDS
                and len(parts) > 3
            ):
                parts.pop(-2)  # keep greeting + action
            script = "। ".join(parts)
            estimated = estimate_speech_seconds(script)

        artifact: SpeechArtifact = self._tts.synthesize(script, language="hi")

        week_of = _week_start(as_of or max((o.date for o in self._obs), default=date.today()))
        delivered: list[str] = []
        if deliver and opted_in_owners:
            for owner in opted_in_owners:
                self._gateway.send(
                    owner,
                    f"🔊 PahadPulse साप्ताहिक ऑडियो ब्रीफ़िंग ({prop_name})\n"
                    f"[audio {artifact.engine}, ~{artifact.estimated_seconds}s]\n\n{script}",
                )
                delivered.append(owner)

        return Briefing(
            property_id=self._home,
            property_name=prop_name,
            week_of=week_of.isoformat(),
            language="hi",
            script=script,
            metrics=metrics,
            estimated_seconds=artifact.estimated_seconds,
            within_cap=artifact.estimated_seconds <= MAX_BRIEFING_SECONDS,
            template_generated=template_generated,
            audio_is_placeholder=artifact.is_placeholder,
            audio_note=artifact.note,
            delivered_to=delivered,
        )
