"""Public Schulnetz constants.

The mobile client id and the PWA host are identical across every Schulnetz
instance (the per-school API base URL is supplied per request, not here) and
neither is a secret, so they ship as defaults — SchulwareAPI runs with no
Schulnetz env configured. Set the matching environment variable only to override
for a non-standard deployment.
"""

DEFAULT_SCHULNETZ_CLIENT_ID = "ppyybShnMerHdtBQ"
DEFAULT_SCHULNETZ_WEB_BASE_URL = "https://schulnetz.web.app"
