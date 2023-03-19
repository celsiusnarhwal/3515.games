from path import Path


class Routes(Path):
    """
    A reliable accessor for certain top-level directories.
    """

    @classmethod
    def root(cls):
        return cls(__file__).parent

    @classmethod
    def bot(cls):
        return cls.root() / "bot"

    @classmethod
    def kurisu(cls):
        return cls.root() / "kurisu"
