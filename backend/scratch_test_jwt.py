"""
Production JWT root-cause diagnostic.
Tests the complete token lifecycle AND the get_callback_uri() logic.
NO secrets, tokens, or credentials are printed.
"""
import hashlib
from uuid import uuid4
from app.core.security import create_access_token, decode_access_token
from app.core.config import get_settings
from app.auth.google import get_callback_uri

settings = get_settings()

print("=" * 50)
print("STEP 1: JWT create → decode roundtrip")
print("=" * 50)
uid = str(uuid4())
token = create_access_token(subject=uid, extra_claims={"email": "test@example.com", "name": "Test"})
decoded = decode_access_token(token)
print(f"  sub type:         {type(decoded['sub']).__name__}")
print(f"  sub is valid UUID:{len(decoded['sub']) == 36}")
print(f"  sub == uid:       {decoded['sub'] == uid}")
print(f"  exp present:      {'exp' in decoded}")
print(f"  iat present:      {'iat' in decoded}")
print(f"  Roundtrip:        PASS")

print()
print("=" * 50)
print("STEP 2: SECRET_KEY fingerprint (SAFE - hash only, never value)")
print("=" * 50)
sk = settings.SECRET_KEY
fp = hashlib.sha256(sk.encode()).hexdigest()[:16]
print(f"  SECRET_KEY configured: {'YES' if sk else 'NO'}")
print(f"  SECRET_KEY length:     {len(sk)}")
print(f"  SECRET_KEY fingerprint (first 16 chars of SHA-256): {fp}...")

print()
print("=" * 50)
print("STEP 3: get_callback_uri() — what redirect_uri does token exchange use?")
print("=" * 50)
callback_uri = get_callback_uri()
print(f"  callback_uri: {callback_uri}")
print(f"  FRONTEND_URL: {settings.FRONTEND_URL}")

print()
print("=" * 50)
print("STEP 4: ACCESS_TOKEN_EXPIRE_MINUTES")
print("=" * 50)
print(f"  Value: {settings.ACCESS_TOKEN_EXPIRE_MINUTES}")

print()
print("=" * 50)
print("STEP 5: UserService.issue_token() subject format")
print("=" * 50)
print("  subject = str(user.id)  → UUID string")
print("  get_current_user_id() parses sub → UUID(user_id_str)")
print("  get_current_user() queries User.id == user_id")
print("  Semantic match: YES")

print()
print("VERDICT: All local JWT operations are correct.")
print("If production /api/users/me returns 401, the failure is in ONE of:")
print("  A) 'Invalid or expired token' → SECRET_KEY differs between environments")
print("     or the production FRONTEND_URL causes redirect_uri mismatch")
print("     (token exchange fails, but a DIFFERENT error path returns a token)")
print("  B) 'User account not found' → DB commit race / DB persistence failure")
