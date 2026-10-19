"""
Scale Capture System

Purpose:
    Capture product transactions from a USB-connected scale.

Transaction Types:
    1. WEIGHT
        - User enters Item Code
        - User selects Container
        - Scale sends Gross Weight
        - Tare is subtracted automatically
        - Net Weight is saved

    2. COUNT
        - User enters Item Code
        - User enters Count
        - No scale interaction required

Data Storage:
    Daily CSV file:
        scale/Data/weights_YYYYMMDD.csv

Scale Communication:
    - USB Virtual Serial Port
    - Auto-detects CH340 adapter
    - 9600 baud
    - Handles disconnects

Author:
    Lorentz Kremer

Change Log
------------------------------------------------
v1.0 Initial weight capture
v1.1 Added automatic tare deduction
v1.2 Added count transactions
v1.3 Added auto COM port detection
v1.4 Added disconnect transaction cancellation
v1.5 Fixed data innacuracies if scale gets disconnected
v1.6 Add GUI
------------------------------------------------
    
Last Major Update:
    2026-09-22


TO DO:
Add operator cancellation
Add CSV export summary
Add product master file for input and validation
"""

# Business Rule:
# Every location has its own containers.
# Update the container constant usign local data.

# Business Rule:
# Transaction is cancelled if scale disconnects.
# Operator must restart from Item Code.
# This prevents incorrect product / weight pairing.

# Business Rule:
# Negative net weights are rejected.
# Indicates tare weight exceeds measured weight.




import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import csv
import re
from pathlib import Path
from datetime import datetime
import winsound
from datetime import datetime, timedelta

# =====================================================
# CONFIG
# =====================================================

VERSION = "1.6"
BAUD = 9600

CONTAINERS = {
    "Hotel Pan": 3.5,
    "Half Pan": 2.8,
    "Sheet Pan": 2.0,
    "Others": 0.0
}

# =====================================================
# DATA FILE
# =====================================================

data_folder = Path("scale/Data")
data_folder.mkdir(parents=True, exist_ok=True)

csv_file = data_folder / f"weights_{datetime.now():%Y%m%d}.csv"

if not csv_file.exists():
    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Timestamp",
            "ItemCode",
            "TransactionType",
            "Count",
            "ContainerType",
            "GrossWeight",
            "TareWeight",
            "NetWeight",
            "Unit"
        ])

# =====================================================
# SCALE COMMUNICATION
# =====================================================

ser = None
current_weight = 0
current_unit = "lb"

last_weight_update = None

def find_scale_port():

    ports = serial.tools.list_ports.comports()

    for port in ports:

        desc = port.description.lower()

        if (
            "ch340" in desc
            or "usb-serial" in desc
        ):
            return port.device

    return None


def connect_scale():

    global ser

    try:

        port = find_scale_port()

        if not port:
            return False

        ser = serial.Serial(
            port,
            BAUD,
            timeout=1
        )

        status_label.config(
            text=f"Scale Connected ({port})",
            fg="green"
        )

        capture_button.config(
            state="normal"
        )

        return True

    except:

        status_label.config(
            text="Scale Disconnected",
            fg="red"
        )

        return False


# =====================================================
# LIVE WEIGHT UPDATE
# =====================================================

def update_weight():

    global ser
    global current_weight
    global current_unit

    try:

        if ser is None or not ser.is_open:

            connect_scale()

        if ser:

            data = ser.read_all()

            if data:

                text = data.decode(
                    errors="ignore"
                )

                match = re.search(
                    r'([\d.]+)\s*(lb|kg)',
                    text,
                    re.IGNORECASE
                )

                if match:

                    current_weight = float(
                        match.group(1)
                    )

                    current_unit = (
                        match.group(2).lower()
                    )

                    global last_weight_update

                    last_weight_update = datetime.now()

                    weight_label.config(
                        text=f"{current_weight:.3f} {current_unit}"
                    )

    except:

        status_label.config(
            text="Scale Disconnected",
            fg="red"
        )

        capture_button.config(
            state="disabled"
        )

        try:
            ser.close()
        except:
            pass

        ser = None

        reset_transaction()

    root.after(200, update_weight)

# =====================================================
# SAVE TRANSACTION
# =====================================================
def reset_transaction():

    global current_weight
    global last_weight_update

    item_entry.delete(0, tk.END)

    count_entry.delete(0, tk.END)

    transaction_var.set("WEIGHT")
    update_transaction_type()

    container_dropdown.current(0)

    current_weight = 0

    last_weight_update = None

    weight_label.config(
        text="0.000 lb"
    )

    item_entry.focus()


def save_transaction():

    global current_weight

    item_code = item_entry.get().strip().upper()

    if not item_code:

        messagebox.showerror(
            "Error",
            "Item Code is required."
        )

        return

    transaction = transaction_var.get()

    # ==========================================
# SCALE SAFETY CHECKS
# ==========================================

    if transaction == "WEIGHT":

        if ser is None:

            winsound.Beep(500, 500)

            messagebox.showerror(
                "Scale Disconnected",
                "The scale is not connected."
            )

            return

        if not ser.is_open:

            winsound.Beep(500, 500)

            messagebox.showerror(
                "Scale Disconnected",
                "The scale connection is closed."
            )

            return

        if last_weight_update is None:

            winsound.Beep(500, 500)

            messagebox.showerror(
                "No Weight Available",
                "No valid weight has been received."
            )

            return

        age = datetime.now() - last_weight_update

        if age > timedelta(seconds=5):

            winsound.Beep(500, 500)

            messagebox.showerror(
                "Weight Too Old",
                "The scale reading is stale.\n\n"
                "Reconnect or obtain a fresh reading."
            )

            return

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # ==========================================
    # COUNT
    # ==========================================

    if transaction == "COUNT":

        count_text = count_entry.get().strip()

        if not count_text.isdigit():

            messagebox.showerror(
                "Error",
                "Enter a valid count."
            )

            return

        count = int(count_text)

        with open(
            csv_file,
            "a",
            newline=""
        ) as f:

            writer = csv.writer(f)

            writer.writerow([
                timestamp,
                item_code,
                "COUNT",
                count,
                "",
                "",
                "",
                "",
                ""
            ])

        winsound.Beep(1000, 200)

        last_transaction.config(
            text=
            f"Last Saved\n\n"
            f"Item: {item_code}\n"
            f"Count: {count}\n"
            f"Time: {timestamp}"
        )

        reset_transaction()

        return

    # ==========================================
    # WEIGHT
    # ==========================================

    container = container_var.get()

    tare_lb = CONTAINERS[container]

    if current_unit == "lb":

        tare_weight = tare_lb

    else:

        tare_weight = round(
            tare_lb * 0.45359237,
            3
        )

    gross_weight = current_weight
    if gross_weight <= 0:

        winsound.Beep(500, 500)

        messagebox.showerror(
            "Invalid Weight",
            "Weight must be greater than zero."
        )

        return

    net_weight = round(
        gross_weight - tare_weight,
        3
    )

    if net_weight < 0:

        winsound.Beep(500, 500)

        messagebox.showerror(
            "Invalid Measurement",
            (
                f"Container: {container}\n"
                f"Gross Weight: {gross_weight} {current_unit}\n"
                f"Tare Weight: {tare_weight} {current_unit}\n\n"
                "The measured weight is less than the selected "
                "container tare.\n\n"
                "The transaction has been cancelled."
            )
        )

        reset_transaction()

        return

    with open(
        csv_file,
        "a",
        newline=""
    ) as f:

        writer = csv.writer(f)

        writer.writerow([
            timestamp,
            item_code,
            "WEIGHT",
            "",
            container,
            gross_weight,
            tare_weight,
            net_weight,
            current_unit
        ])

    winsound.Beep(1000, 200)

    last_transaction.config(
        text=
        f"Last Saved\n\n"
        f"Item: {item_code}\n"
        f"Container: {container}\n"
        f"Net: {net_weight} {current_unit}\n"
        f"Time: {timestamp}"
    )

    reset_transaction()


# =====================================================
# CLEAR FIELDS
# =====================================================

def clear_fields():

    item_entry.delete(0, tk.END)

    count_entry.delete(0, tk.END)

    item_entry.focus()


def update_transaction_type():

    if transaction_var.get() == "WEIGHT":

        container_dropdown.config(
            state="readonly"
        )

        count_entry.config(
            state="disabled"
        )

    else:

        container_dropdown.config(
            state="disabled"
        )

        count_entry.config(
            state="normal"
        )


# =====================================================
# GUI
# =====================================================

root = tk.Tk()

root.title(
    f"Scale Capture System V{VERSION}"
)

root.geometry("700x700")

root.resizable(False, False)

# =====================================================
# HEADER
# =====================================================

title = tk.Label(
    root,
    text=f"SCALE CAPTURE SYSTEM V{VERSION}",
    font=("Arial", 20, "bold")
)

title.pack(pady=10)

status_label = tk.Label(
    root,
    text="Connecting...",
    font=("Arial", 12)
)

status_label.pack()

# =====================================================
# ITEM CODE
# =====================================================

frame_item = tk.Frame(root)
frame_item.pack(pady=10)

tk.Label(
    frame_item,
    text="Item Code",
    font=("Arial", 12)
).pack()

item_entry = tk.Entry(
    frame_item,
    width=30,
    font=("Arial", 14)
)

item_entry.pack()

# =====================================================
# TRANSACTION TYPE
# =====================================================

transaction_var = tk.StringVar(
    value="WEIGHT"
)

frame_type = tk.Frame(root)
frame_type.pack(pady=10)

tk.Radiobutton(
    frame_type,
    text="Weight",
    variable=transaction_var,
    value="WEIGHT",
    command=update_transaction_type
).pack(side="left", padx=20)

tk.Radiobutton(
    frame_type,
    text="Count",
    variable=transaction_var,
    value="COUNT",
    command=update_transaction_type
).pack(side="left", padx=20)

# =====================================================
# CONTAINER
# =====================================================

frame_container = tk.Frame(root)
frame_container.pack(pady=10)

tk.Label(
    frame_container,
    text="Container"
).pack()

container_var = tk.StringVar()

container_dropdown = ttk.Combobox(
    frame_container,
    textvariable=container_var,
    values=list(CONTAINERS.keys()),
    state="readonly",
    width=25
)

container_dropdown.current(0)
container_dropdown.pack()


# =====================================================
# COUNT
# =====================================================

frame_count = tk.Frame(root)
frame_count.pack(pady=10)

tk.Label(
    frame_count,
    text="Count"
).pack()

count_entry = tk.Entry(
    frame_count,
    width=20,
    font=("Arial", 14)
)

count_entry.pack()

# Initialize control states
update_transaction_type()

# =====================================================
# LIVE WEIGHT DISPLAY
# =====================================================

tk.Label(
    root,
    text="Current Weight",
    font=("Arial", 14)
).pack(pady=10)

weight_label = tk.Label(
    root,
    text="0.000 lb",
    font=("Arial", 36, "bold"),
    fg="blue"
)

weight_label.pack(pady=10)

# =====================================================
# CAPTURE BUTTON
# =====================================================

capture_button = tk.Button(
    root,
    text="CAPTURE",
    font=("Arial", 16, "bold"),
    width=20,
    height=2,
    bg="#4CAF50",
    fg="white",
    command=save_transaction
)

capture_button.pack(pady=20)

# =====================================================
# LAST TRANSACTION
# =====================================================

last_transaction = tk.Label(
    root,
    text="No transaction saved",
    justify="left",
    font=("Arial", 11)
)

last_transaction.pack(pady=20)

# =====================================================
# START
# =====================================================

connect_scale()

update_weight()

item_entry.focus()

root.mainloop()

# =====================================================
# CLEAN EXIT
# =====================================================

try:
    if ser:
        ser.close()
except:
    pass