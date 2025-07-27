import argparse
import filecmp
import logging
import os
from pathlib import Path
import shutil
from typing import Iterator, Self


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


class DirectorySynchronizer:
    def __init__(self, source: Path, replica: Path, logger: logging.Logger):
        self.source_root = source
        self.replica_root = replica
        self.logger = logger

    def sync(self) -> None:
        self._sync_files()
        self._remove_extra_replica_items()


    @staticmethod
    def _walk_directory_gen(dir_path: Path, topdown=True) -> Iterator[Path]:
        # iterate recursively from root dir
        for root, dirs, files in os.walk(dir_path, topdown=topdown):
            for directory in dirs:
                yield Path(root) / directory
            for file in files:
                yield Path(root) / file

    def _sync_files(self) -> None:

        source_paths = self._walk_directory_gen(self.source_root)

        for source_path in source_paths:
            replica_path = self.replica_root / source_path.relative_to(
                self.source_root
            )

            if source_path.is_dir():
                replica_path.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"Created directory: {replica_path}")
            else:
                is_same_file = filecmp.cmp(
                    source_path, replica_path, shallow=False
                )

                if not replica_path.exists() or not is_same_file:
                    shutil.copy2(source_path, replica_path)
                    self.logger.info(
                        f"Copied file: {source_path} -> {replica_path}"
                    )

    def _remove_extra_replica_items(self) -> None:

        replica_paths = self._walk_directory_gen(
            self.replica_root,
            topdown=False
        )

        for replica_path in replica_paths:
            source_path = self.source_root / replica_path.relative_to(
                self.replica_root
            )

            if not source_path.exists():
                # delere replica path
                if replica_path.is_dir():
                    shutil.rmtree(replica_path)
                    self.logger.info(f"Removed directory: {replica_path}")
                else:
                    replica_path.unlink()
                    self.logger.info(f"Removed file: {replica_path}")
        


def main():
    args_parser = ArgsParser.from_args()
    logger = get_logger("Directory Synchronizer", args_parser.log_file)
    synchronizer = DirectorySynchronizer(
        args_parser.source,
        args_parser.replica,
        logger
    )
    import pdb; pdb.set_trace()
    synchronizer.sync()



if __name__ == "__main__":
    main()
