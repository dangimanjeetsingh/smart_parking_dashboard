import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None
    list_ports = None

SerialError = serial.SerialException if serial else OSError


class SmartParkingDashboard:
    BAUD_RATE = 9600
    REFRESH_MS = 200
    TOTAL_SLOTS = 2

    BG = "#101114"
    SURFACE = "#191b20"
    SURFACE_2 = "#20232a"
    SURFACE_3 = "#2a2e36"
    TEXT = "#f4f7fb"
    MUTED = "#9aa3af"
    GREEN = "#2dd47a"
    RED = "#ff5a67"
    YELLOW = "#f5b84b"
    BLUE = "#46b6ff"
    LINE = "#343944"

    def __init__(self, root):
        self.root = root
        self.root.title("Smart Parking System")
        self.root.geometry("920x610")
        self.root.minsize(820, 560)
        self.root.configure(bg=self.BG)

        self.serial_connection = None
        self.current_slots = None
        self.car_count = None
        self.slot_states = [None] * self.TOTAL_SLOTS
        self.logs = []
        self.history_window = None
        self.history_listbox = None

        self.port_var = tk.StringVar()
        self.slots_var = tk.StringVar(value="--")
        self.occupied_var = tk.StringVar(value="Waiting for sensor data")
        self.status_var = tk.StringVar(value="Select the Arduino COM port and connect")
        self.connection_var = tk.StringVar(value="Offline")

        self.slot_cards = []

        self._build_style()
        self._build_ui()
        self.refresh_ports()
        self.read_serial_data()

    def _build_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Parking.TCombobox",
            fieldbackground=self.SURFACE_2,
            background=self.SURFACE_2,
            foreground=self.TEXT,
            arrowcolor=self.TEXT,
            bordercolor=self.LINE,
            lightcolor=self.SURFACE_2,
            darkcolor=self.SURFACE_2,
            padding=8,
        )

    def _button(self, parent, text, command, bg, fg=None):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg or self.TEXT,
            activebackground=self._lighten(bg),
            activeforeground=fg or self.TEXT,
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=18,
            pady=10,
            font=("Segoe UI", 10, "bold"),
        )

    def _lighten(self, color):
        palette = {
            self.BLUE: "#73c9ff",
            self.RED: "#ff7d87",
            self.GREEN: "#57df94",
            self.SURFACE_3: "#3a404b",
            "#2d333d": "#3a424f",
        }
        return palette.get(color, color)

    def _build_ui(self):
        main = tk.Frame(self.root, bg=self.BG)
        main.pack(fill="both", expand=True, padx=26, pady=22)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(2, weight=1)

        self._build_header(main)
        self._build_controls(main)
        self._build_dashboard(main)

    def _build_header(self, parent):
        header = tk.Frame(parent, bg=self.BG)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        header.columnconfigure(0, weight=1)

        title_block = tk.Frame(header, bg=self.BG)
        title_block.grid(row=0, column=0, sticky="w")

        tk.Label(
            title_block,
            text="Smart Parking System",
            bg=self.BG,
            fg=self.TEXT,
            font=("Segoe UI", 30, "bold"),
        ).pack(anchor="w")

        tk.Label(
            title_block,
            text="Live Arduino UNO USB serial dashboard",
            bg=self.BG,
            fg=self.MUTED,
            font=("Segoe UI", 11),
        ).pack(anchor="w", pady=(3, 0))

        self.connection_badge = tk.Label(
            header,
            textvariable=self.connection_var,
            bg=self.SURFACE_2,
            fg=self.MUTED,
            padx=18,
            pady=9,
            font=("Segoe UI", 10, "bold"),
        )
        self.connection_badge.grid(row=0, column=1, sticky="e")

    def _build_controls(self, parent):
        controls = tk.Frame(parent, bg=self.SURFACE, padx=18, pady=16)
        controls.grid(row=1, column=0, sticky="ew", pady=(0, 18))
        controls.columnconfigure(1, weight=1)

        tk.Label(
            controls,
            text="PORT",
            bg=self.SURFACE,
            fg=self.MUTED,
            font=("Segoe UI", 9, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=(0, 12))

        self.port_combo = ttk.Combobox(
            controls,
            textvariable=self.port_var,
            state="readonly",
            width=22,
            font=("Segoe UI", 10),
            style="Parking.TCombobox",
        )
        self.port_combo.grid(row=1, column=0, sticky="ew", padx=(0, 12), pady=(6, 0))

        self.connect_button = self._button(
            controls,
            "Connect",
            self.toggle_connection,
            self.BLUE,
            fg="#071016",
        )
        self.connect_button.grid(row=1, column=1, sticky="w", pady=(6, 0))

        refresh_button = self._button(controls, "Refresh Ports", self.refresh_ports, "#2d333d")
        refresh_button.grid(row=1, column=2, padx=(12, 0), pady=(6, 0))

        history_button = self._button(controls, "Action History", self.show_history, self.SURFACE_3)
        history_button.grid(row=1, column=3, padx=(12, 0), pady=(6, 0))

    def _build_dashboard(self, parent):
        body = tk.Frame(parent, bg=self.BG)
        body.grid(row=2, column=0, sticky="nsew")
        body.columnconfigure(0, weight=2)
        body.columnconfigure(1, weight=3)
        body.rowconfigure(0, weight=1)

        summary = tk.Frame(body, bg=self.SURFACE, padx=26, pady=24)
        summary.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        summary.columnconfigure(0, weight=1)

        tk.Label(
            summary,
            text="AVAILABLE SLOTS",
            bg=self.SURFACE,
            fg=self.MUTED,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")

        self.slots_label = tk.Label(
            summary,
            textvariable=self.slots_var,
            bg=self.SURFACE,
            fg=self.GREEN,
            font=("Segoe UI", 96, "bold"),
        )
        self.slots_label.pack(anchor="center", pady=(18, 0))

        self.capacity_label = tk.Label(
            summary,
            textvariable=self.occupied_var,
            bg=self.SURFACE,
            fg=self.MUTED,
            font=("Segoe UI", 14, "bold"),
        )
        self.capacity_label.pack(anchor="center", pady=(0, 24))

        self.status_card = tk.Frame(summary, bg=self.SURFACE_2, padx=18, pady=16)
        self.status_card.pack(fill="x", pady=(6, 0))

        tk.Label(
            self.status_card,
            text="CURRENT STATUS",
            bg=self.SURFACE_2,
            fg=self.MUTED,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w")

        self.status_label = tk.Label(
            self.status_card,
            textvariable=self.status_var,
            bg=self.SURFACE_2,
            fg=self.TEXT,
            font=("Segoe UI", 16, "bold"),
            wraplength=270,
            justify="left",
        )
        self.status_label.pack(anchor="w", pady=(7, 0))

        self.indicator = tk.Canvas(
            summary,
            width=240,
            height=12,
            bg=self.SURFACE,
            highlightthickness=0,
        )
        self.indicator.pack(fill="x", pady=(28, 0))
        self.indicator_track = self.indicator.create_rectangle(0, 0, 240, 12, fill=self.SURFACE_3, outline="")
        self.indicator_fill = self.indicator.create_rectangle(0, 0, 240, 12, fill=self.GREEN, outline="")
        self.indicator.bind("<Configure>", self._resize_indicator)

        parking = tk.Frame(body, bg=self.SURFACE, padx=24, pady=24)
        parking.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        parking.columnconfigure(0, weight=1)
        parking.rowconfigure(1, weight=1)

        top = tk.Frame(parking, bg=self.SURFACE)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        top.columnconfigure(0, weight=1)

        tk.Label(
            top,
            text="Parking Slot View",
            bg=self.SURFACE,
            fg=self.TEXT,
            font=("Segoe UI", 18, "bold"),
        ).grid(row=0, column=0, sticky="w")

        tk.Label(
            top,
            text="Live count and slot sensors from Arduino",
            bg=self.SURFACE,
            fg=self.MUTED,
            font=("Segoe UI", 10),
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))

        self.slot_grid = tk.Frame(parking, bg=self.SURFACE)
        self.slot_grid.grid(row=1, column=0, sticky="nsew")
        self.slot_grid.columnconfigure(0, weight=1)
        self.slot_grid.columnconfigure(1, weight=1)
        self.slot_grid.rowconfigure(0, weight=1)

        for index in range(self.TOTAL_SLOTS):
            card = self._create_slot_card(index + 1)
            card["frame"].grid(row=0, column=index, sticky="nsew", padx=8, pady=8)
            self.slot_cards.append(card)

        self.update_slot_view()

    def _create_slot_card(self, slot_number):
        frame = tk.Frame(self.slot_grid, bg=self.SURFACE_2, padx=18, pady=18)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        title = tk.Label(
            frame,
            text=f"SLOT {slot_number}",
            bg=self.SURFACE_2,
            fg=self.MUTED,
            font=("Segoe UI", 10, "bold"),
        )
        title.grid(row=0, column=0, sticky="w")

        state = tk.Label(
            frame,
            text="Waiting",
            bg=self.SURFACE_2,
            fg=self.MUTED,
            font=("Segoe UI", 20, "bold"),
        )
        state.grid(row=1, column=0, sticky="nsew")

        marker = tk.Canvas(frame, width=18, height=18, bg=self.SURFACE_2, highlightthickness=0)
        marker.grid(row=0, column=1, sticky="e")
        dot = marker.create_oval(2, 2, 16, 16, fill=self.MUTED, outline="")

        return {
            "frame": frame,
            "title": title,
            "state": state,
            "marker": marker,
            "dot": dot,
        }

    def refresh_ports(self):
        if list_ports is None:
            self.set_status("Install pyserial first: pip install pyserial", self.RED)
            return

        ports = [port.device for port in list_ports.comports()]
        self.port_combo["values"] = ports

        if ports and not self.port_var.get():
            self.port_var.set(ports[0])

        if not ports:
            self.port_var.set("")
            self.set_status("No COM ports found", self.YELLOW)

    def toggle_connection(self):
        if self.serial_connection and self.serial_connection.is_open:
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        if serial is None:
            messagebox.showerror("Missing dependency", "Install pyserial using: pip install pyserial")
            return

        port = self.port_var.get().strip()
        if not port:
            self.set_status("Select a COM port first", self.YELLOW)
            return

        try:
            self.serial_connection = serial.Serial(
                port=port,
                baudrate=self.BAUD_RATE,
                timeout=0,
            )
            self.connection_var.set(f"Online: {port}")
            self.connection_badge.configure(bg="#153222", fg=self.GREEN)
            self.connect_button.configure(text="Disconnect", bg=self.RED, fg=self.TEXT)
            self.set_status("Waiting for Arduino data...", self.BLUE)
            self.add_log(f"Connected to {port}")
        except SerialError as error:
            self.serial_connection = None
            self.connection_var.set("Offline")
            self.connection_badge.configure(bg=self.SURFACE_2, fg=self.MUTED)
            self.set_status("Could not open port", self.RED)
            messagebox.showerror("Serial Error", f"Could not open {port}\n\n{error}")

    def disconnect(self):
        if self.serial_connection:
            try:
                self.serial_connection.close()
            except SerialError:
                pass

        self.serial_connection = None
        self.connection_var.set("Offline")
        self.connection_badge.configure(bg=self.SURFACE_2, fg=self.MUTED)
        self.connect_button.configure(text="Connect", bg=self.BLUE, fg="#071016")
        self.set_status("Disconnected", self.MUTED)
        self.add_log("Disconnected")

    def read_serial_data(self):
        try:
            if self.serial_connection and self.serial_connection.is_open:
                while self.serial_connection.in_waiting:
                    raw_line = self.serial_connection.readline().decode("utf-8", errors="ignore")
                    line = raw_line.strip()
                    if line:
                        self.handle_arduino_message(line)
        except (SerialError, OSError) as error:
            self.set_status("Serial disconnected", self.RED)
            self.add_log(f"Serial error: {error}")
            self.disconnect()

        self.root.after(self.REFRESH_MS, self.read_serial_data)

    def handle_arduino_message(self, message):
        if message.startswith("COUNT:"):
            self.handle_state_packet(message)
        elif message == "ENTRY":
            self.set_status("Entry detected", self.GREEN)
            self.add_log("Entry detected")
        elif message == "EXIT":
            self.set_status("Exit detected", self.BLUE)
            self.add_log("Exit detected")
        elif message == "FULL":
            self.set_status("Parking full", self.RED)
            self.add_log("Parking full")
        elif message.startswith("SLOTS:"):
            self.update_slots_from_legacy_message(message)
        else:
            self.add_log(f"Malformed serial input ignored: {message}")

    def handle_state_packet(self, message):
        data = self.parse_state_packet(message)

        if data is None:
            self.add_log(f"Malformed serial input ignored: {message}")
            return

        previous_count = self.car_count
        previous_slots = list(self.slot_states)

        count = data["COUNT"]
        slot_states = [data["SLOT1"], data["SLOT2"]]

        self.car_count = count
        self.slot_states = slot_states

        available = self.TOTAL_SLOTS - count
        self.current_slots = available
        self.slots_var.set(str(available))
        self.occupied_var.set(f"{count} occupied / {self.TOTAL_SLOTS} total")

        self.update_slot_view()
        self.update_indicator(available)
        self.log_state_changes(previous_count, previous_slots, count, slot_states)
        self.update_status_from_count(previous_count, count)

    def parse_state_packet(self, message):
        values = {}

        for part in message.split():
            if ":" not in part:
                return None

            key, raw_value = part.split(":", 1)
            if key not in {"COUNT", "SLOT1", "SLOT2"}:
                return None

            try:
                values[key] = int(raw_value)
            except ValueError:
                return None

        if set(values) != {"COUNT", "SLOT1", "SLOT2"}:
            return None

        if not 0 <= values["COUNT"] <= self.TOTAL_SLOTS:
            return None

        if values["SLOT1"] not in (0, 1) or values["SLOT2"] not in (0, 1):
            return None

        return values

    def log_state_changes(self, previous_count, previous_slots, count, slot_states):
        if previous_count is None:
            self.add_log("Live data received")
        elif count > previous_count:
            self.add_log("Entry detected")
        elif count < previous_count:
            self.add_log("Exit detected")

        for index, state in enumerate(slot_states):
            old_state = previous_slots[index]
            if old_state == state:
                continue

            slot_number = index + 1
            if state == 1:
                self.add_log(f"Slot {slot_number} occupied")
            else:
                self.add_log(f"Slot {slot_number} free")

    def update_status_from_count(self, previous_count, count):
        if previous_count is None:
            color = self.RED if count == self.TOTAL_SLOTS else self.BLUE
            text = "Parking full" if count == self.TOTAL_SLOTS else "Live data connected"
            self.set_status(text, color)
        elif count > previous_count:
            self.set_status("Entry detected", self.GREEN)
        elif count < previous_count:
            self.set_status("Exit detected", self.BLUE)
        elif count == self.TOTAL_SLOTS:
            self.set_status("Parking full", self.RED)

    def update_slots_from_legacy_message(self, message):
        try:
            available = int(message.split(":", 1)[1])
        except ValueError:
            self.add_log(f"Malformed serial input ignored: {message}")
            return

        available = max(0, min(self.TOTAL_SLOTS, available))
        count = self.TOTAL_SLOTS - available
        previous_count = self.car_count

        self.car_count = count
        self.current_slots = available
        self.slots_var.set(str(available))
        self.occupied_var.set(f"{count} occupied / {self.TOTAL_SLOTS} total")
        self.update_indicator(available)

        if previous_count is None or previous_count != count:
            self.update_status_from_count(previous_count, count)

    def update_slot_view(self):
        for index, card in enumerate(self.slot_cards):
            state = self.slot_states[index]

            if state == 1:
                bg = "#322024"
                fg = self.RED
                text = "Occupied"
                dot = self.RED
            elif state == 0:
                bg = "#173024"
                fg = self.GREEN
                text = "Free"
                dot = self.GREEN
            else:
                bg = self.SURFACE_2
                fg = self.MUTED
                text = "Waiting"
                dot = self.MUTED

            card["frame"].configure(bg=bg)
            card["title"].configure(bg=bg)
            card["state"].configure(text=text, bg=bg, fg=fg)
            card["marker"].configure(bg=bg)
            card["marker"].itemconfig(card["dot"], fill=dot)

    def update_indicator(self, available):
        if available is None:
            color = self.MUTED
            ratio = 0
        else:
            color = self.GREEN if available > 0 else self.RED
            ratio = available / self.TOTAL_SLOTS

        self.slots_label.configure(fg=color)
        width = max(1, self.indicator.winfo_width())
        self.indicator.itemconfig(self.indicator_fill, fill=color)
        self.indicator.coords(self.indicator_fill, 0, 0, int(width * ratio), 12)

    def _resize_indicator(self, event):
        self.indicator.coords(self.indicator_track, 0, 0, event.width, 12)
        self.update_indicator(self.current_slots)

    def set_status(self, text, color):
        self.status_var.set(text)
        self.status_label.configure(fg=color)

    def add_log(self, text):
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {text}"
        self.logs.insert(0, entry)

        if len(self.logs) > 100:
            self.logs.pop()

        if self.history_listbox and self.history_listbox.winfo_exists():
            self.history_listbox.insert(0, entry)
            if self.history_listbox.size() > 100:
                self.history_listbox.delete(100, tk.END)

    def show_history(self):
        if self.history_window and self.history_window.winfo_exists():
            self.history_window.lift()
            self.history_window.focus_force()
            return

        self.history_window = tk.Toplevel(self.root)
        self.history_window.title("Action History")
        self.history_window.geometry("520x420")
        self.history_window.minsize(460, 360)
        self.history_window.configure(bg=self.BG)

        panel = tk.Frame(self.history_window, bg=self.SURFACE, padx=18, pady=18)
        panel.pack(fill="both", expand=True, padx=18, pady=18)
        panel.rowconfigure(1, weight=1)
        panel.columnconfigure(0, weight=1)

        header = tk.Frame(panel, bg=self.SURFACE)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        header.columnconfigure(0, weight=1)

        tk.Label(
            header,
            text="Action History",
            bg=self.SURFACE,
            fg=self.TEXT,
            font=("Segoe UI", 18, "bold"),
        ).grid(row=0, column=0, sticky="w")

        clear_button = self._button(header, "Clear", self.clear_history, self.SURFACE_3)
        clear_button.grid(row=0, column=1, sticky="e")

        self.history_listbox = tk.Listbox(
            panel,
            bg="#0d0f13",
            fg=self.TEXT,
            selectbackground=self.SURFACE_3,
            selectforeground=self.TEXT,
            highlightthickness=1,
            highlightbackground=self.LINE,
            borderwidth=0,
            font=("Consolas", 10),
            activestyle="none",
        )
        self.history_listbox.grid(row=1, column=0, sticky="nsew")

        for entry in self.logs:
            self.history_listbox.insert(tk.END, entry)

        self.history_window.protocol("WM_DELETE_WINDOW", self.close_history)

    def clear_history(self):
        self.logs.clear()
        if self.history_listbox and self.history_listbox.winfo_exists():
            self.history_listbox.delete(0, tk.END)

    def close_history(self):
        if self.history_window and self.history_window.winfo_exists():
            self.history_window.destroy()
        self.history_window = None
        self.history_listbox = None

    def on_close(self):
        self.close_history()
        self.disconnect()
        self.root.destroy()


if __name__ == "__main__":
    app_root = tk.Tk()
    app = SmartParkingDashboard(app_root)
    app_root.protocol("WM_DELETE_WINDOW", app.on_close)
    app_root.mainloop()
