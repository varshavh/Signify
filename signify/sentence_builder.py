"""
Sentence-building logic with temporal debouncing.

A raw per-frame prediction stream is noisy. This class waits until one label
has been the top prediction for a run of consecutive frames (and clears the
"cooldown" only after the hand leaves / the sign changes) before committing it
as a word. That turns flickery detections into a clean, editable sentence.
"""

from collections import deque, Counter


class SentenceBuilder:
    def __init__(self, stability=10, min_confidence=0.5, cooldown_frames=8):
        # stability: frames a label must dominate before it's committed
        # cooldown_frames: empty/other frames needed before the SAME word can repeat
        self.stability = stability
        self.min_confidence = min_confidence
        self.cooldown_frames = cooldown_frames

        self._recent = deque(maxlen=stability)
        self._words = []
        self._last_committed = None
        self._empty_streak = 0

    # ---- live feed -------------------------------------------------------
    def update(self, label, score):
        """Feed one frame's top prediction (label may be None). Returns the
        newly committed word this frame, or None."""
        if label is None or score < self.min_confidence:
            self._recent.append(None)
            self._empty_streak += 1
            if self._empty_streak >= self.cooldown_frames:
                self._last_committed = None  # allow same word again after a pause
            return None

        self._empty_streak = 0
        self._recent.append(label)
        if len(self._recent) < self.stability:
            return None

        winner, count = Counter(self._recent).most_common(1)[0]
        if winner is not None and count >= int(0.8 * self.stability):
            if winner != self._last_committed:
                self._words.append(winner)
                self._last_committed = winner
                return winner
        return None

    # ---- editing ---------------------------------------------------------
    def add_space(self):
        # spaces are represented by an explicit marker word
        if self._words and self._words[-1] != " ":
            self._words.append(" ")

    def backspace(self):
        if self._words:
            self._words.pop()
        self._last_committed = None

    def clear(self):
        self._words.clear()
        self._recent.clear()
        self._last_committed = None
        self._empty_streak = 0

    def add_word(self, word):
        """Manually append a word (e.g. from a quick-add button)."""
        self._words.append(word)
        self._last_committed = word

    # ---- output ----------------------------------------------------------
    @property
    def words(self):
        return list(self._words)

    def text(self):
        """Render the words into a readable sentence."""
        out = []
        for w in self._words:
            out.append(" " if w == " " else w)
        # join words with single spaces, but respect explicit space markers
        s = ""
        for i, w in enumerate(self._words):
            if w == " ":
                s = s.rstrip() + " "
            else:
                s += (w + " ")
        return s.strip()
