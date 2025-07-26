from logging import Logger
from pathlib import Path


class ArgsParser:
    def __init__(
        self,
        source: Path,
        replica: Path,
        interval: int,
        sync_amount: int,
        log_file: Path
    ):
        self.source = source
        self.replica = replica
        self.interval = interval
        self.sync_amount = sync_amount
        self.log_file =log_file


def get_logger(name: str) -> Logger:
    pass


class DirectoryComparator:
    pass


class DirectorySynchronizer:
    pass


def main():
    pass


if __name__ == "__main__":
    main()
