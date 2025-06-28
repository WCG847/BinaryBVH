import tkinter as tk
from tkinter import filedialog, messagebox
from BVH2BBVH import BVH2BBVH  # Import your cursed masterpiece
import os

class BBVHGUI:
	def __init__(self, master):
		self.master = master
		master.title("BBVH Tool")

		self.label = tk.Label(master, text="BVH to BBVH Binary Tool")
		self.label.pack(pady=10)

		self.bvh_path = tk.StringVar()
		self.bbvh_path = tk.StringVar()
		self.mode = tk.IntVar(value=1)
		self.flag = tk.IntVar(value=1)

		tk.Button(master, text="Select BVH File", command=self.select_bvh).pack(pady=5)
		tk.Entry(master, textvariable=self.bvh_path, width=60).pack()

		tk.Button(master, text="Select BBVH Output", command=self.select_bbvh).pack(pady=5)
		tk.Entry(master, textvariable=self.bbvh_path, width=60).pack()

		tk.Label(master, text="Encoding Mode:").pack(pady=5)
		tk.Radiobutton(master, text="16-Bit Integer", variable=self.mode, value=1).pack()
		tk.Radiobutton(master, text="Float (Single Precision)", variable=self.mode, value=2).pack()
		tk.Radiobutton(master, text="8-Bit Integer", variable=self.mode, value=3).pack()

		tk.Label(master, text="Add END footer?:").pack(pady=5)
		tk.Radiobutton(master, text="yes", variable=self.flag, value=1).pack()
		tk.Radiobutton(master, text="no", variable=self.flag, value=0).pack()

		tk.Button(master, text="Convert", command=self.convert).pack(pady=15)

		self.status = tk.Label(master, text="", fg="green")
		self.status.pack()

	def select_bvh(self):
		file_path = filedialog.askopenfilename(filetypes=[("BVH files", "*.bvh")])
		if file_path:
			self.bvh_path.set(file_path)

	def select_bbvh(self):
		file_path = filedialog.asksaveasfilename(defaultextension=".bbvh", filetypes=[("BBVH files", "*.bbvh")])
		if file_path:
			self.bbvh_path.set(file_path)

	def convert(self):
		bvh_file = self.bvh_path.get()
		bbvh_file = self.bbvh_path.get()
		mode = self.mode.get()
		flag = self.flag.get()

		if not os.path.exists(bvh_file):
			messagebox.showerror("Error", "BVH file not found.")
			return

		if not bbvh_file:
			messagebox.showerror("Error", "Please specify a BBVH output path.")
			return

		try:
			with open(bvh_file, 'r') as f:
				converter = BVH2BBVH(f, bbvh_file)
				converter.WriteRelocation(flag, mode)  # Calls all methods internally
				self.status.config(text="✅ BBVH written successfully!")
		except Exception as e:
			self.status.config(text="❌ Conversion failed.")
			messagebox.showerror("Conversion Error", str(e))

def main():
	root = tk.Tk()
	app = BBVHGUI(root)
	root.mainloop()

if __name__ == "__main__":
	main()
