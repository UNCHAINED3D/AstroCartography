"""
Interpretation engine — the "why" behind the numbers.

Pure content + templating: given planets, angles and houses, produce plain-English
sentences a non-astrologer can understand. Kept separate from calculations so the
text can be reviewed/edited without touching the maths.
"""

from __future__ import annotations

# Per-planet flavour. Short, human, non-judgemental.
PLANET_MEANING: dict[str, str] = {
    "Sun": "identity, vitality and the core self",
    "Moon": "emotion, instinct, home and family feeling",
    "Mercury": "communication, learning and trade",
    "Venus": "love, beauty, pleasure and values",
    "Mars": "drive, action, desire and conflict",
    "Jupiter": "growth, luck, optimism and expansion",
    "Saturn": "structure, discipline, boundaries and duty",
    "Uranus": "freedom, surprise, rebellion and innovation",
    "Neptune": "imagination, spirituality and blur",
    "Pluto": "power, transformation and depth",
    "Chiron": "healing, wounding and teaching",
    "True Node": "destiny, growth direction and life path",
}

# The four angular lines and what living on each means.
ANGLE_MEANING: dict[str, str] = {
    "MC": "career, public reputation and life direction",
    "IC": "home, roots, family and private life",
    "ASC": "how you present yourself and are first seen",
    "DSC": "partnership, relationships and others",
}

# Natal house themes (1-indexed).
HOUSE_MEANING: dict[int, str] = {
    1: "self, appearance and new beginnings",
    2: "money, possessions and self-worth",
    3: "communication, siblings and short travel",
    4: "home, family and foundations",
    5: "creativity, romance and play",
    6: "work, health and daily routine",
    7: "partnership, marriage and open enemies",
    8: "shared resources, intimacy and transformation",
    9: "travel, higher learning and belief",
    10: "career, public life and achievement",
    11: "friends, groups and hopes",
    12: "subconscious, solitude and the hidden",
}

# Strength bands by distance in km from an ACG line.
def strength_from_distance(km: float) -> str:
    if km <= 120:
        return "strong"
    if km <= 400:
        return "moderate"
    return "light"


# Full interpretation library: 48 planet × angle combinations (12 planets ×
# 4 angles). Each entry is 3–5 plain-English sentences used by the panel when a
# location sits on (or near) the line. Falls back to the templated
# ``line_sentence`` builder below when a key is missing.
ACG_MEANINGS: dict[tuple[str, str], str] = {
    # ---------------- SUN ----------------
    ("Sun", "MC"): (
        "Your Sun on the Midheaven marks a place of destiny for your public life and vocation. "
        "Here the world is most likely to recognise your core identity, vitality and leadership. "
        "Careers where you can shine, create and be seen — politics, the arts, entrepreneurship — "
        "tend to flourish. This is a strong zone for building reputation and leaving a visible mark."
    ),
    ("Sun", "IC"): (
        "With the Sun on your Imum Coeli, home and family life become a stage for your self-expression. "
        "You are likely to feel most authentically 'you' in private, domestic settings here. "
        "Ancestry, roots and the people you live with nourish your identity. This is a grounding place "
        "where personal renewal happens away from the public eye."
    ),
    ("Sun", "ASC"): (
        "The Sun rising on your Ascendant makes this a place where you naturally step into the spotlight. "
        "Strangers read you as confident, warm and authoritative; first impressions favour you. "
        "It is excellent for travel, self-promotion and beginning new chapters of life. "
        "You tend to feel more alive and visible to others here than almost anywhere else."
    ),
    ("Sun", "DSC"): (
        "Your Sun on the Descendant draws significant people and partnerships into your path. "
        "Romantic and business relationships here often feel fated and illuminating. "
        "Others act as mirrors that reveal who you are. This is a prime zone for meeting a partner "
        "or a collaborator who helps you shine."
    ),
    # ---------------- MOON ----------------
    ("Moon", "MC"): (
        "The Moon on the Midheaven colours your public life with feeling, intuition and a nurturing touch. "
        "Careers in care, hospitality, food, psychology or the public eye can feel emotionally fulfilling. "
        "Your reputation here is sensitive and responsive to the moods of the collective. "
        "This is a place where emotion and vocation intertwine."
    ),
    ("Moon", "IC"): (
        "The Moon on your Imum Coeli makes home a deep emotional anchor. "
        "You may feel a powerful pull toward roots, family and a sense of belonging here. "
        "Domestic life is rich, changeable and deeply felt. This is one of the strongest places "
        "to settle, raise family or tend your inner world."
    ),
    ("Moon", "ASC"): (
        "With the Moon rising, others perceive you as empathetic, receptive and instinctively caring. "
        "Your emotional nature is on display and people feel comfortable opening up to you here. "
        "It favours nurturing roles and close, feeling-based connection. "
        "Moods and cycles tend to shape your experience of this place."
    ),
    ("Moon", "DSC"): (
        "The Moon on the Descendant brings emotionally significant relationships into your life. "
        "Partners and close others often play a mothering, supportive or changeable role. "
        "You may meet people who feel like family. This is a place where bonds are formed through "
        "shared feeling and mutual care."
    ),
    # ---------------- MERCURY ----------------
    ("Mercury", "MC"): (
        "Mercury on the Midheaven sharpens your public voice and professional communication. "
        "Careers in writing, teaching, trade, media or technology come naturally here. "
        "You are recognised for your intellect and facility with words. "
        "This is a strong zone for reputation built on ideas and information."
    ),
    ("Mercury", "IC"): (
        "With Mercury on your Imum Coeli, your inner life is busy with thought, study and conversation. "
        "Home may double as a study or workplace of the mind. "
        "You think clearly in private and value learning within the family. "
        "This is a good place to write, research or teach from home."
    ),
    ("Mercury", "ASC"): (
        "Mercury rising makes you quick-witted and verbally fluent in first encounters. "
        "People read you as clever, curious and communicative. "
        "It favours travel, study-abroad and any work involving language. "
        "Your mind is alert and expressive here."
    ),
    ("Mercury", "DSC"): (
        "Mercury on the Descendant attracts communicative, mentally agile partners and collaborators. "
        "Relationships here thrive on dialogue, shared ideas and constant exchange. "
        "You may meet a spouse or business ally through study or conversation. "
        "Intellectual rapport is the glue of your bonds in this zone."
    ),
    # ---------------- VENUS ----------------
    ("Venus", "MC"): (
        "Venus on the Midheaven graces your public life with charm, beauty and social grace. "
        "Careers in art, design, fashion, music or diplomacy can prosper here. "
        "You are liked and admired professionally, often attracting patronage. "
        "This is a place where love of beauty and professional success align."
    ),
    ("Venus", "IC"): (
        "With Venus on your Imum Coeli, home is a source of pleasure, harmony and beauty. "
        "You create a warm, aesthetic domestic sanctuary and value comfort deeply. "
        "Family relationships tend to be affectionate. This is among the most pleasant places "
        "to live and love."
    ),
    ("Venus", "ASC"): (
        "Venus rising makes you appear attractive, agreeable and socially graceful. "
        "First impressions are favourable and you draw people toward you effortlessly. "
        "It is excellent for romance, travel and the arts. "
        "You radiate charm and are generally well received here."
    ),
    ("Venus", "DSC"): (
        "Venus on the Descendant is a classic placement for meeting love and valued partnerships. "
        "Romantic and business relationships are warm, cooperative and pleasurable. "
        "You are likely to attract a partner who embodies beauty or harmony. "
        "This is one of the most relationship-friendly zones on the map."
    ),
    # ---------------- MARS ----------------
    ("Mars", "MC"): (
        "Mars on the Midheaven drives ambition, assertion and visibility in your career. "
        "You are recognised as a doer — competitive, energetic and unafraid to lead. "
        "Careers in sport, the military, engineering or enterprise suit this place. "
        "Success comes through bold, decisive action, though burnout is the risk to manage."
    ),
    ("Mars", "IC"): (
        "With Mars on your Imum Coeli, home life is active, sometimes turbulent and full of initiative. "
        "You may renovate, defend or energetically transform your domestic world. "
        "Family dynamics can be fiery but stimulating. This is a place to channel drive into "
        "building and protecting what you care about."
    ),
    ("Mars", "ASC"): (
        "Mars rising projects force, courage and raw vitality in first meetings. "
        "Others see you as bold, independent and perhaps a little combative. "
        "It favours physical activity, adventure and assertive new starts. "
        "You meet the world head-on here."
    ),
    ("Mars", "DSC"): (
        "Mars on the Descendant draws passionate, dynamic and sometimes confrontational partners. "
        "Relationships here are charged with desire and conflict in equal measure. "
        "You may meet a warrior-lover or a rival who becomes an ally. "
        "Intensity characterizes your one-to-one bonds in this zone."
    ),
    # ---------------- JUPITER ----------------
    ("Jupiter", "MC"): (
        "Jupiter on the Midheaven expands your public standing, reputation and professional luck. "
        "Careers in law, education, publishing, travel or philosophy flourish here. "
        "You are seen as wise, generous and trustworthy. "
        "This is one of the best lines for recognition, growth and worldly success."
    ),
    ("Jupiter", "IC"): (
        "With Jupiter on your Imum Coeli, home and family life are blessed with optimism and abundance. "
        "You may live spaciously, travel from home, or host generously. "
        "Roots feel fortunate and broadening. This is a warm, expansive place to settle and grow."
    ),
    ("Jupiter", "ASC"): (
        "Jupiter rising makes you appear buoyant, open and fortunate to others. "
        "First encounters go well and the world seems to smile on your ventures here. "
        "It favours long journeys, study and optimistic self-presentation. "
        "You readily attract good will."
    ),
    ("Jupiter", "DSC"): (
        "Jupiter on the Descendant brings beneficial, growth-oriented partnerships. "
        "You are likely to meet a mentor, spouse or ally who expands your horizons. "
        "Relationships here are generous and mutually enriching. "
        "This is a fortunate zone for marriage and collaboration."
    ),
    # ---------------- SATURN ----------------
    ("Saturn", "MC"): (
        "Saturn on the Midheaven marks a place of serious achievement and long-term professional structure. "
        "Careers demanding discipline, authority and endurance — law, government, engineering — are favoured. "
        "Recognition comes slowly but lasts. This is a place to build lasting status through hard work."
    ),
    ("Saturn", "IC"): (
        "With Saturn on your Imum Coeli, home life carries responsibility, structure and perhaps duty to family. "
        "You build solid, enduring foundations here, sometimes at personal cost. "
        "Roots are serious but dependable. This is a place to establish security through commitment."
    ),
    ("Saturn", "ASC"): (
        "Saturn rising lends you gravity, reserve and an aura of authority. "
        "Others take you seriously and may initially find you formal or cautious. "
        "It favours disciplined self-presentation and long-term plans. "
        "Maturity and reliability define your presence here."
    ),
    ("Saturn", "DSC"): (
        "Saturn on the Descendant draws committed, stabilizing partnerships — often with older or steadying figures. "
        "Relationships here are built on duty, loyalty and time-tested trust. "
        "You may meet a partner through work or tradition. "
        "This is a zone for enduring, if demanding, bonds."
    ),
    # ---------------- URANUS ----------------
    ("Uranus", "MC"): (
        "Uranus on the Midheaven electrifies your career with originality, disruption and sudden turns. "
        "Technology, science, activism or unconventional paths suit this place. "
        "Your public image is inventive and unpredictable. "
        "Expect breakthroughs and upheavals in equal measure — routine is the enemy here."
    ),
    ("Uranus", "IC"): (
        "With Uranus on your Imum Coeli, home life is unconventional, restless and freedom-seeking. "
        "You may move often, live unconventionally, or host an eccentric household. "
        "Roots are stimulating but unstable. This is a place for independence and reinvention at home."
    ),
    ("Uranus", "ASC"): (
        "Uranus rising makes you read as unique, electric and a little unpredictable. "
        "First impressions are striking and you resist being boxed in. "
        "It favours innovation, travel off the beaten path and sudden fresh starts. "
        "You radiate originality here."
    ),
    ("Uranus", "DSC"): (
        "Uranus on the Descendant attracts unconventional, freedom-loving partners and sudden relationship shifts. "
        "Bonds here are exciting but require space and surprise to survive. "
        "You may meet someone unexpected who changes your life. "
        "This is a zone of electrifying, non-traditional unions."
    ),
    # ---------------- NEPTUNE ----------------
    ("Neptune", "MC"): (
        "Neptune on the Midheaven dissolves boundaries around your public role, favouring art, music, film and healing. "
        "Your career may be inspired yet diffuse, with moments of glamour and confusion. "
        "Reputation here is poetic and elusive. This is a place to create from imagination, while guarding against illusion."
    ),
    ("Neptune", "IC"): (
        "With Neptune on your Imum Coeli, home is dreamy, spiritual and sometimes murky. "
        "You may idealise family or seek refuge in a secluded, artistic sanctuary. "
        "Roots are intuitive and porous. This is a place of imagination and solace, best with clear boundaries."
    ),
    ("Neptune", "ASC"): (
        "Neptune rising gives you a soft, mystical, impressionable first impression. "
        "Others may find you charismatic yet hard to pin down. "
        "It favours artistic, healing or spiritual self-expression. "
        "You channel a dreamlike quality here."
    ),
    ("Neptune", "DSC"): (
        "Neptune on the Descendant draws romantic, soulful and sometimes confusing partners. "
        "Relationships here are tinged with idealism, sacrifice or illusion. "
        "You may meet a muse or a mystery. This is a zone of deep, transcendent — and occasionally deceptive — bonds."
    ),
    # ---------------- PLUTO ----------------
    ("Pluto", "MC"): (
        "Pluto on the Midheaven concentrates power, transformation and intensity in your public life. "
        "Careers in psychology, research, finance or crisis leadership suit this place. "
        "Your reputation is formidable and regenerating. "
        "This is a zone of profound professional reinvention and influence."
    ),
    ("Pluto", "IC"): (
        "With Pluto on your Imum Coeli, home and family carry deep, transformative intensity. "
        "You may experience powerful endings and rebirths in your domestic world. "
        "Roots are profound and controlling yet regenerative. "
        "This is a place where the psyche is rebuilt from the foundations up."
    ),
    ("Pluto", "ASC"): (
        "Pluto rising projects magnetic, intense and somewhat formidable presence. "
        "Others sense power and depth in you immediately. "
        "It favours transformative self-reinvention and commanding first impressions. "
        "You meet the world with quiet, unstoppable force here."
    ),
    ("Pluto", "DSC"): (
        "Pluto on the Descendant draws magnetic, consuming and transformative partnerships. "
        "Relationships here are about power, healing and deep change. "
        "You may meet a partner who forever alters you. "
        "This is a zone of fated, regenerative bonds."
    ),
    # ---------------- CHIRON ----------------
    ("Chiron", "MC"): (
        "Chiron on the Midheaven channels wounded-healer energy into your vocation. "
        "Careers in teaching, medicine, counselling or mentorship can be profoundly meaningful here. "
        "Your public role often involves guiding others through pain. "
        "This is a place where professional life becomes a path of healing."
    ),
    ("Chiron", "IC"): (
        "With Chiron on your Imum Coeli, family and home carry old wounds alongside deep capacity to heal. "
        "You may revisit ancestral patterns and mend them here. "
        "Roots are tender but reparative. This is a place of domestic healing and quiet recovery."
    ),
    ("Chiron", "ASC"): (
        "Chiron rising gives you a vulnerable, teacherly first impression. "
        "Others sense both wound and wisdom in you. "
        "It favours helping roles and authentic self-presentation. "
        "You meet the world as a wounded healer here."
    ),
    ("Chiron", "DSC"): (
        "Chiron on the Descendant attracts relationships that are both wounding and deeply healing. "
        "Partners may be teachers or fellow travellers through pain. "
        "You meet people who help you integrate old hurts. "
        "This is a zone of relational medicine."
    ),
    # ---------------- TRUE NODE ----------------
    ("True Node", "MC"): (
        "The True Node on the Midheaven points your public life toward soul-level growth and destiny. "
        "Careers aligned with your life purpose feel fated and forward-moving here. "
        "You are recognised for following your path rather than your comfort. "
        "This is a place to step into your direction."
    ),
    ("True Node", "IC"): (
        "With the True Node on your Imum Coeli, home and family hold karmic lessons and growth. "
        "You may feel pulled toward roots that teach you about your path. "
        "Domestic life nudges your evolution. This is a place where the personal becomes meaningful."
    ),
    ("True Node", "ASC"): (
        "The True Node rising suggests this place is aligned with your life direction. "
        "First encounters and new beginnings here feel auspicious and growth-oriented. "
        "It favours forward movement and trusting the path. "
        "You step into destiny in this zone."
    ),
    ("True Node", "DSC"): (
        "The True Node on the Descendant draws relationships that advance your soul's growth. "
        "Partners here often feel like destined allies on your journey. "
        "You meet people who help you evolve. "
        "This is a place of karmic connection."
    ),
}

# Paran pair interpretations keyed by a frozenset of the two planets (order
# independent). Covers the most common and symbolically potent combinations.
ACG_PARAN_MEANINGS: dict[frozenset, str] = {
    frozenset({"Sun", "Moon"}): (
        "A Sun–Moon paran unites will and feeling: conscious purpose and instinct blend, "
        "supporting both leadership and emotional fulfilment in one place."
    ),
    frozenset({"Sun", "Venus"}): (
        "A Sun–Venus paran radiates warmth and charm; creativity and love reinforce one another, "
        "a favourable omen for romance and artistic recognition."
    ),
    frozenset({"Sun", "Mars"}): (
        "A Sun–Mars paran fuses identity with drive; vitality becomes action, "
        "amplifying courage, ambition and the will to win."
    ),
    frozenset({"Sun", "Jupiter"}): (
        "A Sun–Jupiter paran expands the self through fortune and wisdom; "
        "confidence meets opportunity, a classic signature of success."
    ),
    frozenset({"Sun", "Saturn"}): (
        "A Sun–Saturn paran tempers identity with discipline; "
        "enduring achievement is built through patience and responsibility."
    ),
    frozenset({"Sun", "Mercury"}): (
        "A Sun–Mercury paran links selfhood with expression; "
        "purpose finds its voice in communication, teaching and trade."
    ),
    frozenset({"Sun", "Uranus"}): (
        "A Sun–Uranus paran electrifies the personality; "
        "originality and independence surge, favouring breakthrough and rebellion."
    ),
    frozenset({"Moon", "Venus"}): (
        "A Moon–Venus paran blends feeling with affection; "
        "domestic and romantic happiness reinforce one another beautifully."
    ),
    frozenset({"Moon", "Jupiter"}): (
        "A Moon–Jupiter paran enlarges the emotional life; "
        "optimism and nurture combine, a warm, fortunate influence for home and family."
    ),
    frozenset({"Moon", "Neptune"}): (
        "A Moon–Neptune paran dissolves feeling into imagination; "
        "deeply spiritual and artistic, yet prone to illusion — bound by compassion."
    ),
    frozenset({"Moon", "Mars"}): (
        "A Moon–Mars paran fuses emotion with drive; "
        "passion runs hot, energising both protection of home and impulsive feeling."
    ),
    frozenset({"Venus", "Mars"}): (
        "A Venus–Mars paran is the archetype of attraction; "
        "love and desire meet, a potent placement for romance and creative passion."
    ),
    frozenset({"Venus", "Jupiter"}): (
        "A Venus–Jupiter paran multiplies pleasure and luck; "
        "relationships and finances expand warmly — a signature of good fortune in love."
    ),
    frozenset({"Venus", "Saturn"}): (
        "A Venus–Saturn paran grounds love in commitment; "
        "affection matures into loyalty and lasting, if sober, bonds."
    ),
    frozenset({"Mars", "Jupiter"}): (
        "A Mars–Jupiter paran fuels confident action; "
        "energy meets opportunity, excellent for enterprise, sport and bold ventures."
    ),
    frozenset({"Mars", "Saturn"}): (
        "A Mars–Saturn paran marries drive with structure; "
        "forceful yet disciplined, it builds through sustained, controlled effort."
    ),
    frozenset({"Mars", "Pluto"}): (
        "A Mars–Pluto paran concentrates will into power; "
        "intense and transformative, it forges relentless, regenerative action."
    ),
    frozenset({"Jupiter", "Saturn"}): (
        "A Jupiter–Saturn paran balances expansion with limits; "
        "growth gains form and durability — the architect's signature."
    ),
    frozenset({"Jupiter", "Uranus"}): (
        "A Jupiter–Uranus paran sparks inspired leaps; "
        "luck arrives through innovation, favouring sudden, liberating breakthroughs."
    ),
    frozenset({"Mercury", "Venus"}): (
        "A Mercury–Venus paran charms the mind; "
        "communication becomes affectionate and persuasive, sweetening social ties."
    ),
    frozenset({"Mercury", "Jupiter"}): (
        "A Mercury–Jupiter paran broadens the intellect; "
        "teaching, publishing and far-reaching ideas flourish here."
    ),
    frozenset({"Saturn", "Uranus"}): (
        "A Saturn–Uranus paran bridges order and revolution; "
        "it builds lasting structures from sudden insight — reform with roots."
    ),
    frozenset({"Saturn", "Neptune"}): (
        "A Saturn–Neptune paran meets discipline with dream; "
        "idealism gains form through patient, devotional craft."
    ),
    frozenset({"Uranus", "Neptune"}): (
        "A Uranus–Neptune paran fuses rebellion with vision; "
        "awakening and imagination blend, a signature of generational idealism."
    ),
    frozenset({"Sun", "Pluto"}): (
        "A Sun–Pluto paran concentrates destiny into power; "
        "the self is transformed through intensity, forging unstoppable purpose."
    ),
    frozenset({"Moon", "Pluto"}): (
        "A Moon–Pluto paran deepens feeling into obsession and healing; "
        "emotional life becomes a crucible of transformation."
    ),
    frozenset({"Venus", "Neptune"}): (
        "A Venus–Neptune paran romanticises love into the ideal; "
        "profoundly poetic and artistic, yet inviting illusion in relationships."
    ),
    frozenset({"Jupiter", "Neptune"}): (
        "A Jupiter–Neptune paran expands the imagination; "
        "visionary faith and artistic largesse, best anchored in reality."
    ),
    frozenset({"Mars", "Uranus"}): (
        "A Mars–Uranus paran electrifies action; "
        "sudden, brilliant, rebellious energy — brilliant yet volatile."
    ),
    frozenset({"Mercury", "Uranus"}): (
        "A Mercury–Uranus paran sparks genius; "
        "quick, original thinking favours invention and sudden insight."
    ),
}


def line_sentence(planet: str, angle: str, km: float) -> str:
    p = PLANET_MEANING.get(planet, planet.lower())
    a = ANGLE_MEANING.get(angle, angle)
    band = strength_from_distance(km)
    where = {
        "MC": "your public/career life",
        "IC": "your home and private life",
        "ASC": "your self and how others see you",
        "DSC": "your relationships and partnerships",
    }.get(angle, a)
    # Prefer the full interpretation library when available.
    full = ACG_MEANINGS.get((planet, angle))
    if full:
        if band == "strong":
            lead = f"Right on your {planet} {angle} line, this place means: "
        else:
            lead = f"About {round(km)} km from your {planet} {angle} line, this area means: "
        return lead + full
    if band == "strong":
        dist = f"right on your {planet} {angle} line"
    else:
        dist = f"about {round(km)} km from your {planet} {angle} line"
    return (
        f"{dist}: {p.capitalize()} expresses through {where} "
        f"({a}). This is a {band} influence here."
    )


def relocation_sentence(
    asc_sign: str,
    planet_houses: list[dict],
) -> str:
    parts = [f"Your Ascendant becomes {asc_sign} here."]
    # Highlight up to three meaningful planet moves.
    notable = [ph for ph in planet_houses if ph.get("notable")]
    for ph in notable[:3]:
        theme = HOUSE_MEANING.get(ph["house"], "")
        parts.append(
            f"{ph['name']} moves into your {ph['house']} house of {theme}."
        )
    return " ".join(parts)


def paran_pair_meaning(planet_a: str, planet_b: str) -> str | None:
    """Return the interpretation for a paran planet pair, if known."""
    return ACG_PARAN_MEANINGS.get(frozenset({planet_a, planet_b}))


def paran_sentence(
    planet_a: str, circle_a: str, planet_b: str, circle_b: str
) -> str:
    a = PLANET_MEANING.get(planet_a, planet_a.lower())
    b = PLANET_MEANING.get(planet_b, planet_b.lower())
    extra = paran_pair_meaning(planet_a, planet_b)
    base = (
        f"{planet_a} {circle_a} × {planet_b} {circle_b}: {a} blends with {b} "
        f"where these two lines meet."
    )
    if extra:
        return base + " " + extra
    return base


def house_region_sentence(house: int) -> str:
    theme = HOUSE_MEANING.get(house, "life")
    return f"This spot falls in your {house}th-house region of {theme}."
