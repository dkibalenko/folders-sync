import logging
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock, call

from main import ArgsParser, DirectorySynchronizer
import main


class TestArgsParser(unittest.TestCase):
    def setUp(self):
        """
        Set up mock paths for validation tests.
        """
        self.mock_source_path = MagicMock(spec=Path)
        self.mock_replica_path = MagicMock(spec=Path)
        self.mock_log_file_path = MagicMock(spec=Path)
        self.mock_log_file_parent_path = MagicMock(spec=Path)

        self.mock_log_file_path.parent = self.mock_log_file_parent_path

        self.args_parser = ArgsParser(
            source=self.mock_source_path,
            replica=self.mock_replica_path,
            interval=60,
            sync_amount=10,
            log_file=self.mock_log_file_path
        )

    @patch("argparse.ArgumentParser")
    def test_from_args(self, mock_argparse):

        mock_args = MagicMock()

        mock_args.source = "/path/to/source"
        mock_args.replica = "/path/to/replica"
        mock_args.interval = 10
        mock_args.sync_amount = 2
        mock_args.log_file = "/path/to/log/file.log"

        mock_parser = MagicMock()
        mock_parser.parse_args.return_value = mock_args
        mock_argparse.return_value = mock_parser

        # call the factory method
        args_parser = ArgsParser.from_args()

        self.assertEqual(args_parser.source, Path(mock_args.source))
        self.assertEqual(args_parser.replica, Path(mock_args.replica))
        self.assertEqual(args_parser.interval, mock_args.interval)
        self.assertEqual(args_parser.sync_amount, mock_args.sync_amount)
        self.assertEqual(args_parser.log_file, Path(mock_args.log_file))

    def test_validate_args_valid(self):
        """
        Tests _validate_args with all valid arguments.
        """
        self.mock_source_path.is_dir.return_value = True
        self.mock_replica_path.exists.return_value = True
        self.mock_replica_path.is_dir.return_value = True
        self.mock_log_file_parent_path.exists.return_value = True
        self.mock_log_file_path.is_dir.return_value = False

        self.args_parser._validate_args()


    def test_validate_args_invalid_source(self):
        """
        Tests _validate_args with a source that is not a directory.
        """
        self.mock_source_path.is_dir.return_value = False
        with self.assertRaises(ValueError):
            self.args_parser._validate_args()

    def test_validate_args_invalid_replica(self):
        """
        Tests _validate_args with a replica that is not a directory.
        """
        self.mock_source_path.is_dir.return_value = True
        self.mock_replica_path.exists.return_value = True
        self.mock_replica_path.is_dir.return_value = False
        with self.assertRaises(ValueError):
            self.args_parser._validate_args()

    def test_validate_args_replica_does_not_exist(self):
        """
        Tests if os.makedirs is called when replica does not exist.
        """
        self.mock_source_path.is_dir.return_value = True
        self.mock_replica_path.exists.return_value = False
        self.mock_replica_path.is_dir.return_value = True # Assume it becomes a dir after creation
        self.mock_log_file_parent_path.exists.return_value = True
        self.mock_log_file_path.is_dir.return_value = False
        self.args_parser._validate_args()

    def test_validate_args_negative_interval(self):
        """
        Tests _validate_args with a negative interval.
        """
        self.args_parser.interval = -1
        self.mock_source_path.is_dir.return_value = True
        self.mock_replica_path.exists.return_value = True
        self.mock_replica_path.is_dir.return_value = True
        with self.assertRaises(ValueError):
            self.args_parser._validate_args()

    def test_validate_args_zero_sync_amount(self):
        """
        Tests _validate_args with a sync_amount less than 1.
        """
        self.args_parser.sync_amount = 0
        self.mock_source_path.is_dir.return_value = True
        self.mock_replica_path.exists.return_value = True
        self.mock_replica_path.is_dir.return_value = True
        with self.assertRaises(ValueError):
            self.args_parser._validate_args()

    def test_validate_log_file_is_directory(self):
        """
        Tests _validate_args when the log file path is a directory.
        """
        self.mock_source_path.is_dir.return_value = True
        self.mock_replica_path.exists.return_value = True
        self.mock_replica_path.is_dir.return_value = True
        self.mock_log_file_parent_path.exists.return_value = True
        self.mock_log_file_path.exists.return_value = True
        self.mock_log_file_path.is_dir.return_value = True
        with self.assertRaises(ValueError):
            self.args_parser._validate_args()

    def test_validate_args_log_parent_creation_fails(self):
        """
        Tests that a ValueError is raised if creating the log file's parent directory fails.
        """
        # basic validation setup
        self.mock_source_path.is_dir.return_value = True
        self.mock_replica_path.exists.return_value = True
        self.mock_replica_path.is_dir.return_value = True

        # key condition for this test: log parent directory does NOT exist
        self.mock_log_file_parent_path.exists.return_value = False

        # configure the mkdir method on the mock to raise an OSError
        self.mock_log_file_parent_path.mkdir.side_effect = OSError("Permission denied")

        # expect a ValueError to be raised
        with self.assertRaises(ValueError) as context:
            self.args_parser._validate_args()

        # optionally, check the content of the error message
        self.assertIn("Failed to create log file directory", str(context.exception))

        # assert that mkdir was called, even though it failed
        self.mock_log_file_parent_path.mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_validate_args_log_parent_does_not_exist_creates_it(self):
        """
        Tests that the log file's parent directory is created if it does not exist.
        """
        # basic validation setup
        self.mock_source_path.is_dir.return_value = True
        self.mock_replica_path.exists.return_value = True
        self.mock_replica_path.is_dir.return_value = True
        self.mock_log_file_path.is_dir.return_value = False

        # key condition for this test: log parent directory does NOT exist
        self.mock_log_file_parent_path.exists.return_value = False

        # don't expect any exception here
        self.args_parser._validate_args()

        # assert that mkdir was called to create the missing directory
        self.mock_log_file_parent_path.mkdir.assert_called_once_with(parents=True, exist_ok=True)


class TestDirectorySynchronizer(unittest.TestCase):
    def setUp(self):
        # create two real temp dirs
        self.src_dir = tempfile.mkdtemp()
        self.dst_dir = tempfile.mkdtemp()
        self.src = Path(self.src_dir)
        self.dst = Path(self.dst_dir)

        # simple mock logger
        self.logger = MagicMock(spec=logging.Logger)

        # the system under test
        self.syncer = DirectorySynchronizer(self.src, self.dst, self.logger)

    def tearDown(self):
        # clean up on disk
        shutil.rmtree(self.src_dir)
        shutil.rmtree(self.dst_dir)

    def test_sync_creates_dirs_and_copies_files(self):
        # Arrange: build nested source tree + one file
        nested = self.src / "a" / "b"
        nested.mkdir(parents=True)
        file_src = nested / "hello.txt"
        file_src.write_text("Hello world", encoding="utf-8")

        # Act
        self.syncer.sync(count=1)

        # Assert: directory and file exist under replica
        replica_dir = self.dst / "a" / "b"
        replica_file = replica_dir / "hello.txt"
        self.assertTrue(replica_dir.is_dir())
        self.assertTrue(replica_file.is_file())
        self.assertEqual(replica_file.read_text(), "Hello world")

        # Assert: logger got start/completed, plus dir‐create and file‐copy
        self.logger.info.assert_any_call("Start sync cycle 1")
        self.logger.info.assert_any_call(f"Created directory: {replica_dir}")
        self.logger.info.assert_any_call(f"Copied file: {file_src} -> {replica_file}")
        self.logger.info.assert_any_call("Completed sync cycle 1")

    def test_sync_updates_modified_file(self):
        # Arrange: initial file + sync
        file_src = self.src / "data.txt"
        file_src.write_text("v1")
        self.syncer.sync(count=1)

        # reset logger so we only see calls from second sync
        self.logger.reset_mock()

        # Act: modify source + sync again
        file_src.write_text("v2")
        self.syncer.sync(count=2)

        # Assert: replica updated, copy logged
        replica_file = self.dst / "data.txt"
        self.assertEqual(replica_file.read_text(), "v2")
        self.logger.info.assert_any_call(f"Copied file: {file_src} -> {replica_file}")

    def test_sync_removes_deleted_file(self):
        # Arrange: initial file + sync
        file_src = self.src / "temp.txt"
        file_src.write_text("bye")
        self.syncer.sync(count=1)

        # reset logger
        self.logger.reset_mock()

        # Act: delete in source + sync
        file_src.unlink()
        self.syncer.sync(count=2)

        # Assert: gone in replica + removal logged
        replica_file = self.dst / "temp.txt"
        self.assertFalse(replica_file.exists())
        self.logger.info.assert_any_call(f"Removed file: {replica_file}")

    def test_sync_removes_deleted_directory(self):
        # Arrange: nested dir + file + sync
        nested = self.src / "x" / "y"
        nested.mkdir(parents=True)
        (nested / "f.txt").write_text("data")
        self.syncer.sync(count=1)

        # reset logger
        self.logger.reset_mock()

        # Act: delete entire subtree in source + sync
        shutil.rmtree(self.src / "x")
        self.syncer.sync(count=2)

        # Assert: dir removed in replica + logged
        replica_nested = self.dst / "x" / "y"
        self.assertFalse(replica_nested.exists())
        # The code first removes files, then dirs; we should see:
        self.logger.info.assert_any_call(f"Removed directory: {self.dst / 'x'}")


class TestMainFunction(unittest.TestCase):

    @patch('main.sleep')
    @patch('main.DirectorySynchronizer')
    @patch('main.get_logger')
    @patch('main.ArgsParser')
    def test_main_drives_sync_and_sleep(
        self,
        mock_argsparser_cls,
        mock_get_logger,
        mock_ds_cls,
        mock_sleep
    ):
        # Arrange: build a fake namespace returned by ArgsParser.from_args()
        fake_args = MagicMock()
        fake_args.source = '/src/path'
        fake_args.replica = '/dst/path'
        fake_args.log_file = '/var/log/f.log'
        fake_args.sync_amount = 3
        fake_args.interval = 5
        mock_argsparser_cls.from_args.return_value = fake_args

        # Arrange: fake logger and synchronizer
        fake_logger = MagicMock(name='fake_logger')
        mock_get_logger.return_value = fake_logger

        fake_syncer = MagicMock(name='fake_syncer')
        mock_ds_cls.return_value = fake_syncer

        # Act
        main.main()

        # Assert: ArgsParser.from_args() was called
        mock_argsparser_cls.from_args.assert_called_once_with()

        # Assert: get_logger called with correct parameters
        mock_get_logger.assert_called_once_with(
            "Directory Synchronizer",
            fake_args.log_file
        )

        # Assert: DirectorySynchronizer was instantiated correctly
        mock_ds_cls.assert_called_once_with(
            fake_args.source,
            fake_args.replica,
            fake_logger
        )

        # Assert: sync() called 3 times with counts 1, 2, 3
        expected_calls = [(( ), {'count': i}) for i in (1, 2, 3)]
        # build actual call args list
        actual = fake_syncer.sync.call_args_list
        # transform to just count arg lists
        counts = [call.kwargs.get('count') for call in actual]
        self.assertEqual(counts, [1, 2, 3])

        # Assert: sleep() called twice with interval=5
        # since sync_amount=3, we sleep between 1->2 and 2->3
        mock_sleep.assert_has_calls([call(5), call(5)])
        self.assertEqual(mock_sleep.call_count, 2)
