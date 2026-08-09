"""
Offline spelling autocorrect for fingerspelled words.

Fingerspelling is error-prone (a missed or misread letter gives "wnt" for
"want"), so we correct each spelled word against a built-in frequency list of
common English words using a Norvig-style edit-distance corrector. No network,
no heavy dependencies — everything is local.

Only fingerspelled words are corrected; recognized whole-word signs (Hello,
I Love You, ...) are trusted as-is.
"""

import re
from collections import Counter
from pathlib import Path

# A compact frequency-ranked list of common English words. Ranked roughly by
# usage frequency so the corrector prefers common words. Bundled so the app
# works on any machine (not reliant on a system dictionary).
_COMMON_WORDS = """
the be to of and a in that have i it for not on with he as you do at this but his
by from they we say her she or an will my one all would there their what so up out
if about who get which go me when make can like time no just him know take people
into year your good some could them see other than then now look only come its over
think also back after use two how our work first well way even new want because any
these give day most us is are was were been has had did yes ok okay please thanks
thank sorry hello hi bye help name my me you your friend father mother deaf learn
meet tell pen eat drink water food home school love happy sad good morning night
today tomorrow here where why nice fine great cool right left stop wait more less
big small hot cold open close read write speak listen understand repeat again slow
fast easy hard true false maybe sure done ready begin end start finish call ask
answer question word letter sentence family people person man woman child boy girl
""".split()


def _seed_counter():
    # Give higher weight to earlier (more common) words so ties break sensibly.
    c = Counter()
    n = len(_COMMON_WORDS)
    for i, w in enumerate(_COMMON_WORDS):
        c[w.lower()] += (n - i)  # earlier word -> higher count
    return c


class AutoCorrector:
    def __init__(self, extra_words=None):
        self._words = _seed_counter()
        # Optionally enrich with a system dictionary if present (adds coverage
        # for rarer words; kept at weight 1 so common words still win).
        for path in ("/usr/share/dict/words",):
            p = Path(path)
            if p.exists():
                try:
                    for line in p.read_text(errors="ignore").splitlines():
                        w = line.strip().lower()
                        if w.isalpha() and w not in self._words:
                            self._words[w] += 1
                except Exception:
                    pass
        for w in (extra_words or []):
            self._words[w.lower()] += 10_000  # domain words are always valid

    # ---- Norvig corrector ------------------------------------------------
    def _known(self, words):
        return {w for w in words if w in self._words}

    @staticmethod
    def _edits1(word):
        letters = "abcdefghijklmnopqrstuvwxyz"
        splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
        deletes = [L + R[1:] for L, R in splits if R]
        transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R) > 1]
        replaces = [L + c + R[1:] for L, R in splits if R for c in letters]
        inserts = [L + c + R for L, R in splits for c in letters]
        return set(deletes + transposes + replaces + inserts)

    def _edits2(self, word):
        return {e2 for e1 in self._edits1(word) for e2 in self._edits1(e1)}

    def correct(self, word: str) -> str:
        """Return the best correction for a single spelled word."""
        if not word or not word.isalpha():
            return word
        lw = word.lower()
        # already a known word -> keep original casing
        if lw in self._words:
            return word
        candidates = (self._known([lw])
                      or self._known(self._edits1(lw))
                      or self._known(self._edits2(lw))
                      or [lw])
        best = max(candidates, key=lambda w: self._words.get(w, 0))
        # preserve all-caps style used while fingerspelling
        return best.upper() if word.isupper() else best
