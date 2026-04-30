import os
import json
import shutil
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox
import threading

try:
    from pymediainfo import MediaInfo
    MEDIAINFO_AVAILABLE = True
except ImportError:
    MEDIAINFO_AVAILABLE = False

def collect_file_properties(directory):
    files = []
    for root, dirs, filenames in os.walk(directory):
        for name in filenames:
            full_path = os.path.join(root, name)
            try:
                stat = os.stat(full_path)
            except OSError:
                continue
            files.append({
                "name": name,
                "relative_path": os.path.relpath(full_path, directory),
                "full_path": full_path,
                "size_bytes": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "accessed": datetime.fromtimestamp(stat.st_atime).isoformat()
            })
    return sorted(files, key=lambda item: item["relative_path"])

def write_json(output_file, dir_path, file_properties):
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({"directory": dir_path, "files": file_properties}, f, indent=2)

def write_text_names(output_file, file_properties):
    with open(output_file, "w", encoding="utf-8") as f:
        for item in file_properties:
            f.write(f"{item['name']}\n")

def write_text_info(output_file, file_properties):
    with open(output_file, "w", encoding="utf-8") as f:
        for item in file_properties:
            f.write(f"\n{'='*80}\n")
            f.write(f"{item['name']}\n")
            f.write(f"{'='*80}\n\n")
            
            if MEDIAINFO_AVAILABLE:
                try:
                    # Set timeout to prevent hanging on large/problematic files
                    media_info = MediaInfo.parse(item['full_path'], parse_speed=0.5)
                    
                    track_found = False
                    for track in media_info.tracks:
                        track_found = True
                        f.write(f"{track.track_type}\n")
                        f.write("-" * 80 + "\n")
                        
                        # Get all available attributes for the track
                        for attr in dir(track):
                            if not attr.startswith('_') and attr not in ['track_type', 'other_tracks']:
                                try:
                                    value = getattr(track, attr, None)
                                    if value is not None and value != '':
                                        # Format the attribute name nicely
                                        attr_display = attr.replace('_', ' ').title()
                                        if isinstance(value, list):
                                            value = ', '.join(map(str, value))
                                        f.write(f"{attr_display:<40}: {value}\n")
                                except Exception:
                                    pass
                        f.write("\n")
                    
                    if not track_found:
                        write_basic_info(f, item)
                        
                except Exception as e:
                    # Fallback if MediaInfo fails
                    write_basic_info(f, item)
            else:
                write_basic_info(f, item)

def write_basic_info(f, item):
    f.write("General\n")
    f.write("-" * 80 + "\n")
    f.write(f"{'File Name':<40}: {item['name']}\n")
    f.write(f"{'Relative Path':<40}: {item['relative_path']}\n")
    f.write(f"{'Full Path':<40}: {item['full_path']}\n")
    f.write(f"{'File Size':<40}: {item['size_bytes']} bytes\n")
    f.write(f"{'Created':<40}: {item['created']}\n")
    f.write(f"{'Modified':<40}: {item['modified']}\n")
    f.write(f"{'Accessed':<40}: {item['accessed']}\n")

def extract_images(directory):
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico', '.tiff', '.tif', '.exif', '.heic', '.heif'}
    extracted_count = 0
    extract_folder = os.path.join(directory, 'extractedImages')
    
    if not os.path.exists(extract_folder):
        os.makedirs(extract_folder)
    
    for root, dirs, filenames in os.walk(directory):
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if ext in image_extensions:
                full_path = os.path.join(root, name)
                try:
                    dest_path = os.path.join(extract_folder, name)
                    counter = 1
                    base_name, file_ext = os.path.splitext(name)
                    while os.path.exists(dest_path):
                        dest_path = os.path.join(extract_folder, f"{base_name}_{counter}{file_ext}")
                        counter += 1
                    
                    shutil.copy2(full_path, dest_path)
                    extracted_count += 1
                except Exception:
                    pass
    
    return extracted_count, extract_folder

def choose_directory():
    path = filedialog.askdirectory()
    if path:
        path = os.path.abspath(os.path.expanduser(path))
        directory_var.set(path)

class BusyDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Processing")
        self.geometry("250x100")
        self.resizable(False, False)
        
        # Center on parent
        self.transient(parent)
        self.grab_set()
        
        frame = tk.Frame(self, padx=20, pady=20)
        frame.pack(fill="both", expand=True)
        
        tk.Label(frame, text="Processing...", font=("Arial", 12)).pack(pady=10)
        
        self.progress_label = tk.Label(frame, text="", font=("Arial", 10), fg="blue")
        self.progress_label.pack(pady=5)
        
        self.update_idletasks()
    
    def update_message(self, message):
        self.progress_label.config(text=message)
        self.update_idletasks()

def process_export(dir_path, choice):
    """Process export in background thread"""
    try:
        if choice == "4":
            extracted_count, extract_folder = extract_images(dir_path)
            return ("success", f"Extracted {extracted_count} image(s) to:\n{extract_folder}")
        
        file_properties = collect_file_properties(dir_path)
        outputs = []
        
        if choice == "1":
            json_file = os.path.join(dir_path, "files_properties.json")
            write_json(json_file, dir_path, file_properties)
            outputs.append(json_file)
        
        if choice == "2":
            text_file = os.path.join(dir_path, "files_names.txt")
            write_text_names(text_file, file_properties)
            outputs.append(text_file)
        
        if choice == "3":
            text_file = os.path.join(dir_path, "files_info.txt")
            write_text_info(text_file, file_properties)
            outputs.append(text_file)
        
        return ("success", "Export complete:\n" + "\n".join(outputs))
    except Exception as e:
        return ("error", str(e))

def run_export():
    dir_path = directory_var.get().strip()
    if not dir_path or not os.path.isdir(dir_path):
        messagebox.showerror("Error", "Please select a valid directory.")
        return

    choice = option_var.get()
    if choice not in {"1", "2", "3", "4"}:
        messagebox.showerror("Error", "Please select an output option.")
        return

    if choice == "3" and MEDIAINFO_AVAILABLE:
        busy_dialog = BusyDialog(app)
        
        def process():
            result_type, result_msg = process_export(dir_path, choice)
            app.after(0, lambda: finish_processing(busy_dialog, result_type, result_msg))
        
        thread = threading.Thread(target=process, daemon=True)
        thread.start()
    else:
        result_type, result_msg = process_export(dir_path, choice)
        if result_type == "success":
            messagebox.showinfo("Success", result_msg)
        else:
            messagebox.showerror("Error", result_msg)

def finish_processing(dialog, result_type, result_msg):
    """Called from main thread after processing completes"""
    dialog.destroy()
    if result_type == "success":
        messagebox.showinfo("Success", result_msg)
    else:
        messagebox.showerror("Error", result_msg)

app = tk.Tk()
app.title("Directory File Exporter")
app.geometry("460x310")
app.resizable(False, False)

directory_var = tk.StringVar()
option_var = tk.StringVar(value="1")

frame = tk.Frame(app, padx=12, pady=12)
frame.pack(fill="both", expand=True)

tk.Label(frame, text="Select directory:").grid(row=0, column=0, sticky="w")
entry = tk.Entry(frame, textvariable=directory_var, width=50)
entry.grid(row=1, column=0, columnspan=2, pady=(0, 10), sticky="w")
tk.Button(frame, text="Browse...", command=choose_directory, width=12).grid(row=1, column=2, padx=(8,0))

tk.Label(frame, text="Output option:").grid(row=2, column=0, sticky="w")
tk.Radiobutton(frame, text="JSON file only", variable=option_var, value="1").grid(row=3, column=0, sticky="w", pady=2)
tk.Radiobutton(frame, text="Text file - Names only", variable=option_var, value="2").grid(row=4, column=0, sticky="w", pady=2)
tk.Radiobutton(frame, text="Text file - All properties", variable=option_var, value="3").grid(row=5, column=0, sticky="w", pady=2)
tk.Radiobutton(frame, text="Extract images to folder", variable=option_var, value="4").grid(row=6, column=0, sticky="w", pady=2)

tk.Button(frame, text="Export", command=run_export, width=16, bg="#4CAF50", fg="white").grid(row=7, column=0, columnspan=3, pady=(16, 0))

app.mainloop()