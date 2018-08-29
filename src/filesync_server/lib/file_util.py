import hashlib
import os
from functools import partial

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


def checksums2dict(checksums: tuple) -> dict:
    """
    Converts a tuple of checksums to a dict
    :param checksums:  tuple of checksums
    :return: dictionary of {checksum: index}
    """
    result = {}
    for index, checksum in enumerate(checksums):
        if checksum not in result:
            result[checksum] = index

    return result


class FileObj:
    """File representation in terms of blocks
    :param path: path to the file
    """

    def __init__(self, path: str, blocksize: int):
        assert os.path.exists(path)
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
