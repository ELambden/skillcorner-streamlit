from __future__ import annotations

EVENT_TYPE_LABELS = {
    "player_possession": "In-possession action",
    "off_ball_run": "Off-ball movement",
    "passing_option": "Available passing lane",
    "on_ball_engagement": "Defensive pressure",
}

IN_POSSESSION_PHASE_LABELS = {
    "build_up": "Build-up",
    "chaotic": "Broken play",
    "create": "Chance creation",
    "direct": "Direct attack",
    "finish": "Final-third attack",
    "quick_break": "Counter-attack",
    "set_play": "Set play",
    "transition": "Transition attack",
}

OUT_OF_POSSESSION_PHASE_LABELS = {
    "chaotic": "Broken defensive shape",
    "defending_direct": "Defending direct play",
    "defending_quick_break": "Defending counter-attack",
    "defending_set_play": "Defending set play",
    "defending_transition": "Defensive transition",
    "high_block": "High block",
    "medium_block": "Mid block",
    "low_block": "Low block",
}

RUN_SUBTYPE_LABELS = {
    "behind": "Run in behind",
    "coming_short": "Coming short",
    "cross_receiver": "Cross receiver",
    "dropping_off": "Dropping off",
    "overlap": "Overlap",
    "pulling_half_space": "Pulling half-space",
    "pulling_wide": "Pulling wide",
    "run_ahead_of_the_ball": "Ahead of the ball",
    "support": "Support run",
    "underlap": "Underlap",
}

SPEED_BAND_LABELS = {
    "walking": "Walking",
    "jogging": "Jogging",
    "running": "Running",
    "hsr": "High-speed run",
    "sprinting": "Sprint",
    "sprint": "Sprint",
}

TRACKING_STATUS_LABELS = {
    "available": "Full tracking available",
    "lfs-pointer": "Tracking stored in Git LFS",
    "missing": "Tracking file missing",
}

SCORE_LABELS = {
    "profile_score": "Overall profile",
    "athletic_load_score": "Athletic load",
    "sprint_threat_score": "Sprint threat",
    "off_ball_threat_score": "Off-ball threat",
    "passing_progression_score": "Passing progression",
    "reliability_score": "Reliability",
}

METRIC_LABELS = {
    "total_metersperminute_full_all": "Metres per minute",
    "running_distance_full_all": "Running distance",
    "hsr_distance_full_all": "High-speed running distance",
    "hsr_count_full_all": "High-speed runs",
    "sprint_distance_full_all": "Sprint distance",
    "sprint_count_full_all": "Sprints",
    "hi_count_full_all": "High-intensity actions",
    "medaccel_count_full_all": "Medium accelerations",
    "meddecel_count_full_all": "Medium decelerations",
    "explacceltosprint_count_full_all": "Explosive accelerations into sprint",
    "psv99": "Peak speed",
    "offballrun_count_p30tip": "Off-ball movements per 30 possession minutes",
    "offballrun_count_dangerous_p30tip": "Dangerous off-ball movements",
    "offballrun_count_penaltyarea_p30tip": "Penalty-area off-ball movements",
    "offballrun_count_targeted_p30tip": "Off-ball movements targeted by a pass",
    "offballrun_count_received_p30tip": "Off-ball movements that receive the ball",
    "offballrun_count_shotwithin10s_p30tip": "Off-ball movements before a shot",
    "pass_count_linebreak_completed_p30tip": "Completed line-breaking passes",
    "pass_count_torun_completed_p30tip": "Completed passes into runs",
    "pass_count_dangerous_completed_p30tip": "Completed dangerous passes",
    "pass_count_difficultpass_attempted_p30tip": "Difficult pass attempts",
    "pass_avgxpass_attempted": "Average pass difficulty",
    "pass_count_shotwithin10s_p30tip": "Passes before a shot",
    "pass_pct_completed": "Pass completion rate",
}

ARCHETYPE_DEFINITIONS = {
    "Depth runner": {
        "short": "A vertical mover who repeatedly threatens space beyond or across the defensive line.",
        "meaning": "These players combine strong off-ball movement scores with high sprint threat. The profile points to runners who stretch compact blocks, give ball carriers forward options, and force defenders to turn toward their own goal.",
        "prioritised": [
            "Off-ball movement volume and dangerous off-ball movements",
            "High-speed running and sprint volume",
            "Penalty-area, ahead-of-ball and targeted movement when available",
        ],
        "rule": "Assigned when off-ball threat is at least 72 and sprint threat is at least 65 within the player's position group.",
        "tactical_use": "Best interpreted as a depth, channel or blind-side running profile rather than a pure finishing profile.",
    },
    "Connector creator": {
        "short": "A link player who turns movement into useful receiving and passing options.",
        "meaning": "These players rate strongly for passing progression while still offering above-average off-ball threat. The combination suggests players who do not only run into space, but also help possessions continue after receiving or offering a passing lane.",
        "prioritised": [
            "Completed line-breaking passes and passes into runs",
            "Dangerous completed passes and pass difficulty",
            "Off-ball threat high enough to show useful movement away from the ball",
        ],
        "rule": "Assigned when passing progression is at least 72 and off-ball threat is at least 58.",
        "tactical_use": "Useful for identifying interiors, wide creators and forwards who knit attacking moves together.",
    },
    "High-output carrier": {
        "short": "A high-load player whose value is driven by repeat running and physical coverage.",
        "meaning": "These players stand out for athletic load without also grading as high-end progression passers. The signal is physical influence: covering ground, repeating high-intensity actions and supporting transitions.",
        "prioritised": [
            "Metres per minute and running distance",
            "High-speed running and high-intensity action count",
            "Acceleration and deceleration volume",
        ],
        "rule": "Assigned when athletic load is at least 72 and passing progression is below 58.",
        "tactical_use": "Useful for identifying full-backs, wide players and midfielders who sustain team intensity.",
    },
    "Progression hub": {
        "short": "A possession progressor who advances attacks mainly through passing choices.",
        "meaning": "These players separate through the passing progression score even when their off-ball movement profile is not high enough for connector status. They are more ball-use hubs than constant runners.",
        "prioritised": [
            "Completed line-breaking passes",
            "Completed passes into runners",
            "Dangerous completed passes and above-average pass difficulty",
        ],
        "rule": "Assigned when passing progression is at least 72 and the stronger connector-creator condition is not met.",
        "tactical_use": "Useful for spotting players who can move a team through pressure or feed runners ahead of them.",
    },
    "Box-movement threat": {
        "short": "A movement threat whose value appears around dangerous and penalty-area actions.",
        "meaning": "These players have high off-ball threat but do not pair it with enough sprint threat to become depth runners. The interpretation is more about timing, receiving zones and box occupation than raw speed.",
        "prioritised": [
            "Dangerous off-ball movements",
            "Penalty-area off-ball movements",
            "Movements targeted, received or followed by a shot",
        ],
        "rule": "Assigned when off-ball threat is at least 72 and higher-priority depth/connector rules are not met.",
        "tactical_use": "Useful for identifying players who arrive in scoring zones or offer close-range combination options.",
    },
    "Balanced contributor": {
        "short": "A rounded profile without one dominant standout family of actions.",
        "meaning": "These players do not trigger the specialist thresholds. That does not mean low quality: it often means the player contributes across multiple areas, has limited minutes, or sits closer to the positional average in the selected sample.",
        "prioritised": [
            "No single specialist score crosses the classification threshold",
            "Overall profile score still rewards broad contribution",
            "Reliability adjusts for the amount of playing-time evidence",
        ],
        "rule": "Assigned when none of the specialist archetype rules are met.",
        "tactical_use": "Useful as a baseline group for comparing specialists against more rounded squad players.",
    },
}


def label_value(value: object, labels: dict[str, str]) -> str:
    text = "" if value is None else str(value)
    return labels.get(text, text.replace("_", " ").title())


def event_label(value: object) -> str:
    return label_value(value, EVENT_TYPE_LABELS)


def phase_label(value: object) -> str:
    return label_value(value, IN_POSSESSION_PHASE_LABELS)


def defensive_phase_label(value: object) -> str:
    return label_value(value, OUT_OF_POSSESSION_PHASE_LABELS)


def tracking_label(value: object) -> str:
    return label_value(value, TRACKING_STATUS_LABELS)


def run_subtype_label(value: object) -> str:
    return label_value(value, RUN_SUBTYPE_LABELS)


def speed_band_label(value: object) -> str:
    return label_value(value, SPEED_BAND_LABELS)


def metric_label(value: object) -> str:
    return label_value(value, METRIC_LABELS | SCORE_LABELS)
