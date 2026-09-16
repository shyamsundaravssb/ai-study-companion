import json
import time
import urllib.request
from fastapi import HTTPException
from jose import jwt
from app.core.config import settings

_jwks_cache = None
_jwks_cache_time = 0
CACHE_TTL = 3600  # 1 hour

def get_jwks(force_refresh=False):
    global _jwks_cache, _jwks_cache_time
    
    if not force_refresh and _jwks_cache and (time.time() - _jwks_cache_time) < CACHE_TTL:
        return _jwks_cache
        
    url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            jwks = json.loads(response.read().decode())
            _jwks_cache = jwks
            _jwks_cache_time = time.time()
            return jwks
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch JWKS: {str(e)}")

def verify_jwt_token(token: str) -> dict:
    try:
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        
        if not kid:
            raise HTTPException(status_code=401, detail="Invalid token: missing kid in header")
            
        jwks = get_jwks()
        
        # Try to find the matching key
        signing_key = next((key for key in jwks.get('keys', []) if key['kid'] == kid), None)
                
        # If kid not found in cache, might be rotated. Refetch and try once more.
        if not signing_key:
            jwks = get_jwks(force_refresh=True)
            signing_key = next((key for key in jwks.get('keys', []) if key['kid'] == kid), None)
                    
        if not signing_key:
            raise HTTPException(status_code=401, detail="Invalid token: Key ID not found in JWKS")
            
        # Verify the token
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["ES256", "RS256"], 
            options={"verify_aud": False}
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")
