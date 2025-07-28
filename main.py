import argparse
import filecmp
import logging
import os
from pathlib import Path
import shutil
from time import sleep
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
        # self._validate_args()
        

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
        
        log_file_parent = self.log_file.parent

        if not log_file_parent.exists():
            try:
                log_file_parent.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise ValueError(
                    f"Failed to create log file directory: {log_file_parent}. "
                    f"Error: {e}")
        if self.log_file.exists() and self.log_file.is_dir():
            raise ValueError(f"Log file path is a directory: {self.log_file}")
        # if not os.access(log_file_parent, os.W_OK):
        #     raise ValueError(
        #         f"No write permission for log file directory: {log_file_parent}"
        #     )


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

    def sync(self, count: int = 1) -> None:
        self.logger.info(
            f"Start sync cycle {count}"
        )
        self._sync_dirs()
        self._sync_files()
        self._remove_old_replica_files()
        self._remove_old_replica_dirs()
        self.logger.info(
            f"Completed sync cycle {count}"
        )

    @staticmethod
    def _walk_directory_gen(dir_path: Path, topdown=True) -> Iterator[Path]:
        """
        Iterate recursively from root directory.

        This is a generator of paths which iterates recursively from the given
        directory, yielding each subdirectory and file.

        Args:
            dir_path (Path): The path to the root directory.
            topdown (bool): Whether to iterate top-down or bottom-up. (default: True)

        Yields:
            Iterator[Path]: An iterator of paths to the subdirectories and files.
        """
        # iterate recursively from root dir
        for root, dirs, files in os.walk(dir_path, topdown=topdown):
            for directory in dirs:
                yield Path(root) / directory
            for file in files:
                yield Path(root) / file

    def _replica_path_construct(self, source_path: Path) -> Path:
        return self.replica_root / source_path.relative_to(
                self.source_root
            )

    def _source_path_construct(self, replica_path: Path) -> Path:
        return self.source_root / replica_path.relative_to(
                self.replica_root
            )

    def _sync_dirs(self) -> None:
        """
        Synchronizes directories between source and replica directories.

        This method traverses the source directory structure and ensures that
        all directories present in the source are also present in the replica.
        If a directory in the source does not exist in the replica, it is created
        in the replica and the action is logged. Handles potential errors in 
        directory creation and logs them accordingly.
        """

        source_paths = self._walk_directory_gen(self.source_root)

        for source_path in source_paths:
            replica_path = self._replica_path_construct(source_path)

            if source_path.is_dir():
                if not replica_path.exists():
                    try:
                        replica_path.mkdir(parents=True)
                        self.logger.info(f"Created directory: {replica_path}")
                    except OSError as e:
                        self.logger.error(
                        f"Failed to create directory {replica_path}: {e}"
                    )

    def _sync_files(self) -> None:
        """
        Synchronizes files between source and replica directories.

        This method traverses the source directory structure and identifies
        files that are not present in the replica directory structure or
        whose contents differ from those in the replica. It copies each
        identified file to the replica directory structure, and logs the
        action. Handles both symbolic links and regular files.

        Logs an error if a file cannot be copied.
        """
        source_paths = self._walk_directory_gen(self.source_root)

        for source_path in source_paths:
            replica_path = self._replica_path_construct(source_path)

            if source_path.is_file():
                if (
                    not replica_path.exists()
                    or not filecmp.cmp(
                        source_path,
                        replica_path,
                        shallow=False
                    )
                ):
                    try:
                        replica_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source_path, replica_path)
                        self.logger.info(
                            f"Copied file: {source_path} -> {replica_path}"
                        )
                    except OSError as e:
                        self.logger.error(
                            f"Failed to copy file {source_path}: {e}"
                        )
                    except Exception as e:
                        self.logger.error(
                            f"Unexpected error when copy files: {e}"
                        )

    def _remove_old_replica_files(self) -> None:
        """
        Removes files in the replica that do not exist in the source.

        This method traverses the replica directory structure in reverse order 
        and identifies files that are not present in the source directory structure. 
        It removes each identified file and logs the action. Handles potential 
        errors during file removal by logging appropriate error messages.
        """

        replica_paths = self._walk_directory_gen(
            self.replica_root,
            topdown=False
        )

        for replica_path in replica_paths:
            source_path = self._source_path_construct(replica_path)

            if not source_path.exists():

                if replica_path.is_file():
                    try:
                        replica_path.unlink()
                        self.logger.info(f"Removed file: {replica_path}")
                    except FileNotFoundError as e:
                        self.logger.error(
                            f"File not found for removal: {replica_path} ({e})"
                        )
                    except OSError as e:
                        self.logger.error(
                            f"Failed to remove file {replica_path}: {e}"
                        )

    def _remove_old_replica_dirs(self) -> None:

        """
        Removes directories in the replica that do not exist in the source.
        
        This method traverses the replica directory structure and identifies 
        directories that are not present in the source directory structure. 
        It removes each identified directory, and logs the action. Handles 
        both symbolic links and regular directories.

        Logs an error if a directory cannot be removed.
        """

        replica_paths = self._walk_directory_gen(
            self.replica_root,
            topdown=False
        )

        for replica_path in replica_paths:
            source_path = self._source_path_construct(replica_path)

            if not source_path.exists():  # remove only replica paths
                # delere replica path
                if replica_path.is_dir():
                    try:
                        if replica_path.is_symlink():
                            replica_path.unlink()
                            self.logger.info(f"Removed symlink: {replica_path}")
                        else:
                            shutil.rmtree(replica_path)
                            self.logger.info(f"Removed directory: {replica_path}")
                    except OSError as e:
                        self.logger.error(
                            f"Failed to remove directory {replica_path}: {e}"
                        )


def main():
    args_parser = ArgsParser.from_args()
    logger = get_logger("Directory Synchronizer", args_parser.log_file)
    synchronizer = DirectorySynchronizer(
        args_parser.source,
        args_parser.replica,
        logger
    )
    sync_count = 1
    # import pdb; pdb.set_trace()
    for _ in range(args_parser.sync_amount):
        synchronizer.sync(count=sync_count)

        if sync_count < args_parser.sync_amount:
             sleep(args_parser.interval)
             sync_count += 1


if __name__ == "__main__":
    main()
