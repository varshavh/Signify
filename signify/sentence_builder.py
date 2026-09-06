"""
Sentence-building logic with temporal debouncing + smart letter/word handling.

The model emits two kinds of labels:
  * single LETTERS (A–Z)  -> should be spelled INTO one word, e.g. W,A,N,T -> "WANT"
  * whole WORDS (Hello, ILoveYou, ...) -> stand-alone tokens, spaced apart

So we keep a `_buffer` of the letters currently being spelled and a list of
finalized `_words`. A letter appends to the buffer; a whole word flushes the
buffer and adds itself as its own token; Space flushes the current buffer.

Raw per-frame predictions are noisy, so a label must be the top prediction for
a run of consecutive frames before it's committed (temporal debouncing).
"""

from collections import deque, Counter

# Labels that need a nicer on-screen / spoken form than the raw model label.
DISPLAY_NAMES = {
    "ILoveYou": "I Love You",
    "NotOk": "Not Ok",
    "Thankyou": "Thank You",
    "MyNameIs": "My Name Is",
    "GoodMorning": "Good Morning",
    "none": "",
}


def display_name(label: str) -> str:
    """Human-friendly form of a raw model label."""
    if label is None:
        return ""
    return DISPLAY_NAMES.get(label, label)


def is_letter(label: str) -> bool:
    """True for single A–Z fingerspelling letters."""
    return isinstance(label, str) and len(label) == 1 and label.isalpha()


class SentenceBuilder:
    def __init__(self, stability=10, min_confidence=0.5, cooldown_frames=8,
                 autobreak_frames=25, corrector=None):
        # stability: frames a label must dominate before it's committed
        # cooldown_frames: empty/other frames before the SAME label can repeat
        # autobreak_frames: empty frames after which spelled letters auto-finish
        #                   into a word (so pausing the hand = a word break)
        # corrector: optional AutoCorrector applied to spelled words on flush
        self.stability = stability
        self.min_confidence = min_confidence
        self.cooldown_frames = cooldown_frames
        self.autobreak_frames = autobreak_frames
        self.corrector = corrector
        self.autocorrect_enabled = corrector is not None

        self._recent = deque(maxlen=stability)
        self._words = []       # finalized tokens (already display-formatted)
        self._buffer = ""      # letters currently being spelled
        self._last_committed = None
        self._empty_streak = 0

    # ---- live feed -------------------------------------------------------
    def update(self, label, score):
        """Feed one frame's top prediction (label may be None).

        Returns the newly committed item this frame (a letter or a word), or
        None if nothing was committed.
        """
        # 'none' is the model's no-gesture class — treat as empty.
        if label == "none":
            label = None

        if label is None or score < self.min_confidence:
            self._recent.append(None)
            self._empty_streak += 1
            if self._empty_streak >= self.cooldown_frames:
                self._last_committed = None  # allow same label again after a pause
            # a longer pause while spelling auto-finishes the current word
            if self._empty_streak == self.autobreak_frames and self._buffer:
                self._flush_buffer()
            return None

        self._empty_streak = 0
        self._recent.append(label)
        if len(self._recent) < self.stability:
            return None

        winner, count = Counter(self._recent).most_common(1)[0]
        if winner is None or count < int(0.8 * self.stability):
            return None
        if winner == self._last_committed:
            return None

        self._last_committed = winner
        if is_letter(winner):
            # spell into the current word
            self._buffer += winner
            return winner
        else:
            # a whole word: finalize any spelled letters, then add the word
            self._flush_buffer()
            self._words.append(display_name(winner))
            return display_name(winner)

    # ---- editing ---------------------------------------------------------
    def _flush_buffer(self):
        if self._buffer:
            word = self._buffer
            # spelled words get autocorrected (whole-word signs never enter here)
            if self.autocorrect_enabled and self.corrector is not None:
                word = self.corrector.correct(word)
            self._words.append(word)
            self._buffer = ""

    def add_space(self):
        """Finish the word currently being spelled (start a new one).

        No-op when nothing is being spelled, so repeated presses can't create
        empty tokens / double spaces. Also clears the debounce window so a
        lingering letter isn't re-committed into the next word.
        """
        self._flush_buffer()
        self._recent.clear()
        self._last_committed = None
        self._empty_streak = 0

    # kept as an explicit alias so the UI can have a distinct "Space" button
    end_word = add_space

    def add_period(self):
        """Finish the current word and put a full stop on the last token."""
        self._flush_buffer()
        self._recent.clear()
        self._last_committed = None
        self._empty_streak = 0
        if not self._words:
            return
        last = self._words[-1]
        if last.endswith((".", "!", "?")):
            return
        self._words[-1] = last + "."

    def backspace(self):
        """Delete the last character being spelled, or the last whole token."""
        if self._buffer:
            self._buffer = self._buffer[:-1]
        elif self._words:
            self._words.pop()
        self._last_committed = None

    def clear(self):
        self._words.clear()
        self._buffer = ""
        self._recent.clear()
        self._last_committed = None
        self._empty_streak = 0

    def add_word(self, word):
        """Manually append a finalized word (e.g. from a quick-add button)."""
        self._flush_buffer()
        self._words.append(display_name(word))
        self._last_committed = None

    # ---- output ----------------------------------------------------------
    @property
    def words(self):
        out = list(self._words)
        if self._buffer:
            out.append(self._buffer)
        return out

    def text(self):
        """Render finalized words + the word currently being spelled."""
        return " ".join(self.words)
