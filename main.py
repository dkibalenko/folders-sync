import argparse
import logging
import os
from pathlib import Path
from typing import Self


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
        self.log_file = log_file
        self._validate_args()
        

    @classmethod
    def from_args(cls) -> Self:
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

    def _validate_args(self) -> None:

        if not self.source.is_dir():
            raise ValueError(
                f"Source folder does not exist or "
                f"is not a directory: {self.source}"
            )
        if not self.replica.exists():
            os.makedirs(name=self.replica)
        if not self.replica.is_dir():
            raise ValueError(
                f"Replica path is not a directory: {self.replica}"
            )
        if self.interval < 0:
            raise ValueError("Interval must be non-negative")
        if self.sync_amount < 1:
            raise ValueError("Synchronization amount must be at least 1")
        
        # validation for log file ? logger should write in it


def get_logger(
    name: str,
    log_file: Path,
    level = logging.INFO
) -> logging.Logger:

    logger = logging.getLogger(name=name)
    logger.setLevel(level=level)

    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # set consol handler to send logs to the consol
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # set file handler to send logs to a file
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


class DirectoryComparator:
    pass


class DirectorySynchronizer:
    def __init__(self, source: Path, replica: Path):
        self.source_root = source
        self.replica_root = replica

    def walk_source(self) -> list[Path]:
        items_to_sync = []
        # get all items from source root and sub dirs
        for root, dirs, files in os.walk(self.source_root):
            for directory in dirs:
                items_to_sync.append(os.path.join(root, directory))
            for file in files:
                items_to_sync.append(os.path.join(root, file))

        return items_to_sync


def main():
    args_parser = ArgsParser.from_args()


if __name__ == "__main__":
    main()
