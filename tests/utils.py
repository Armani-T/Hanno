# pylint: disable=W0612
SAMPLE_SOURCE = "let l = [1, 2, 3] <> [4, 5, 6] in head(l)"
SAMPLE_SOURCE_PATH = __file__


class FakeMatch:
    """This class is used to mock passing a `re.Match` object."""

    def __init__(self, span: tuple[int, int], last_group: str, text: str) -> None:
        self._span = span
        self.lastgroup = last_group
        self.text = text

    def span(self):
        return self._span

    def __getitem__(self, index):
        if index == 0:
            return self.text
        raise RuntimeError("`FakeMatch` can only index the value 0.")
