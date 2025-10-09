#!/usr/bin/env python3
import json
from urllib.request import Request, urlopen

DOMAIN = "dev-tlzrol0zsxw40ujx.us.auth0.com"
CLIENT_ID = "GGLemeiKL6MfXD7Hy4L4mtz8WNIhRtkS"
CLIENT_SECRET = "zXcdPIQRAM9iHzABZtcfaN_2iICW4pfuoyUChIcVDF5488ejtyKG_U_PyWj9kpJT"

request = Request(
    f"https://{DOMAIN}/oauth/token",
    data=json.dumps({
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "audience": f"https://{DOMAIN}/api/v2/",
        "grant_type": "client_credentials"
    }).encode('utf-8'),
    headers={"Content-Type": "application/json"},
    method='POST'
)

with urlopen(request) as response:
    print(json.loads(response.read().decode('utf-8'))["access_token"])
