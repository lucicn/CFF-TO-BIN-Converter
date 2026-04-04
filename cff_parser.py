"""
CFF (Caesar Flash File) Parser
Ported from CFFFlashFileTools (C++/Qt) to Python.
Parses Mercedes-Benz CFF containers and extracts flash segments as binary data.
"""

import struct
import io

# CRC32 lookup table (from CFFFlashContainer.cpp)
CRC_TABLE = [
    0x00000000, 0x77073096, 0xEE0E612C, 0x990951BA, 0x076DC419, 0x706AF48F,
    0xE963A535, 0x9E6495A3, 0x0EDB8832, 0x79DCB8A4, 0xE0D5E91B, 0x97D2D988,
    0x09B64C2B, 0x7EB17CBB, 0xE7B82D09, 0x90BF1D9F, 0x1DB71064, 0x6AB020F2,
    0xF3B97148, 0x84BE41DE, 0x1ADAD47D, 0x6DDDE4EB, 0xF4D4B551, 0x83D385C7,
    0x136C9856, 0x646BA8C0, 0xFD62F97A, 0x8A65C9EC, 0x14015C4F, 0x63066CD9,
    0xFA0F3D63, 0x8D080DF5, 0x20D02996, 0x57D74199, 0xCEDE30AD, 0xB9D94116,
    0x27B7D422, 0x50B0E4B2, 0xC9B9B508, 0xBEB6858E, 0x26D930AC, 0x51DE003A,
    0xC8D75180, 0xBFD06116, 0x21B4F4B5, 0x56B3C423, 0xCFBA9599, 0xB8BDA50F,
    0x2802B89E, 0x5F058808, 0xC60CD9B2, 0xB10BE924, 0x2F6F7C87, 0x58684C11,
    0xC1611DAB, 0xB6662D3D, 0x76DC4190, 0x01DB7106, 0x98D220BC, 0xEFD5102A,
    0x71B18589, 0x06B6B51F, 0x9FBFE4A5, 0xE8B8D433, 0x7807C9A2, 0x0F00F934,
    0x9609A88E, 0xE10E9818, 0x7F6A0D0B, 0x086D3D2D, 0x91646C97, 0xE6635C01,
    0x6B6B51F4, 0x1C6C6162, 0x856530D8, 0xF262004E, 0x6C0695ED, 0x1B01A57B,
    0x8208F4C1, 0xF50FC457, 0x65B0D9C6, 0x12B7E950, 0x8BBEB8EA, 0xFCB9887C,
    0x62DD1DDF, 0x15DA2D49, 0x8CD37CF3, 0xFBD44C65, 0x4DB26158, 0x3AB551CE,
    0xA3BC0074, 0xD4BB30E2, 0x4ADFA541, 0x3DD895D7, 0xA4D1C46D, 0xD3D6F4FB,
    0x4369E96A, 0x346ED9FC, 0xAD678846, 0xDA60B8D0, 0x44042D73, 0x33031DE5,
    0xAA0A4C5F, 0xDD0D7AC9, 0x5005713C, 0x270241AA, 0xBE0B1010, 0xC90C2086,
    0x5768B525, 0x206F85B3, 0xB966D409, 0xCE61E49F, 0x5E0C5ACA, 0x29021C5C,
    0xB00C06E6, 0xC70AD070, 0x5BDEF796, 0x2CD99816, 0xB5D0CF31, 0xC2D7FFA7,
    0x32D186B2, 0x45D6B3B4, 0xDCDFD20E, 0xABD89098, 0x3D6EE63B, 0x4A69D6AD,
    0xD3609017, 0xA4678019, 0x34E0D488, 0x43E7A41E, 0xDAEE95A4, 0xADD8A532,
    0x33BC2191, 0x44BB1107, 0xDBB240BD, 0xACB5702B, 0x22B8F08A, 0x55BFE01C,
    0xCCB6D1A6, 0xBBB1B130, 0x246D0693, 0x53603605, 0xCA6967BF, 0xBD6E5729,
    0x2DD1D8B8, 0x5AD6E82E, 0xC3DFB994, 0xB4D88963, 0x2A4C0E61, 0x5D4B1EF7,
    0xC445284D, 0xB34258DB, 0x24BEB2CE, 0x53B98258, 0xCAB0D3E2, 0xBDB3C374,
    0x2D0DD8D7, 0x5A0AE841, 0xC303B9FB, 0xB400896D, 0xBB0DC5EF, 0xCC0BD679,
    0x550CA6C3, 0x2209B655, 0xBC6E23F6, 0xCB690360, 0x5260F2DA, 0x2567D24C,
    0xB5DFCF5D, 0xC2D8BECB, 0x5BD1EF71, 0x2CD6DFE7, 0xBA4AE244, 0xCD4DD2D2,
    0x54446368, 0x234553FE, 0x13D9B865, 0x64DE88F3, 0x0BD7D949, 0x7CD0E9DF,
    0xE2B47C7C, 0x959B4CEA, 0x0C921D50, 0x7B952BC6, 0xEB0D2A57, 0x9C0A1AC1,
    0x050A397B, 0x720D09ED, 0xEC634E4E, 0x9B6478D8, 0x0827A962, 0x7F2099F4,
    0x6E17E745, 0x192087D3, 0x8029D669, 0xF72EB6FF, 0x692B075C, 0x1E2C37CA,
    0x87255670, 0xF02266E6, 0x6095BF77, 0x179287E1, 0x8E9BD65B, 0xF99CE6CD,
    0x673A736E, 0x101D63F8, 0x89144242, 0xFE1372D4, 0x8D03D2B7, 0xFA043021,
    0x6303619B, 0x1404510D, 0x8A61C4AE, 0xFD668438, 0x6469D582, 0x13E6E514,
    0x836FD985, 0xF468E913, 0x6D61B8A9, 0x1A66A83F, 0x845B379C, 0xF35C070A,
    0x6A5556B0, 0x1D525626, 0x046BEB95, 0x73626B03, 0xEA6B3AB9, 0x9D6C0A2F,
    0x03280B8C, 0x7421CB1A, 0xED28DAA0, 0x9A2F0A36, 0x0AB00CA7, 0x7DB73D31,
    0xE4BE6C8B, 0x93B95E1D, 0x0DBD50BE, 0x7ABA4028, 0xE3B31192, 0x94B42104,
    0xA4D8564B, 0xD3DF65DD, 0x4AD63467, 0x3DD104F1, 0xA3B59152, 0xD4B2A1C4,
    0x4DBBB07E, 0x3ABCA0E8, 0xAAB40D79, 0xDDB33DEF, 0x44BA6C55, 0x33BD5CC3,
    0xADD90460, 0xDADE34F6, 0x43D7254C, 0x34D015DA,
]

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
            val = struct.unpack_from('<i', data, offset)[0]
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
            end = data.index(b'\x00', str_pos)
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
            crc = CRC_TABLE[(crc ^ byte) & 0xFF] ^ (crc >> 8)
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

        bf = BitflagReader(bitflags)

        block.qualifier, offset = bf.read_string(self.data, offset, base_address)
        _desc_str, offset = bf.read_string(self.data, offset, base_address)
        block.data_block_type, offset = bf.read_string(self.data, offset, base_address)
        _encryption_mode, offset = bf.read_string(self.data, offset, base_address)

        _unk_b, offset = bf.read_4byte(self.data, offset)

        _flash_data_segment_addr, offset = bf.read_4byte(self.data, offset)
        _flash_data_segment_count, offset = bf.read_4byte(self.data, offset)

        block.flash_data_info, offset = bf.read_string(self.data, offset, base_address)

        _unk_key, offset = bf.read_4byte(self.data, offset)
        _unk_key2, offset = bf.read_4byte(self.data, offset)

        segment_table_count, offset = bf.read_4byte(self.data, offset)
        segment_table_offset, offset = bf.read_4byte(self.data, offset)

        _unk_g, offset = bf.read_4byte(self.data, offset)
        _unk_h, offset = bf.read_4byte(self.data, offset)
        _unk_i, offset = bf.read_4byte(self.data, offset)

        block.file_name, offset = bf.read_string(self.data, offset, base_address)

        _unk_k, offset = bf.read_4byte(self.data, offset)

        # Parse segments
        for seg_idx in range(segment_table_count):
            seg_entry_addr = segment_table_offset + base_address + (seg_idx * 4)
            seg_pos = struct.unpack_from('<i', self.data, seg_entry_addr)[0]
            seg_base = segment_table_offset + base_address + seg_pos

            segment = self._read_segment(seg_base, cff_header_size, language_block_length)
            block.segments.append(segment)

        return block

    def _read_segment(self, base_address, cff_header_size, language_block_length):
        segment = FlashSegment()
        offset = base_address

        bitflags = struct.unpack_from('<H', self.data, offset)[0]
        offset += 2

        bf = BitflagReader(bitflags)

        segment.segment_name, offset = bf.read_string(self.data, offset, base_address)

        _unk3, offset = bf.read_4byte(self.data, offset)
        segment.from_address, offset = bf.read_4byte(self.data, offset)
        _unk5, offset = bf.read_4byte(self.data, offset)
        _unk6, offset = bf.read_4byte(self.data, offset)
        _unk7, offset = bf.read_4byte(self.data, offset)
        segment.segment_length, offset = bf.read_4byte(self.data, offset)

        # Calculate flash data offset
        flash_offset = STUB_HEADER_SIZE + 4 + cff_header_size + language_block_length
        # Read the actual segment binary data
        segment.data = self._read_segment_data(flash_offset, segment.segment_length)

        return segment

    def _read_segment_data(self, flash_offset, length):
        if flash_offset + length > len(self.data):
            available = len(self.data) - flash_offset
            if available > 0:
                return self.data[flash_offset:flash_offset + available]
            return b""
        return self.data[flash_offset:flash_offset + length]

    def get_all_segments(self):
        """Returns a flat list of all (block, segment) pairs."""
        results = []
        for block in self.data_blocks:
            for segment in block.segments:
                results.append((block, segment))
        return results

    def get_combined_binary(self):
        """Returns all segment data combined into a single binary blob."""
        parts = []
        for block in self.data_blocks:
            for segment in block.segments:
                if segment.data:
                    parts.append(segment.data)
        return b"".join(parts)