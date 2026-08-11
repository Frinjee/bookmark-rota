"""
Constants for detecting private/personal sites that should be excluded from
the public rotation pool.  Imported by both catalog.py and tagger.py to
avoid duplication.
"""
from __future__ import annotations

# Exact registered domains (matched against the result of domain_from_url).
PRIVATE_DOMAINS: frozenset[str] = frozenset({
    # Email providers
    'gmail.com',
    'mail.google.com',
    'protonmail.com',
    'proton.me',
    'outlook.com',
    'outlook.live.com',
    'mail.yahoo.com',
    'mail.aol.com',
    'hotmail.com',
    # Email tools / alias dashboards
    'app.addy.io',
    'tuta.com',
    # School / LMS portals
    'canvas.instructure.com',
    'panopto.com',
    'blackboard.com',
    'moodle.org',
    'brightspace.com',
    'ubalt.edu',
    'coursework.com',
    # Banking / Finance
    'chase.com',
    'wellsfargo.com',
    'bankofamerica.com',
    'citibank.com',
    'usaa.com',
    'schwab.com',
    'fidelity.com',
    'mint.com',
    'capitalone.com',
    'discover.com',
    'truist.com',
    'pnc.com',
    # Job boards / ATS portals
    'indeed.com',
    'glassdoor.com',
    'myworkdayjobs.com',
    'greenhouse.io',
    'lever.co',
    'smartrecruiters.com',
    'icims.com',
    'bamboohr.com',
    # Employer-specific ATS subdomains / job posting pages
    'taleo.net',
    'hrsmart.com',
    'trinethire.com',
    'hireology.com',
    'workat.doximity.com',
    # Personal account / dashboard subdomains (root domain stays PUBLIC)
    'app.hackthebox.com',
    'account.hackthebox.com',
})

# Substrings matched against the lowercased concatenation of title + url +
# folder_path.  Keep entries specific enough to avoid false positives.
PRIVATE_KEYWORDS: tuple[str, ...] = (
    # Email
    'gmail',
    'protonmail',
    'proton.me',
    'webmail',
    'tuta mail',
    # School portals
    'canvas',
    'panopto',
    'blackboard',
    'moodle',
    'brightspace',
    'ubalt',
    'my ubalt',
    'coursework',
    'omnissa',
    # Banking / Finance
    'chase.com',
    'wellsfargo',
    'bankofamerica',
    'usaa',
    'schwab',
    'fidelity',
    'myaccounts',
    'banking',
    'bank account',
    # Job boards / ATS — keyword signals for specific job postings
    'indeed.com',
    'glassdoor',
    'myworkdayjobs',
    'greenhouse.io',
    'lever.co',
    'job description',
    'job application',
    # Generic private markers (kept from original code)
    'password',
    'token',
    'key',
    'billing',
    'bank',
    'private',
    'vpn',
)

# Source folder path substrings (matched case-insensitively against source_path).
# Any bookmark whose folder path contains one of these strings is marked PRIVATE.
PRIVATE_FOLDERS: tuple[str, ...] = (
    # Personal job-hunt folders
    'job search',
    'jobs july',
    'portfolio site',
    # Email account shortcuts
    'e-mail',
    # School course-specific folders (portals, assignments, notes)
    'cyfi 330',
    'cyfi-330',
    'hist-205',
    'phil paper',
    # Personal browser pinned items (school portals, personal sites)
    'pins',
)
