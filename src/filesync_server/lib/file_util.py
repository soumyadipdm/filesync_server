import hashlib
import logging
import os
import shutil
import tempfile
from functools import partial

from filesync_server.lib.util import Counter

BLOCKSIZE = 4096  # 4kb
HASHFUNCTION = hashlib.sha256


def calc_hash(data: bytes) -> str:
    """
    Calculate hash of a given string
    :param data: for which hash is to be calculated
    :return: hex digest of the data
    """
    return HASHFUNCTION(data).hexdigest()


def file_checksum(filepath: str) -> str:
    """
    Calculate checksum of the entire file
    :param filepath: path to the file
    :return: calculated hex digest
    """
    with open(filepath, "rb") as fd:
        data = fd.read()
    if data:
        return calc_hash(data)
    return ""


def blocks(filename: str, size: int=BLOCKSIZE, is_data: bool=True):
    """
    returns blocks of a file and their checksum
    :param filename: path to the file
    :param size: block size
    :param is_data: Whether the block data to be returned
    :return: a generator of tuple of checksum and data of each block
    """
    with open(filename, "rb") as fd:
        for data in iter(partial(fd.read, size), b""):
            checksum = calc_hash(data)
            if is_data:
                yield checksum, data
            else:
                yield checksum


def checksums2dict(checksums: list) -> dict:
    """
    Converts a list of checksums to a dict for easier look up of a block
    :param checksums:  tuple of checksums
    :return: dictionary of {checksum: index}
    """
    result = {}
    for index, checksum in enumerate(checksums):
        if checksum not in result:
            result[checksum] = index

    return result


class ServedFile:
    """Representation of file being served in terms of blocks
    :param path: path to the file
    :param blocksize: size of each of the block
    """

    def __init__(self, path: str, blocksize: int):
        assert os.path.isfile(path)
        self.file = path
        self.blocksize = blocksize

        # TODO: avoid reading same file 2 times
        self.checksum = file_checksum(self.file)

    def blocks(self):
        for block in blocks(self.file, size=self.blocksize):
            yield block

    def patch(self, checksums: list):
        """
        Create a patch from another file's block checksums
        :param checksums:
        :return: a generator either checksum and block data or
        index number
        """
        checksums_dict = checksums2dict(checksums)
        for checksum, data in self.blocks():
            if checksum in checksums_dict:
                yield checksums_dict[checksum]
            else:
                yield (checksum, data)


class ReceivedFile:
    """Representation of file being received

    :param path: path to the file
    :param blocksize: size of each of the block
    """

    def __init__(self, path: str, blocksize: int):
        self._log = logging.getLogger()
        self.file = path
        self.blocksize = blocksize

        if os.path.isfile(self.file):
            self.checksum = file_checksum(self.file)
        else:
            self.checksum = ""

        fd, self._tmpfile = tempfile.mkstemp(dir=os.path.dirname(self.file))
        os.close(fd)  # close the unwanted open file handle

    def apply_patch(self, patchdata: list, checksum: str, validate_block: bool=False):
        """
        Apply patch to the existing file
        :param patchdata: patch to be applied, a list of Block data
        :param checksum: checksum of the source file
        :param validate_block: should we validate downloaded blocks, block by block? It's slow of course
        :return:
        """
        def validate_block_data(block):
            assert block.checksum.checksum == calc_hash(block.data)

        # simple counters to emit a few metrics e.g how much data we transferred and how much we saved
        nr_block_saving = Counter()
        nr_block_transferred = Counter()

        try:
            if not self.checksum:
                # there's no already existing file to compare to
                with open(self._tmpfile, "wb") as fd:
                    for block in patchdata:
                        nr_block_transferred.incr()
                        if validate_block:
                            validate_block_data(block)
                        fd.seek(block.number * self.blocksize)
                        fd.write(block.data)

            else:
                if self.checksum == checksum:
                    # file already exists
                    self._log.debug("%s checksum matches with the source file checksum %s", self.file, checksum)
                    return

                with open(self._tmpfile, "wb") as tmpfd, open(self.file, "rb") as origfd:
                    for block in patchdata:
                        if block.data:
                            nr_block_transferred.incr()
                            if validate_block:
                                validate_block_data(block)
                            tmpfd.seek(block.number * self.blocksize)
                            tmpfd.write(block.data)
                        else:
                            nr_block_saving.incr()
                            origfd.seek(block.existing * self.blocksize)
                            data = origfd.read(self.blocksize)
                            tmpfd.seek(block.number * self.blocksize)
                            tmpfd.write(data)

            # it's necessary to ensure that the resultant file is exactly same as the source one
            tmpfile_checksum = file_checksum(self._tmpfile)
            assert tmpfile_checksum == checksum
            shutil.move(self._tmpfile, self.file)
            self._log.debug("%d bytes saved", nr_block_saving.value * self.blocksize)
            self._log.debug("%d bytes transferred", nr_block_transferred.value * self.blocksize)

        finally:
            # delete the temp file no matter what
            try:
                os.remove(self._tmpfile)
            except FileNotFoundError:
                # file is already moved
                pass
