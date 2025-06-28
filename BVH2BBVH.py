from struct import pack
from typing import *
import re


def simdseek(file: BinaryIO, line: int) -> int:
	'''
	Returns a position on 64-byte boundaries.\n
	ARGS:
		file: A BinaryIO file
		line: Original Position\n
	RET:
		Aligned Position
		'''
	return file.seek(line * 64)


class BVH2BBVH:
	'''Convert a BioVision Hierarchy (BVH) file into a Binary BioVision Hierarchy (BBVH) structure.
		'''
	def __init__(self, bvh: TextIO, bbvh: str):
		'''Set up self.bbvh and self.bvh.\n
		ARGS: TextIO for self.bvh, bbvh is string path.
		'''
		self.bbvh = open(bbvh, "wb+", buffering=64)
		self.bvh = bvh.read()

	def extract_bvh_structure_and_data(self, bvh_text: str):
		'''Pass in bvh_text as string and get a BVH to dictionary in return'''
		joint_names = re.findall(r"(?:JOINT|ROOT)\s+(\w+)", bvh_text)
		joint_count = len(joint_names)

		channel_blocks = re.findall(r"CHANNELS\s+(\d+)\s+([^\n\r]+)", bvh_text)
		channels_per_joint = []
		total_channel_count = 0

		for count_str, channel_names in channel_blocks:
			count = int(count_str)
			total_channel_count += count
			channels_per_joint.append((count, channel_names.strip().split()))

		frame_count_match = re.search(r"Frames:\s*(\d+)", bvh_text)
		frame_count = int(frame_count_match.group(1)) if frame_count_match else 0

		frame_time_match = re.search(r"Frame Time:\s*([\d.]+)", bvh_text)
		frame_time = float(frame_time_match.group(1)) if frame_time_match else 0.0

		motion_block = bvh_text.split("Frame Time:")[-1]
		float_matches = re.findall(
			r"[-+]?\d*\.\d+(?:[eE][-+]?\d+)?|[-+]?\d+", motion_block
		)
		flat_motion_data = [float(val) for val in float_matches]

		return {
			"joint_count": joint_count,
			"channel_count": total_channel_count,
			"channels_per_joint": channels_per_joint,
			"frame_count": frame_count,
			"frame_time": frame_time,
			"motion_data": flat_motion_data,
		}

	def CreateHierarchy(self):
		'''Create Hierarchy Block'''
		ZRotate = 1
		YRotate = 2
		XRotate = 3
		XPos = 4
		YPos = 5
		ZPos = 6

		HIERARCHY = b"CRAH"
		self.bbvh.write(pack("I", 0x42425648))
		self.bbvh.write(b"\x00" * 60)

		simdseek(self.bbvh, 1)
		self.HPTR = self.bbvh.tell()
		self.bbvh.write(HIERARCHY)

		chunk_start = self.bbvh.tell()

		self.bbvh.write(b"\x00" * 60)

		BVHLIST = self.extract_bvh_structure_and_data(self.bvh)
		self.bbvh.seek(chunk_start + 5)

		self.bbvh.write(pack("B", BVHLIST["joint_count"]))
		self.bbvh.write(pack("B", BVHLIST["channel_count"]))
		self.bbvh.seek(4, 1)

		for i, (count, channel_list) in enumerate(BVHLIST["channels_per_joint"]):
			self.bbvh.write(pack("B", i))
			self.bbvh.write(pack("B", count))

			for ch in channel_list:
				if ch == "Xposition":
					self.bbvh.write(pack("B", XPos))
				elif ch == "Yposition":
					self.bbvh.write(pack("B", YPos))
				elif ch == "Zposition":
					self.bbvh.write(pack("B", ZPos))
				elif ch == "Xrotation":
					self.bbvh.write(pack("B", XRotate))
				elif ch == "Yrotation":
					self.bbvh.write(pack("B", YRotate))
				elif ch == "Zrotation":
					self.bbvh.write(pack("B", ZRotate))
				else:
					self.bbvh.write(pack("B", 0xFF))
		Size = self.bbvh.tell()
		SizeAlign = (Size + 63) &~63
		Padding = SizeAlign - Size
		self.bbvh.seek(chunk_start)
		self.bbvh.write(pack('H', SizeAlign))
		self.bbvh.seek(SizeAlign)
		self.bbvh.write(b'\x00' * Padding)
		self.BVHLIST = BVHLIST

	def CreateMotion(self, mode: int = 1):
		'''Mode : 1 = INT16 (scaled 100)'''
		'''Mode : 2 = Float32'''
		'''Mode : 3 = INT8 (scaled 10)'''

		MOTIONPTR = self.bbvh.tell()
		MOTION = b"NTOM"
		self.bbvh.write(MOTION)
		self.bbvh.write(b'\x00' * 12)

		self.bbvh.seek(MOTIONPTR + 8)
		self.bbvh.write(pack("I", self.BVHLIST["frame_count"]))
		self.bbvh.write(pack("f", self.BVHLIST["frame_time"]))

		cursor = 0
		for i in range(self.BVHLIST["frame_count"]):
			frame_start = self.bbvh.tell()
			self.bbvh.write(b'\x00\x00')  # Placeholder for frame length

			for joint_idx, (channel_count, _) in enumerate(self.BVHLIST["channels_per_joint"]):
				for c in range(channel_count):
					val = self.BVHLIST["motion_data"][cursor]
					if mode == 1:
						self.bbvh.write(pack("h", int(val * 100)))
					elif mode == 2:
						self.bbvh.write(pack("f", val))
					elif mode == 3:
						v = int(val * 10)
						v = max(-128, min(127, v))
						self.bbvh.write(pack("b", v))
					cursor += 1

			# Backpatch frame length
			end = self.bbvh.tell()
			frame_len = end - frame_start
			self.bbvh.seek(frame_start)

			if mode in (1, 3):
				self.bbvh.write(pack("B", frame_len | 0x80)) 
				self.bbvh.write(pack("B", end & 0xFF))        
			elif mode == 2:
				self.bbvh.write(pack("H", frame_len | 0x8000))  
				self.bbvh.write(pack("H", end & 0xFFFF))        

			self.bbvh.seek(end)

		EndSize = self.bbvh.tell()
		AlignedEnd = (EndSize + 63) & ~63
		Padding = AlignedEnd - EndSize
		self.bbvh.write(b'\x00' * Padding)

		self.bbvh.seek(MOTIONPTR + 4)
		self.bbvh.write(pack("I", AlignedEnd))
		self.bbvh.seek(AlignedEnd)
		self.MPTR = MOTIONPTR

	def WriteRelocation(self, introduceend: int, mode: int):
		'''Create optimised relocation delta pointers'''
		self.CreateHierarchy()
		self.CreateMotion(mode)
		chunkptr = self.bbvh.tell()
		formatheader = b'TIXE'
		self.bbvh.write(formatheader)
		self.bbvh.write(b'\x00' * 12)
		motionoffset = (self.MPTR >> 2) | 0x40
		hierarchyoffset = ((motionoffset - self.HPTR) >> 2) | 0x40
		self.bbvh.write(pack('B', motionoffset))
		self.bbvh.write(pack('B', hierarchyoffset))
		EndSize = self.bbvh.tell()
		AlignedEnd = (EndSize + 63) & ~63
		Padding = AlignedEnd - EndSize
		self.bbvh.write(b'\x00' * Padding)

		self.bbvh.seek(chunkptr + 4)
		self.bbvh.write(pack("I", AlignedEnd))
		self.bbvh.seek(4)
		self.bbvh.write(pack('I', AlignedEnd))
		self.bbvh.seek(AlignedEnd)
		if introduceend == 1:
			self.bbvh.write(pack('I', 0x454E4421))
		



		