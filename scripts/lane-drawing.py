# filepath: untitled:Untitled-1
import tkinter as tk
import json
from tkinter import filedialog
from PIL import ImageTk, Image
import sys
import argparse

colors = [
    "red", "green", "blue", "yellow", "purple", "orange", "black", "white", 
    "cyan", "magenta", "brown", "gray", "pink", "lime", "navy", "teal", 
    "maroon", "olive", "silver", "gold"
]

class Line:
    def __init__(self, lane_name, color):
        self.name = lane_name
        self.color = color
        self.points = []

    def to_dict(self):
        return {"name": self.name, "points": self.points}
    
    def add_point(self, event):
        self.points.append((event.x, event.y))

    def get_points(self):
        yield from self.points

    def get_last_point(self):
        if len(self.points) > 0:
            return self.points[-1]
        return None


class DrawApp:
    def __init__(self, root, input_image):
        self.root = root
        self.root.title("Traffic Lane Marking Tool")
        
        self.image = Image.open(input_image)
        
        self.canvas = tk.Canvas(root, width=self.image.width, height=self.image.height, bg="white")
        self.canvas.pack(side=tk.LEFT)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.image_tk = ImageTk.PhotoImage(self.image)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.image_tk)

        self.lines = []
        self.listbox = tk.Listbox(root)
        self.listbox.bind("<<ListboxSelect>>", self.on_listbox_select)
        self.listbox.pack(side=tk.RIGHT, fill=tk.Y)

        self.name_label = tk.Label(root, text="Line Name:")
        self.name_label.pack()

        self.name_entry = tk.Entry(root)
        self.name_entry.pack()
        self.add_button = tk.Button(root, text="Add a new line", command=self.create_new_line)
        self.add_button.pack()

        self.remove_button = tk.Button(root, text="Remove Last Point", command=self.remove_last_point)
        self.remove_button.pack()

        self.save_button = tk.Button(root, text="Save Polylines", command=self.save_polylines)
        self.save_button.pack()

        # Add a line to start
        # self.create_new_line()
        # self.update_listbox()
        # self.listbox.select_set(0)
        # self.last_point = self.current_line.get_last_point()

    def update_listbox(self):
        selected = self.listbox.curselection()
        for index, line in enumerate(self.lines):
            self.listbox.delete(index)
            self.listbox.insert(index, f"{line.name} {index} ({line.color}): {len(line.points)} points")
        if selected:
            self.listbox.select_set(selected[0])

    def create_new_line(self):
        lane_name = self.name_entry.get()
        if lane_name == "":
            tk.messagebox.showerror("Error", "Please enter a name for the line")
            return
        self.lines.append(Line(lane_name=lane_name, color=colors[len(self.lines) % len(colors)]))
        self.update_listbox()
        self.listbox.selection_clear(0, tk.END)
        self.listbox.select_set(tk.END, tk.END)
        self.current_line = self.lines[-1]
        self.last_point = self.current_line.get_last_point()
        self.name_entry.delete(0, tk.END)

    def remove_last_point(self):
        if self.last_point is None:
            return
        self.current_line.points.pop()
        self.last_point = self.current_line.get_last_point()
        self.update_listbox()

        # Clear the canvas and redraw all lines
        self.canvas.delete("lines")
        self.update_lines()

    def on_listbox_select(self, event):
        index = self.listbox.curselection()[0]
        self.current_line = self.lines[index]
        self.last_point = self.current_line.get_last_point()
        self.update_listbox()

    def on_button_release(self, event):
        self.current_line.add_point(event)
        if self.last_point is not None:
            x, y = self.last_point
            self.canvas.create_line(x, y, event.x, event.y, fill=self.current_line.color, width=2, tags="lines")
        else:
            x, y = event.x, event.y
            self.canvas.create_oval(x-2, y-2, x+2, y+2, fill=self.current_line.color, tags="lines")
        self.last_point = (event.x, event.y)
        
    def update_lines(self):
        for line in self.lines:
            last_x = None
            last_y = None
            for x, y in line.get_points():
                if last_x is None:
                    last_x = x
                    last_y = y
                    self.canvas.create_oval(x-2, y-2, x+2, y+2, fill=line.color, tags="lines")
                    continue
                self.canvas.create_line(last_x, last_y, x, y, fill=line.color, width=2, tags="lines")
                last_x = x
                last_y = y

    def save_polylines(self):
        with open("out.json", "w") as f:
            lanes = [x.to_dict() for x in self.lines]
            json.dump(lanes, f, indent=4)
        tk.messagebox.showinfo("Save Traffic lanes", "Traffic lanes saved to out.json")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Traffic Lane Marking Tool")
    parser.add_argument("--image", "-i", required=True, help="Path to image file")
    args = parser.parse_args()

    root = tk.Tk()
    app = DrawApp(root, input_image=args.image)
    root.mainloop()