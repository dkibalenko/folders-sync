import argparse
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
        

    @classmethod
    def from_args(cls):
        parser = argparse.ArgumentParser(
            description="Synchronizer's argument parser"
        )

        parser.add_argument("source", help="The path to source folder")
        parser.add_argument("replica", help="The path to replica folder")
        parser.add_argument("interval", type=int, help="Time between syncs")
        parser.add_argument("sync_amount", type=int, help="Number of sync runs")
        parser.add_argument("log_file", help="The path to log file")

        args = parser.parse_args()

        return cls(
            source=Path(args.source),
            replica=Path(args.replica),
            interval=args.interval,
            sync_amount=args.sync_amount,
            log_file=Path(args.log_file)
        )


def get_logger(name: str) -> Logger:
    pass


class DirectoryComparator:
    pass


class DirectorySynchronizer:
    pass


def main():
    args_parser = ArgsParser.from_args()


if __name__ == "__main__":
    main()
