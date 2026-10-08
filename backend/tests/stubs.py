# Fake sentence_transformers (torch doesn't fit in this sandbox)
import sys, types
st = types.ModuleType("sentence_transformers")
class SentenceTransformer:
    def __init__(self, *a, **k): pass
    def encode(self, text, convert_to_tensor=False):
        import numpy as np
        v = np.zeros(384); v[len(text) % 384] = 1; v[0] = 1
        return v
class util:
    @staticmethod
    def cos_sim(a, b):
        import numpy as np
        a, b = np.array(a), np.array(b)
        return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))
st.SentenceTransformer = SentenceTransformer; st.util = util
sys.modules["sentence_transformers"] = st
