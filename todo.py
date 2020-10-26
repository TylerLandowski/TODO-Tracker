# TODO parameters for pretty colors
# TODO ? set width of grid to be maximum length OR length of header name
# TODO ? store previously 'chosen' items that user didn't want
# TODO give Choose an 'optimal' checkbox for choosing best item
# TODO color code Choose results
# TODO NAMING SCHEMES - change 'item' to 'task'

WINDOW_GEOMETRY = "780x320"
FONT            = "courier 8"

import os
import datetime
from functools import partial
import pandas as pd
from pandas import DataFrame
import tkinter as tk
from tkinter import ttk, messagebox
from random import randint

class ItemHandler:
	_columns: dict = {
		# On creation
		"name": str,
		"description": str,
		"length": str,
		"reviewable": bool,
		"in_progress": bool,
		"priority": str,
		"urgency": str,
		"enjoyability": str,
		"complete": bool,
		"creation_date": "datetime64[ns]",
		# After creation
		"start_date": "datetime64[ns]",
		"deadline": "datetime64[ns]",
	}
	
	# Options for combo boxes, as well as useful information for them
	_cboptions: dict = {
		"length": {
			"< 1 hr"         : {"color": "red"},
			"1 hr - 1 day"   : {"color": "indian red"},
			"1 day"          : {"color": "orange"},
			"1 day - 1 wk"   : {"color": "gold"},
			"1 wk"           : {"color": "lime green"},
			"1 wk - 1 mth"   : {"color": "green"},
			"Several months" : {"color": "black"},
			"<= 1 year"      : {"color": "gray"},
			"Several years"  : {"color": "light gray"},
		},
		
		"priority": {
			"Very High" : {"color": "red"},
			"High"      : {"color": "orange"},
			"Medium"    : {"color": "lime green"},
			"Low"       : {"color": "black"},
			"Very Low"  : {"color": "gray"},
		},
		
		"urgency": {
			"ASAP"          : {"color": "red"},
			"Soon"          : {"color": "orange"},
			"When ready"    : {"color": "lime green"},
			"In the future" : {"color": "black"},
			"Whenever"      : {"color": "gray"},
		},
		
		"enjoyability": {
			"Fun"    : {"color": "red"},
			"Okay"   : {"color": "lime green"},
			"Boring" : {"color": "gray"},
		}
	}
	
	# Stores all items
	items: DataFrame
	
	# Adds a row to the data frame
	def add_item(self, item: dict):
		self.items = self.items.append(item, ignore_index=True)
		self.export_items()
		
	# Removes an item that's not completed
	def delete_incomplete_item(self, name: str) -> None:
		df = self.items
		
		self.items.drop(
			df.loc[
				(df["complete"] == False) &
				(df["name"] == name)
			].index,
			inplace=True
		)
		self.export_items()
		
	# Updates the columns values for the incomplete item's row in dataframe
	# with the given name, using a col:val dictionary
	# Returns False if new name is taken, and fails to update
	def update_incomplete_item(self, name: str, cols: dict):
		df = self.items
		
		name_changed = "name" in cols.keys() and cols["name"] != name
		# Check if name already exists
		if name_changed:
			name_taken = cols["name"] in df["name"].unique()
			if name_taken: return False
		
		row_idx = df[(df["complete"] == False) & (df["name"] == name)].index[0]
		for col, val in cols.items():
			self.items.iloc[row_idx, df.columns.get_loc(col)] = val
		self.export_items()
		return True
	
	# Exports the items dataframe to CSV
	def export_items(self) -> None:
		self.items.to_csv("items.csv", index=False)

	# Reads the items CSV into the items dataframe, or creates a new one
	def load_items(self) -> None:
		# Create items file
		if not os.path.exists("items.csv"):
			self.items = DataFrame(columns = self._columns)
			self.set_item_dtypes()
			self.export_items()
		# Read items file
		else:
			self.items = pd.read_csv("items.csv")
			self.set_item_dtypes()
			
	# Set dtypes of items and convert to categoricals
	def set_item_dtypes(self) -> None:
		self.items = self.items.astype(self._columns)
		# Convert to categoricals for sorting
		for col in ["length", "priority", "urgency", "enjoyability"]:
			self.items[col] = pd.Categorical(
				self.items[col],
				categories=list(ItemHandler._cboptions[col].keys()), ordered=True
			)
	
class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
		
class GUI:
	items_handler : ItemHandler
	win_main      : tk.Tk
	tab_control   : ttk.Notebook
	tab_choose    : tk.Frame
	tab_insert    : tk.Frame
	tab_view      : ScrollableFrame
	items_disp    : list = list() # Items displayed in the View tab's grid
	sort_col      : str  = "" # Column used to sort
	sort_asc      : bool = True            # Sort ascending?
	# Insert Item
	txt_name   : tk.Entry     # Name
	txt_desc   : tk.Text      # Description
	cbx_leng   : ttk.Combobox # Length
	cbx_prior  : ttk.Combobox # Priority
	cbx_urge   : ttk.Combobox # Urgency
	cbx_enjoy  : ttk.Combobox # Enjoyability
	int_review : tk.IntVar    # Is reviewable
	# Choose Item
	cbx_leng_min    : ttk.Combobox    # Length Min
	cbx_leng_max    : ttk.Combobox    # Length Max
	cbx_prior_min   : ttk.Combobox    # Priority Min
	cbx_urge_min    : ttk.Combobox    # Urgency Min
	cbx_enjoy_min   : ttk.Combobox    # Enjoyability Min
	frm_chosen_item : tk.Frame = None # Displays the chosen item
	# Edit Item (popup window)
	win_edit             : tk.Tk        # View popup window
	txt_edit_name        : tk.Entry     # Name
	txt_edit_desc        : tk.Text      # Description
	cbx_edit_leng        : ttk.Combobox # Length
	cbx_edit_prior       : ttk.Combobox # Priority
	cbx_edit_urge        : ttk.Combobox # Urgency
	cbx_edit_enjoy       : ttk.Combobox # Enjoyability
	int_edit_review      : tk.IntVar    # Is reviewable
	int_edit_in_progress : tk.IntVar    # In progress
	int_edit_complete    : tk.IntVar    # Complete
	remove_frm_chosen    : bool         # Whether to remove frame in Choose
	
	def __init__(self, items_handler: ItemHandler):
		self.items_handler = items_handler
		
	# Displays items as rows in View tab
	# Holds them in items_disp for easy removal
	def disp_items(self, sort_col: str, keep_sort: bool = False):
		# Sort all items
		if sort_col == self.sort_col and not keep_sort:
			self.sort_asc = not self.sort_asc
		else:
			self.sort_asc = True
		self.sort_col = sort_col
		self.items_handler.items.sort_values(
			by=[sort_col, "creation_date"],
			inplace=True,
			ascending=self.sort_asc
		)
		self.items_handler.items.reset_index(drop=True, inplace=True)
		
		# Clear items_disp from screen if already drawn
		for lbl in self.items_disp:
			lbl.destroy()
		self.items_disp = list()
		
		# Make a label to be placed in a cell
		def make_label(width: int, col: str, row_idx: int, col_idx: int):
			fg = "black"
			bg = None
			if col == sort_col: bg = "white"
			if col in ["length", "priority", "urgency", "enjoyability"]:
				fg = ItemHandler._cboptions[col][item[col]]["color"]
			if   col == "in_progress"   : text = "✓" if item["in_progress"] else ""
			elif col == "creation_date" : text = item[col].date()
			else                        : text = item[col]
			lbl = tk.Label(
				self.tab_view.scrollable_frame,
				width = width,
				text = text,
				fg = fg,
				bg = bg
			)
			self.items_disp.append(lbl)
			lbl.grid(row=row_idx+1, column=col_idx, sticky="w")
		
		# Add each row
		items = self.items_handler.items
		items = items[items["complete"] == False]
		for idx, item in items.iterrows():
			self.tab_view.scrollable_frame.grid_rowconfigure(idx+1, weight=1)
			make_label(30, "name"         , idx, 0)
			make_label(13, "length"       , idx, 1)
			make_label(9 , "priority"     , idx, 2)
			make_label(13, "urgency"      , idx, 3)
			make_label(6 , "enjoyability" , idx, 4)
			make_label(10, "creation_date", idx, 5)
			make_label(6 , "in_progress"  , idx, 6)
			btn = tk.Button(
				self.tab_view.scrollable_frame,
				width=5,
				text="Edit",
				command=partial(self.edit_item, item["name"])
			)
			self.items_disp.append(btn)
			btn.grid(row=idx+1, column=7, sticky="w")
		
	# Sets the item to be in_progress
	def commit_item(self, name: str):
		self.frm_chosen_item.destroy()
		self.items_handler.update_incomplete_item(
			name, {"in_progress": True}
		)
		self.disp_items(self.sort_col, keep_sort = True)
	
	# Displays a randomly generated item following given parameters
	def choose_item(self):
		# Remove previous choice
		if self.frm_chosen_item != None:
			self.frm_chosen_item.pack_forget()
		
		# Create and store the choice as a frame
		frm = tk.Frame(self.tab_choose, borderwidth=2, relief=tk.RAISED)
		frm.pack(side=tk.TOP)
		self.frm_chosen_item = frm
		
		# Generate a random item
		items = self.items_handler.items
		items = items[
			(items["complete"]     == False                   ) &
			(items["in_progress"]  == False                   ) &
			(items["length"]       >= self.cbx_leng_min .get()) &
			(items["length"]       <= self.cbx_leng_max .get()) &
			(items["priority"]     <= self.cbx_prior_min.get()) &
			(items["urgency"]      <= self.cbx_urge_min .get()) &
			(items["enjoyability"] <= self.cbx_enjoy_min.get())
		]
		res_len = len(items)
		if res_len < 1:
			tk.Label(frm, text="No items found!").pack()
			return
		item = items.iloc[randint(0, res_len - 1)]
		
		# Display the item
		def make_row(name: str, col: str):
			fg = "black"
			if col in ["length", "priority", "urgency", "enjoyability"]:
				fg = ItemHandler._cboptions[col][item[col]]["color"]
			subframe = tk.Frame(frm)
			tk.Label(subframe, text=name, width=13, anchor="w").pack(side=tk.LEFT)
			tk.Label(subframe, text=item[col], anchor="w", fg=fg).pack(side=tk.LEFT, fill=tk.X, expand=1)
			subframe.pack(side=tk.TOP, anchor="w", fill=tk.X)
		make_row("Name"        , "name")
		make_row("Length"      , "length")
		make_row("Priority"    , "priority")
		make_row("Urgency"     , "urgency")
		make_row("Enjoyability", "enjoyability")
		
		# Display buttons
		subframe = tk.Frame(frm)
		tk.Button(subframe, text="Commit", command=partial(self.commit_item, item["name"])).pack(fill=tk.X)
		tk.Button(subframe, text="Edit", command=partial(self.edit_item, item["name"], True)).pack(fill=tk.X)
		subframe.pack(side=tk.TOP, anchor="w", fill=tk.X)
	
	# Opens a popup for viewing the item
	def edit_item(self, name: str, called_by_choose: bool = False):
		self.win_edit = tk.Toplevel()
		self.win_edit.grab_set()
		self.win_edit.title("Edit Task")
		self.win_edit.geometry(WINDOW_GEOMETRY)
		self.win_edit.option_add("*Font", FONT)
		
		items = self.items_handler.items
		items = items[items["complete"] == False]
		item = items[items["name"] == name].iloc[0]
		
		# Build the UI
		frm_edit = tk.Frame(self.win_edit)
		
		# Name
		subframe = tk.Frame(frm_edit)
		tk.Label(subframe, text="Name", width=12, borderwidth=2, anchor="w").pack(side=tk.LEFT)
		self.txt_edit_name = tk.Entry(subframe)
		self.txt_edit_name.insert(0, item["name"])
		self.txt_edit_name.pack(side=tk.LEFT, fill=tk.X, expand=1)
		subframe.pack(side=tk.TOP, fill=tk.X)
		
		# Description
		subframe = tk.Frame(frm_edit)
		tk.Label(subframe, text="Description", width=12, borderwidth=2, anchor="w").pack(side=tk.LEFT)
		self.txt_edit_desc = tk.Text(subframe, height=5)
		self.txt_edit_desc.insert(1.0, item["description"])
		self.txt_edit_desc.pack(side=tk.LEFT, fill=tk.X, expand=1)
		subframe.pack(side=tk.TOP, fill=tk.X)
		
		# Length
		subframe = tk.Frame(frm_edit)
		tk.Label(subframe, text="Length", width=12, borderwidth=2, anchor="w").pack(side=tk.LEFT)
		self.cbx_edit_leng = ttk.Combobox(subframe, state="readonly", values=list(ItemHandler._cboptions["length"].keys()))
		self.cbx_edit_leng.set(item["length"])
		self.cbx_edit_leng.pack(side=tk.LEFT, fill=tk.X, expand=1)
		subframe.pack(side=tk.TOP, fill=tk.X)
		
		# Priority
		subframe = tk.Frame(frm_edit)
		tk.Label(subframe, text="Priority", width=12, borderwidth=2, anchor="w").pack(side=tk.LEFT)
		self.cbx_edit_prior = ttk.Combobox(subframe, state="readonly", values=list(ItemHandler._cboptions["priority"].keys()))
		self.cbx_edit_prior.set(item["priority"])
		self.cbx_edit_prior.pack(side=tk.LEFT, fill=tk.X, expand=1)
		subframe.pack(side=tk.TOP, fill=tk.X)
		
		# Urgency
		subframe = tk.Frame(frm_edit)
		tk.Label(subframe, text="Urgency", width=12, borderwidth=2, anchor="w").pack(side=tk.LEFT)
		self.cbx_edit_urge = ttk.Combobox(subframe, state="readonly", values=list(ItemHandler._cboptions["urgency"].keys()))
		self.cbx_edit_urge.set(item["urgency"])
		self.cbx_edit_urge.pack(side=tk.LEFT, fill=tk.X, expand=1)
		subframe.pack(side=tk.TOP, fill=tk.X)
		
		# Enjoyability
		subframe = tk.Frame(frm_edit)
		tk.Label(subframe, text="Enjoyability", width=12, borderwidth=2, anchor="w").pack(side=tk.LEFT)
		self.cbx_edit_enjoy = ttk.Combobox(subframe, state="readonly", values=list(ItemHandler._cboptions["enjoyability"].keys()))
		self.cbx_edit_enjoy.set(item["enjoyability"])
		self.cbx_edit_enjoy.pack(side=tk.LEFT, fill=tk.X, expand=1)
		subframe.pack(side=tk.TOP, fill=tk.X)
		
		# Checkboxes
		subframe = tk.Frame(frm_edit)
		self.int_edit_review = tk.IntVar(value=int(item["reviewable"]))
		cb = tk.Checkbutton(subframe, variable=self.int_edit_review, text="Is reviewable")
		if item["reviewable"]: cb.select()
		cb.pack(side=tk.LEFT)
		
		self.int_edit_complete = tk.IntVar()
		tk.Checkbutton(subframe, variable=self.int_edit_complete, text="Complete").pack(side=tk.LEFT)
		
		self.int_edit_in_progress = tk.IntVar(value=int(item["in_progress"]))
		cb = tk.Checkbutton(subframe, variable=self.int_edit_in_progress, text="In Progress")
		if item["in_progress"]: cb.select()
		cb.pack(side=tk.LEFT)
		subframe.pack()
		
		# Buttons
		self.remove_frm_chosen = False # Whether or not we should remove the frame in Choose tab
		def apply_wrapper(name):
			self.remove_frm_chosen = self.int_edit_complete.get() or self.int_edit_in_progress.get()
			self.edit_apply(name)
		def delete_wrapper(name):
			self.remove_frm_chosen = True
			self.edit_delete(name)
		tk.Button(frm_edit, text="Apply",  command=partial(apply_wrapper , name)).pack(fill=tk.X)
		tk.Button(frm_edit, text="Delete", command=partial(delete_wrapper, name)).pack(fill=tk.X)
		
		frm_edit.pack()
		
		self.win_main.wait_window(self.win_edit)
		self.disp_items(self.sort_col, keep_sort=True)
		
		#print(called_by_choose, remove_frm_chosen)
		if called_by_choose and self.remove_frm_chosen:
			self.frm_chosen_item.destroy()
				
	# Applies views to the item in the dataframe and View tab
	def edit_apply(self, name: str):
		result = self.items_handler.update_incomplete_item(
			name, {
				"name":          self.txt_edit_name.get(),
				"description":   self.txt_edit_desc.get("1.0", tk.END)[:-1],
				"length":        self.cbx_edit_leng.get(),
				"reviewable":    bool(self.int_edit_review .get()),
				"in_progress":   bool(self.int_edit_in_progress.get()),
				"priority":      self.cbx_edit_prior.get(),
				"urgency":       self.cbx_edit_urge.get(),
				"enjoyability":  self.cbx_edit_enjoy.get(),
				"complete":      bool(self.int_edit_complete.get()),
			}
		)
		
		# Was name already taken?
		if result == False:
			messagebox.showerror(title="ERROR", message="Name already exists for another uncompleted task. Uncompleted task names must be unique")
		
	# Deletes the given item from the dataframe and View tab
	def edit_delete(self, name: str):
		self.items_handler.delete_incomplete_item(name)
		self.win_edit.destroy()
			
	# Inserts an item into the dataframe, writes the CSV, and updates View tab
	def insert_item(self):
		name = self.txt_name.get()
		if name == "":
			messagebox.showerror(title="ERROR", message="Please enter a name")
			return
		cur_names = self.items_handler.items
		cur_names = cur_names[cur_names["complete"] == False]["name"].values
		if name in cur_names:
			messagebox.showerror(title="ERROR", message="Name already exists for another uncompleted task. Uncompleted task names must be unique")
			return
		item = {
			"name":          self.txt_name.get(),
			"description":   self.txt_desc.get("1.0", tk.END)[:-1],
			"length":        self.cbx_leng.get(),
			"reviewable":    self.int_review.get(),
			"in_progress":   False,
			"priority":      self.cbx_prior.get(),
			"urgency":       self.cbx_urge.get(),
			"enjoyability":  self.cbx_enjoy.get(),
			"creation_date": datetime.datetime.now(),
			"complete":      False,
			#"start_date": None,
			#"deadline": None,
		}
		# Add to data frame and export
		self.items_handler.add_item(item)
		# Clear fields
		self.txt_name  .delete(0  , tk.END)
		self.txt_desc  .delete(1.0, tk.END)
		self.cbx_leng  .set(list(ItemHandler._cboptions["length"      ].keys())[0])
		self.cbx_prior .set(list(ItemHandler._cboptions["priority"    ].keys())[0])
		self.cbx_urge  .set(list(ItemHandler._cboptions["urgency"     ].keys())[0])
		self.cbx_enjoy .set(list(ItemHandler._cboptions["enjoyability"].keys())[0])
		self.int_review.set(False)
		# Re-display items
		self.items_handler.set_item_dtypes()
		self.disp_items(self.sort_col, keep_sort=True)
		
	# TODO
	def build_tab_insert(self):
		self.tab_insert = tk.Frame(self.tab_control)
		
		# Name
		subframe = tk.Frame(self.tab_insert)
		tk.Label(subframe, text="Name", width=12, borderwidth=2, anchor="w").pack(side=tk.LEFT)
		self.txt_name = tk.Entry(subframe)
		self.txt_name.pack(side=tk.LEFT, fill=tk.X, expand=1)
		subframe.pack(side=tk.TOP, fill=tk.X)
		
		# Description
		subframe = tk.Frame(self.tab_insert)
		tk.Label(subframe, text="Description", width=12, borderwidth=2, anchor="w").pack(side=tk.LEFT)
		self.txt_desc = tk.Text(subframe, height=5)
		self.txt_desc.pack(side=tk.LEFT, fill=tk.X, expand=1)
		subframe.pack(side=tk.TOP, fill=tk.X)
		
		# Length
		subframe = tk.Frame(self.tab_insert)
		tk.Label(subframe, text="Length", width=12, borderwidth=2, anchor="w").pack(side=tk.LEFT)
		self.cbx_leng = ttk.Combobox(subframe, state="readonly", values=list(ItemHandler._cboptions["length"].keys()))
		self.cbx_leng.set(list(ItemHandler._cboptions["length"].keys())[0])
		self.cbx_leng.pack(side=tk.LEFT, fill=tk.X, expand=1)
		subframe.pack(side=tk.TOP, fill=tk.X)
		
		# Priority
		subframe = tk.Frame(self.tab_insert)
		tk.Label(subframe, text="Priority", width=12, borderwidth=2, anchor="w").pack(side=tk.LEFT)
		self.cbx_prior = ttk.Combobox(subframe, state="readonly", values=list(ItemHandler._cboptions["priority"].keys()))
		self.cbx_prior.set(list(ItemHandler._cboptions["priority"].keys())[0])
		self.cbx_prior.pack(side=tk.LEFT, fill=tk.X, expand=1)
		subframe.pack(side=tk.TOP, fill=tk.X)
		
		# Urgency
		subframe = tk.Frame(self.tab_insert)
		tk.Label(subframe, text="Urgency", width=12, borderwidth=2, anchor="w").pack(side=tk.LEFT)
		self.cbx_urge = ttk.Combobox(subframe, state="readonly", values=list(ItemHandler._cboptions["urgency"].keys()))
		self.cbx_urge.set(list(ItemHandler._cboptions["urgency"].keys())[0])
		self.cbx_urge.pack(side=tk.LEFT, fill=tk.X, expand=1)
		subframe.pack(side=tk.TOP, fill=tk.X)
		
		# Enjoyability
		subframe = tk.Frame(self.tab_insert)
		tk.Label(subframe, text="Enjoyability", width=12, borderwidth=2, anchor="w").pack(side=tk.LEFT)
		self.cbx_enjoy = ttk.Combobox(subframe, state="readonly", values=list(ItemHandler._cboptions["enjoyability"].keys()))
		self.cbx_enjoy.set(list(ItemHandler._cboptions["enjoyability"].keys())[0])
		self.cbx_enjoy.pack(side=tk.LEFT, fill=tk.X, expand=1)
		subframe.pack(side=tk.TOP, fill=tk.X)
		
		# Checkboxes
		subframe = tk.Frame(self.tab_insert)
		self.int_review = tk.IntVar()
		tk.Checkbutton(subframe, variable=self.int_review, text="Is reviewable").pack(side=tk.LEFT)
		subframe.pack()
		
		# Insert button
		tk.Button(self.tab_insert, text="Insert", command=self.insert_item).pack(fill=tk.X)
		
		self.tab_insert.pack()
		
	def build_tab_view(self):
		self.tab_view = ScrollableFrame(self.tab_control)
		
		# Not sure this does anything
		for i in range(8):
			self.tab_view.scrollable_frame.grid_columnconfigure(i, weight=1)
		self.tab_view.scrollable_frame.grid_rowconfigure(0, weight=1)
		
		# Makes a column header (button)
		def make_col(text, width, data, col):
			tk.Button(self.tab_view.scrollable_frame, text=text, width=width, relief=tk.RAISED, command=lambda: self.disp_items(data)).grid(row=0, column=col, sticky="w")
		
		# Column headers
		make_col("Name"    , 30, "name"         , 0)
		make_col("Length"  , 13, "length"       , 1)
		make_col("Priority", 9 , "priority"     , 2)
		make_col("Urgency" , 13, "urgency"      , 3)
		make_col("Enjoy"   , 6 , "enjoyability" , 4)
		make_col("Created" , 10, "creation_date", 5)
		make_col("InProg"  , 6 , "in_progress"  , 6)
		tk.Button(self.tab_view.scrollable_frame, text="Edit", width=5, relief=tk.RAISED).grid(row=0, column=7, sticky="w")
		
		# Items (and initial sorting)
		self.disp_items("creation_date")
		
		self.tab_view.pack()
		
	def build_tab_choose(self):
		self.tab_choose = tk.Frame(self.tab_control)
		# cboptions = ItemHandler._cboptions["length"].keys() # alias
		
		# Length Min
		subframe = tk.Frame(self.tab_choose)
		tk.Label(subframe, text="Length       Min", width=16, borderwidth=2, anchor="w").pack(side=tk.LEFT)
		self.cbx_leng_min = ttk.Combobox(subframe, state="readonly", values=list(ItemHandler._cboptions["length"].keys()))
		self.cbx_leng_min.set(list(ItemHandler._cboptions["length"].keys())[0])
		self.cbx_leng_min.pack(side=tk.LEFT, fill=tk.X, expand=1)
		subframe.pack(side=tk.TOP, fill=tk.X)
		
		# Length Max
		subframe = tk.Frame(self.tab_choose)
		tk.Label(subframe, text="             Max", width=16, borderwidth=2, anchor="w").pack(side=tk.LEFT)
		self.cbx_leng_max = ttk.Combobox(subframe, state="readonly", values=list(ItemHandler._cboptions["length"].keys()))
		self.cbx_leng_max.set(list(ItemHandler._cboptions["length"].keys())[0])
		self.cbx_leng_max.pack(side=tk.LEFT, fill=tk.X, expand=1)
		subframe.pack(side=tk.TOP, fill=tk.X)
		
		# Priority Min
		subframe = tk.Frame(self.tab_choose)
		tk.Label(subframe, text="Priority     Min", width=16, borderwidth=2, anchor="w").pack(side=tk.LEFT)
		self.cbx_prior_min = ttk.Combobox(subframe, state="readonly", values=list(ItemHandler._cboptions["priority"].keys()))
		self.cbx_prior_min.set(list(ItemHandler._cboptions["priority"].keys())[0])
		self.cbx_prior_min.pack(side=tk.LEFT, fill=tk.X, expand=1)
		subframe.pack(side=tk.TOP, fill=tk.X)
		
		# Urgency Min
		subframe = tk.Frame(self.tab_choose)
		tk.Label(subframe, text="Urgency      Min", width=16, borderwidth=2, anchor="w").pack(side=tk.LEFT)
		self.cbx_urge_min = ttk.Combobox(subframe, state="readonly", values=list(ItemHandler._cboptions["urgency"].keys()))
		self.cbx_urge_min.set(list(ItemHandler._cboptions["urgency"].keys())[0])
		self.cbx_urge_min.pack(side=tk.LEFT, fill=tk.X, expand=1)
		subframe.pack(side=tk.TOP, fill=tk.X)
		
		# Enjoyability Min
		subframe = tk.Frame(self.tab_choose)
		tk.Label(subframe, text="Enjoyability Min", width=16, borderwidth=2, anchor="w").pack(side=tk.LEFT)
		self.cbx_enjoy_min = ttk.Combobox(subframe, state="readonly", values=list(ItemHandler._cboptions["enjoyability"].keys()))
		self.cbx_enjoy_min.set(list(ItemHandler._cboptions["enjoyability"].keys())[0])
		self.cbx_enjoy_min.pack(side=tk.LEFT, fill=tk.X, expand=1)
		subframe.pack(side=tk.TOP, fill=tk.X)
		
		# Choose button
		tk.Button(self.tab_choose, text="Choose", command=self.choose_item).pack(fill=tk.X)
		
		self.tab_choose.pack()
		
	def build_gui(self):
		self.win_main = tk.Tk()
		self.win_main.title("TODO")
		self.win_main.geometry(WINDOW_GEOMETRY)
		self.win_main.option_add("*Font", FONT)
		self.tab_control = ttk.Notebook(self.win_main)
		self.build_tab_choose()
		self.build_tab_insert()
		self.build_tab_view()
		self.tab_control.add(self.tab_choose, text='Choose')
		self.tab_control.add(self.tab_insert, text='Insert')
		self.tab_control.add(self.tab_view, text='View')
		self.tab_control.pack(expand=True, fill="both")
		self.win_main.mainloop()
	
def main():
	items_handler = ItemHandler()
	items_handler.load_items()
	gui = GUI(items_handler)
	gui.build_gui()

if __name__== "__main__": main()