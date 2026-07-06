from app.core.security import hash_password, verify_password
try:
    h = hash_password("12345678")
    print("Hashing works! Hash:", h)
    v = verify_password("12345678", h)
    print("Verification works! Match:", v)
except Exception as e:
    print("Hashing error:", type(e), str(e))
