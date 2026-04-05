"""
CFF (Caesar Flash File) Parser
Ported from CFFFlashFileTools (C++/Qt) to Python.
Parses Mercedes-Benz CFF containers and extracts flash segments as binary data.
"""

import struct


def _build_crc_table():
    """Generate standard CRC32 lookup table with polynomial 0xEDB88320."""
    table = []
    for i in range(256):
        crc = i
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xEDB88320
            else:
                crc >>= 1
        table.append(crc)
    return table


CRC_TABLE = _build_crc_table()

STUB_HEADER_SIZE = 0x410
FILE_HEADER_ID = "CBF-TRANSLATOR-VERSION:04.00"


class BitflagReader:
    """Reads fields conditionally based on a bitflag word, mirroring CFFUtils."""

    def __init__(self, bitflags):
        self.bitflags = bitflags

    def check_and_advance(self):
        flag_is_set = (self.bitflags & 1) > 0
        self.bitflags >>= 1
        return flag_is_set

    def read_4byte(self, data, offset):
        if self.check_and_advance():
            val = struct.unpack_from('<I', data, offset)[0]
            return val, offset + 4
        return 0, offset

    def read_2byte(self, data, offset):
        if self.check_and_advance():
            val = struct.unpack_from('<H', data, offset)[0]
            return val, offset + 2
        return 0, offset

    def read_1byte(self, data, offset):
        if self.check_and_advance():
            val = struct.unpack_from('<B', data, offset)[0]
            return val, offset + 1
        return 0, offset

    def read_string(self, data, offset, virtual_base):
        if self.check_and_advance():
            string_offset = struct.unpack_from('<i', data, offset)[0]
            offset += 4
            str_pos = string_offset + virtual_base
            if str_pos < 0 or str_pos >= len(data):
                return "", offset
            try:
                end = data.index(b'\x00', str_pos)
            except ValueError:
                end = len(data)
            return data[str_pos:end].decode('latin-1', errors='replace'), offset
        return "", offset


class FlashSegment:
    """Represents a single flash segment (binary firmware chunk)."""

    def __init__(self):
        self.segment_name = ""
        self.from_address = 0
        self.segment_length = 0
        self.data = b""


class FlashDataBlock:
    """Represents a flash data block containing multiple segments."""

    def __init__(self):
        self.qualifier = ""
        self.data_block_type = ""
        self.flash_data_info = ""
        self.file_name = ""
        self.segments = []


class CFFParser:
    """Parses a CFF (Caesar Flash File) container and extracts flash segments."""

    def __init__(self, file_data):
        self.data = file_data
        self.flash_name = ""
        self.file_author = ""
        self.file_creation_time = ""
        self.cff_version = ""
        self.stored_checksum = 0
        self.calculated_checksum = 0
        self.data_blocks = []
        self.base_address = 0

    @classmethod
    def from_file(cls, filepath):
        with open(filepath, 'rb') as f:
            data = f.read()
        parser = cls(data)
        parser.parse()
        return parser

    def parse(self):
        self._read_checksum()
        self._gen_checksum()
        self._read_header()
        self._read_flash_header()

    def _read_checksum(self):
        if len(self.data) < 4:
            raise ValueError("File too small to contain a checksum")
        self.stored_checksum = struct.unpack_from('<I', self.data, len(self.data) - 4)[0]

    def _gen_checksum(self):
        crc = 0xFFFFFFFF
        for i in range(len(self.data) - 4):
            byte = self.data[i]
            table_index = (crc ^ byte) & 0xFF
            crc = CRC_TABLE[table_index] ^ ((crc >> 8) & 0xFFFFFF)
        self.calculated_checksum = crc & 0xFFFFFFFF

    def checksum_valid(self):
        return self.stored_checksum == self.calculated_checksum

    def _read_header(self):
        if len(self.data) < STUB_HEADER_SIZE + 4:
            raise ValueError("File too small for CFF format")
        file_type_byte = self.data[0x401]
        if file_type_byte not in (3, 5):
            raise ValueError(f"Unknown file type identifier: {file_type_byte}")

    def _read_flash_header(self):
        offset = STUB_HEADER_SIZE  # 0x410

        cff_header_size = struct.unpack_from('<I', self.data, offset)[0]
        offset += 4

        self.base_address = offset

        bitflags = struct.unpack_from('<I', self.data, offset)[0]
        offset += 4
        _tmp = struct.unpack_from('<H', self.data, offset)[0]
        offset += 2

        bf = BitflagReader(bitflags)

        self.flash_name, offset = bf.read_string(self.data, offset, self.base_address)
        _flash_gen_params, offset = bf.read_string(self.data, offset, self.base_address)

        _unk3, offset = bf.read_4byte(self.data, offset)
        _unk4, offset = bf.read_4byte(self.data, offset)

        self.file_author, offset = bf.read_string(self.data, offset, self.base_address)
        self.file_creation_time, offset = bf.read_string(self.data, offset, self.base_address)
        _authoring_tool_ver, offset = bf.read_string(self.data, offset, self.base_address)
        _ftrafo_ver_string, offset = bf.read_string(self.data, offset, self.base_address)

        _ftrafo_ver_num, offset = bf.read_4byte(self.data, offset)

        self.cff_version, offset = bf.read_string(self.data, offset, self.base_address)

        num_flash_areas, offset = bf.read_4byte(self.data, offset)
        flash_desc_table, offset = bf.read_4byte(self.data, offset)
        data_block_count, offset = bf.read_4byte(self.data, offset)
        data_block_ref_table, offset = bf.read_4byte(self.data, offset)
        _ctf_header_table, offset = bf.read_4byte(self.data, offset)
        language_block_length, offset = bf.read_4byte(self.data, offset)
        _num_ecu_refs, offset = bf.read_4byte(self.data, offset)
        _ecu_ref_table, offset = bf.read_4byte(self.data, offset)
        _unk_table_count, offset = bf.read_4byte(self.data, offset)
        _unk_table_probably, offset = bf.read_4byte(self.data, offset)
        _unk15, offset = bf.read_1byte(self.data, offset)

        # Parse data blocks
        for i in range(data_block_count):
            entry_addr = data_block_ref_table + self.base_address + (i * 4)
            block_pos = struct.unpack_from('<i', self.data, entry_addr)[0]
            block_base = data_block_ref_table + self.base_address + block_pos

            db = self._read_data_block(block_base, cff_header_size, language_block_length)
            self.data_blocks.append(db)

    def _read_data_block(self, base_address, cff_header_size, language_block_length):
        block = FlashDataBlock()
        offset = base_address

        bitflags = struct.unpack_from('<I', self.data, offset)[0]
        offset += 4

        # 2-byte tmp (matches C++: ushort tmp; cff->read(&tmp, 2))
        _tmp = struct.unpack_from('<H', self.data, offset)[0]
        offset += 2

        bf = BitflagReader(bitflags)

        # Field order matches CFFFlashDataBlock::readCFFData() exactly
        block.qualifier, offset = bf.read_string(self.data, offset, base_address)
        _long_name, offset = bf.read_4byte(self.data, offset)
        _description, offset = bf.read_4byte(self.data, offset)
        flash_data, offset = bf.read_4byte(self.data, offset)
        _block_length, offset = bf.read_4byte(self.data, offset)
        _data_format, offset = bf.read_4byte(self.data, offset)
        _file_name, offset = bf.read_4byte(self.data, offset)
        _num_filters, offset = bf.read_4byte(self.data, offset)
        _filters_offset, offset = bf.read_4byte(self.data, offset)
        num_segments, offset = bf.read_4byte(self.data, offset)
        segment_offset, offset = bf.read_4byte(self.data, offset)
        _encryption_mode, offset = bf.read_4byte(self.data, offset)
        _key_length, offset = bf.read_4byte(self.data, offset)
        _key_buffer, offset = bf.read_4byte(self.data, offset)
        _num_own_idents, offset = bf.read_4byte(self.data, offset)
        _idents_offset, offset = bf.read_4byte(self.data, offset)
        _num_securities, offset = bf.read_4byte(self.data, offset)
        _securities_offset, offset = bf.read_4byte(self.data, offset)
        block.data_block_type, offset = bf.read_string(self.data, offset, base_address)
        _unique_object_id, offset = bf.read_4byte(self.data, offset)
        block.flash_data_info, offset = bf.read_string(self.data, offset, base_address)
        _flash_data_info_lang1, offset = bf.read_4byte(self.data, offset)
        _flash_data_info_lang2, offset = bf.read_4byte(self.data, offset)
        _flash_data_info_idk2, offset = bf.read_4byte(self.data, offset)

        # Parse segments with fileCursor accumulation (matches C++ exactly)
        file_cursor = 0
        for seg_idx in range(num_segments):
            seg_entry_addr = segment_offset + base_address + (seg_idx * 4)
            seg_pos = struct.unpack_from('<i', self.data, seg_entry_addr)[0]
            seg_base = segment_offset + base_address + seg_pos

            # flash_offset = FlashData + CffHeaderSize + LanguageBlockLength + fileCursor + 0x414
            flash_offset = flash_data + cff_header_size + language_block_length + file_cursor + 0x414

            segment = self._read_segment(seg_base, flash_offset)
            file_cursor += segment.segment_length
            block.segments.append(segment)

        return block

    def _read_segment(self, base_address, flash_offset):
        segment = FlashSegment()
        offset = base_address

        # Segment uses 2-byte bitflags (matches C++: ushort tmp; bitFlags = tmp)
        bitflags = struct.unpack_from('<H', self.data, offset)[0]
        offset += 2

        bf = BitflagReader(bitflags)

        # Field order matches CFFFlashSegment::readCFFData() exactly
        segment.from_address, offset = bf.read_4byte(self.data, offset)
        segment.segment_length, offset = bf.read_4byte(self.data, offset)
        _unk3, offset = bf.read_4byte(self.data, offset)
        segment.segment_name, offset = bf.read_string(self.data, offset, base_address)
        _unk5, offset = bf.read_4byte(self.data, offset)
        _unk6, offset = bf.read_4byte(self.data, offset)
        _unk7, offset = bf.read_4byte(self.data, offset)

        # Read the actual segment binary data from pre-calculated flash_offset
        segment.data = self._read_segment_data(flash_offset, segment.segment_length)

        return segment

    def _read_segment_data(self, flash_offset, length):
        if flash_offset < 0 or length <= 0 or flash_offset >= len(self.data):
            return b""
        end = min(flash_offset + length, len(self.data))
        return self.data[flash_offset:end]

    def get_all_segments(self):
        """Returns a flat list of all (block, segment) pairs."""
        results = []
        for block in self.data_blocks:
            for segment in block.segments:
                results.append((block, segment))
        return results

    def get_combined_binary(self):
        """Returns a full flash binary with segments placed at their correct addresses.

        Creates a 0xFF-filled buffer spanning from the lowest to highest segment
        address, then places each segment at its from_address offset — matching
        what a hardware flash programmer (KTag, Autotuner, etc.) would read.
        """
        # Collect all segments with valid address and data
        placed = []
        for block in self.data_blocks:
            for segment in block.segments:
                if segment.data and segment.segment_length > 0:
                    placed.append(segment)

        if not placed:
            return b""

        # Find the address range
        min_addr = min(s.from_address for s in placed)
        max_addr = max(s.from_address + len(s.data) for s in placed)

        # Create 0xFF-filled buffer (empty flash state)
        buf = bytearray(b'\xFF' * (max_addr - min_addr))

        # Place each segment at its correct address
        for seg in placed:
            offset = seg.from_address - min_addr
            buf[offset:offset + len(seg.data)] = seg.data

        return bytes(buf)