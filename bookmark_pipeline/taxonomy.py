from __future__ import annotations

CANONICAL_TAXONOMY: dict[str, dict[str, list[str]]] = {
    'INFSEC': {
        'OSINT': ['SEARCH', 'SOCIAL_MEDIA', 'PEOPLE_SEARCH', 'CORPORATE', 'GEOINT'],
        'DFIR': ['ANDROID', 'IOS', 'WINDOWS', 'MEMORY', 'TOOLS'],
        'PENTEST': ['RECON', 'WEB', 'NETWORK', 'EXPLOITATION', 'PRIVESC'],
        'REDTEAM': [],
        'BLUETEAM': [],
        'MALWARE_RE': [],
        'APPSEC': [],
        'GRC': [],
        'CERTS': [],
        'CAREER': [],
    },
    'DEV': {
        'PYTHON': [],
        'WEBDEV': [],
        'PROGRAMMING': [],
        'NETWORKING': [],
        'LINUX': [],
        'DATABASES': [],
        'AI_ML': [],
        'OPEN_SOURCE': [],
        'GAMEDEV': [],
        'TOOLS': [],
    },
    'GAMING': {
        'ARPG': [],
        'MMO': [],
        'FPS': [],
        'TFT': [],
        'MINECRAFT': [],
        'STRATEGY': [],
        'GUIDES': [],
        'MODDING': [],
        'TOOLS': [],
        'COMMUNITIES': [],
    },
    'EDUCATION': {
        'UNIVERSITY': [],
        'COURSES': [],
        'RESEARCH': [],
        'PHILOSOPHY': [],
        'HISTORY': [],
        'ARTS': [],
        'GENEALOGY': [],
        'WRITING': [],
        'REFERENCE': [],
        'STUDY': [],
    },
    'CAREER': {
        'JOB_SEARCH': [],
        'INTERVIEWS': [],
        'PORTFOLIO': [],
        'NETWORKING': [],
        'TRAINING': [],
        'CERTIFICATIONS': [],
        'HIRING': [],
        'PRODUCTIVITY': [],
        'REMOTE_WORK': [],
        'GENERAL': [],
    },
    'MEDIA': {
        'MUSIC': [],
        'VIDEO': [],
        'STREAMING': [],
        'ARCHIVES': [],
        'BOOKS': [],
        'PODCASTS': [],
        'RADIO': [],
        'TV': [],
        'MOVIES': [],
        'GENERAL': [],
    },
    'PRIVACY': {
        'OPSEC': [],
        'ANONYMITY': [],
        'EMAIL': [],
        'BROWSERS': [],
        'TRACKING': [],
        'SECURE_COMMS': [],
        'DATA_REMOVAL': [],
        'GUIDES': [],
        'TOOLS': [],
        'GENERAL': [],
    },
    'RESEARCH': {
        'BALTIMORE': [],
        'MAPS': [],
        'ARCHIVES': [],
        'DATASETS': [],
        'ACADEMIC': [],
        'INVESTIGATIONS': [],
        'HISTORY': [],
        'SOCIETY': [],
        'POLITICS': [],
        'GENERAL': [],
    },
    'UTILITIES': {
        'SEARCH': [],
        'BOOKMARKLETS': [],
        'CHEATSHEETS': [],
        'CALCULATORS': [],
        'PRODUCTIVITY': [],
        'FILETOOLS': [],
        'WEBTOOLS': [],
        'AUTOMATION': [],
        'EMAIL': [],
        'GENERAL': [],
    },
    'PERSONAL': {
        'RECIPES': [],
        'SHOPPING': [],
        'QUOTES': [],
        'FANTASY_FOOTBALL': [],
        'HOBBIES': [],
        'COLLECTIONS': [],
        'HOME': [],
        'FITNESS': [],
        'FINANCE': [],
        'GENERAL': [],
    },
}


UNSORTED_CATEGORY = 'UNSORTED'
UNSORTED_SUBCATEGORY = 'UNSORTED'
UNSORTED_LEAF = ''


def validate_taxonomy_shape() -> None:
    if len(CANONICAL_TAXONOMY) > 10:
        raise ValueError('Too many top-level categories in taxonomy.')
    for category, subcategories in CANONICAL_TAXONOMY.items():
        if len(subcategories) > 10:
            raise ValueError(f'Too many subcategories under {category}.')
        for subcategory, leaves in subcategories.items():
            if len(leaves) > 5:
                raise ValueError(f'Too many leaves under {category}/{subcategory}.')


def classify_from_path(path: str) -> tuple[str, str, str] | None:
    parts = [part.strip().upper() for part in path.split('/') if part.strip()]
    for category in parts:
        if category not in CANONICAL_TAXONOMY:
            continue
        for subcategory in parts:
            if subcategory in CANONICAL_TAXONOMY[category]:
                leaves = CANONICAL_TAXONOMY[category][subcategory]
                for leaf in parts:
                    if leaf in leaves:
                        return category, subcategory, leaf
                return category, subcategory, ''
        return category, 'GENERAL', ''
    return None
