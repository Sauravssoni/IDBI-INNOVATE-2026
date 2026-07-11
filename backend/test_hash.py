from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
hash_str = "$argon2id$v=19$m=65536,t=3,p=4$YCzFGEMIIQRA6B3DGMO4Fw$q5Mbf8o/ZqtS8q4BayIH2KBToHHv1RLOTB332UHyrt0"
print(pwd_context.verify("VyaparPulseDemo2026!", hash_str))
