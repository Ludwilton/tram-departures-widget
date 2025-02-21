import requests
from requests.auth import HTTPBasicAuth
import datetime
import tkinter as tk
from tkinter import ttk
import ctypes
import win32con
import win32gui

from API_KEYS import API_KEY, SECRET


def get_access_token():
    url = "https://ext-api.vasttrafik.se/token"
    auth = HTTPBasicAuth(API_KEY, SECRET)
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'grant_type': 'client_credentials'
    }

    response = requests.post(url, headers=headers, data=data, auth=auth)

    if response.status_code == 200:
        return response.json()['access_token']
    else:
        response.raise_for_status()  # Raise an exception for error status codes

def get_departures(access_token, stop_area_gid, start_date_time=None, platforms=None, time_span_in_minutes=60,
                   max_departures_per_line_and_direction=2, limit=10, offset=0, include_occupancy=False, direction_gid=None):
    url = f"https://ext-api.vasttrafik.se/pr/v4/stop-areas/{stop_area_gid}/departures"
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    params = {
        "timeSpanInMinutes": time_span_in_minutes,
        "maxDeparturesPerLineAndDirection": max_departures_per_line_and_direction,
        "limit": limit,
        "offset": offset,
        "includeOccupancy": include_occupancy,
    }
    params = {k: v for k, v in params.items() if v is not None}

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status() 

class DepartureWidget(tk.Tk):
    def __init__(self, stop_area_gid, update_interval=600):
        super().__init__()
        self.stop_area_gid = stop_area_gid
        self.update_interval = update_interval
        self.title("Avgångar från Doktor Fries Torg")
        self.geometry("400x200")
        self.configure(bg='#f0f0f0')

        self.overrideredirect(True)  # Remove window decorations
        self.attributes('-alpha', 0.9)  # Make the window slightly transparent

        self.is_movable = False

        self.hwnd = self.winfo_id()
        self.set_desktop_position()
        self.bind("<Button-1>", self.start_move)
        self.bind("<B1-Motion>", self.on_motion)
        self.bind("<ButtonRelease-1>", self.stop_move)
        self.bind("<KeyPress-M>", self.toggle_move)

        self.style = ttk.Style(self)
        self.style.configure("TLabel", font=("Helvetica", 12), background='#f0f0f0')
        self.style.configure("Header.TLabel", font=("Helvetica", 16, "bold"), background='#f0f0f0')
        self.style.configure("Departure.TFrame", background='#ffffff', relief='solid', padding=(10, 5))
        
        self.header_label = ttk.Label(self, text="Avgångar Doktor Fries Torg", style="Header.TLabel", anchor="center")
        self.header_label.pack(pady=10)

        self.departure_frame = ttk.Frame(self, style="Departure.TFrame")
        self.departure_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.update_departures()

    def set_desktop_position(self):
        desktop_hwnd = win32gui.FindWindow("Progman", "Program Manager")
        ctypes.windll.user32.SetParent(self.hwnd, desktop_hwnd)
        win32gui.SetWindowPos(self.hwnd, win32con.HWND_BOTTOM, 0, 0, 0, 0,
                              win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)

    def toggle_move(self):
        self.is_movable = not self.is_movable

    def start_move(self, event):
        if self.is_movable:
            self.x = event.x
            self.y = event.y

    def stop_move(self):
        if self.is_movable:
            self.x = None
            self.y = None

    def on_motion(self, event):
        if self.is_movable:
            deltax = event.x - self.x
            deltay = event.y - self.y
            x = self.winfo_x() + deltax
            y = self.winfo_y() + deltay
            self.geometry(f"+{x}+{y}")

    def update_departures(self):
        start_date_time = datetime.datetime.now().isoformat()
        try:
            access_token = get_access_token()
            departures = get_departures(access_token, self.stop_area_gid, start_date_time=start_date_time)
            self.display_departures(departures)
        except Exception as e:
            print(f"Error fetching departures: {e}")

        self.after(self.update_interval * 1000, self.update_departures)
            
    def display_departures(self, departures):
        for widget in self.departure_frame.winfo_children():
            widget.destroy()

        if "results" not in departures:
            ttk.Label(self.departure_frame, text="No departures found.", style="TLabel").pack(anchor="w")
            return

        departure_list = departures["results"]
        for departure in departure_list:
            estimated_time = departure.get("estimatedTime", "Unknown time")
            line_info = departure.get("serviceJourney", {}).get("line", {})
            direction_info = departure.get("serviceJourney", {}).get("directionDetails", {})
            stop_point_info = departure.get("stopPoint", {})
            
            line = line_info.get("shortName", "Unknown line")
            destination = direction_info.get("fullDirection", "Unknown destination")
            platform = stop_point_info.get("platform", "Unknown platform")

            if estimated_time != "Unknown time":
                try:
                    departure_time = datetime.datetime.fromisoformat(estimated_time)
                    formatted_time = departure_time.strftime("%H:%M")
                except ValueError:
                    formatted_time = "Unknown time (formatting error)"
            else:
                formatted_time = "Unknown time"

            departure_row = ttk.Frame(self.departure_frame, style="Departure.TFrame")
            departure_row.pack(fill=tk.X, pady=5)

            ttk.Label(departure_row, text=f"linje {line}", style="TLabel", width=8).pack(side=tk.LEFT, padx=5)
            ttk.Label(departure_row, text=f"till {destination}", style="TLabel", width=14).pack(side=tk.LEFT, padx=5)
            ttk.Label(departure_row, text=f"Läge {platform}", style="TLabel", width=9).pack(side=tk.LEFT, padx=5)
            ttk.Label(departure_row, text=f"{formatted_time}", style="TLabel", width=5).pack(side=tk.LEFT, padx=5)

def run_widget(stop_area_gid):
    app = DepartureWidget(stop_area_gid)
    app.mainloop()

if __name__ == "__main__":
    stop_area_gid = "9021014002090000"  # Sätt din hållplats GID här
    run_widget(stop_area_gid)