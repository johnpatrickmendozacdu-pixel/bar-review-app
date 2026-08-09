# Certificate bundle for the SC e-Library

`elibrary.judiciary.gov.ph` serves an **incomplete TLS chain**: it presents a
valid GlobalSign EV certificate but omits the intermediate that links it to the
root. Standard verification therefore fails with:

    unable to verify the first certificate

## What's here

| File | What it is |
|---|---|
| `elibrary-leaf.pem` | The server's own certificate. Reference only — not used for verification. |
| `elibrary-intermediate.pem` | `GlobalSign GCC R3 EV TLS CA 2025`, the intermediate the server omits. Downloaded from the CA Issuers URL in the leaf's Authority Information Access extension. |
| `elibrary-chain.pem` | `certifi`'s full CA bundle **plus** the intermediate. This is what `verify=` points at. |

Verification remains genuine. The trust anchor is still GlobalSign Root CA R3
from certifi — we only supply a link the server forgot to send. The leaf is
**not** a trust anchor, which is why certificate renewal won't break us.

**Never replace this with `verify=False`.** That accepts any certificate from
any party, turning a cosmetic server misconfiguration into a real
man-in-the-middle vulnerability on a government source of legal truth.

## Refreshing

The intermediate expires **16 July 2027**. When ingest starts failing with a
TLS error:

```bash
# 1. Find the current intermediate URL from the live leaf
openssl s_client -showcerts -servername elibrary.judiciary.gov.ph \
  -connect elibrary.judiciary.gov.ph:443 </dev/null 2>/dev/null \
  | openssl x509 -outform PEM > certs/elibrary-leaf.pem
openssl x509 -in certs/elibrary-leaf.pem -noout -text | grep -A2 "Authority Information Access"

# 2. Download it and convert to PEM
curl -sS -o /tmp/inter.crt <the CA Issuers URL>
openssl x509 -inform DER -in /tmp/inter.crt -out certs/elibrary-intermediate.pem

# 3. Rebuild the bundle
cat "$(.venv/bin/python -c 'import certifi;print(certifi.where())')" \
    certs/elibrary-intermediate.pem > certs/elibrary-chain.pem

# 4. Verify
.venv/bin/python -c "import requests; print(requests.get('https://elibrary.judiciary.gov.ph/', verify='certs/elibrary-chain.pem').status_code)"
```

Expected: `200`.
