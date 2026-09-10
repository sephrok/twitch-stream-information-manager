import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import requests
import json
import os
import webbrowser
import threading

CLIENT_ID = 'b5rzfq5x5to3uoxekmkb7ib3t2jgsc' # Ensure your Public Client ID is pasted here
CONFIG_FILE = 'config.json'
PRESETS_FILE = 'presets.json'

class TwitchStreamManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Twitch Stream Information Manager v0.2")
        self.root.geometry("450x620")
        
        self.config = self.load_json(CONFIG_FILE)
        if "accounts" not in self.config:
            self.config = {"accounts": {}, "active": None}
            
        self.presets = self.load_json(PRESETS_FILE)
        self.device_code = ""
        self.interval = 5

        # --- ACCOUNT MANAGEMENT UI ---
        account_frame = tk.LabelFrame(root, text="Twitch Account")
        account_frame.pack(fill='x', padx=20, pady=10)
        
        self.account_combobox = ttk.Combobox(account_frame, state="readonly")
        self.account_combobox.pack(side='left', padx=10, pady=5, fill='x', expand=True)
        self.account_combobox.bind("<<ComboboxSelected>>", self.on_account_select)
        
        tk.Button(account_frame, text="Add", command=self.start_auth, width=5).pack(side='left', padx=(0, 5), pady=5)
        tk.Button(account_frame, text="Logout", command=self.logout_account, width=6).pack(side='left', padx=(0, 10), pady=5)
        
        self.refresh_account_dropdown()

        # --- PRESET UI ---
        preset_frame = tk.LabelFrame(root, text="Stream Information")
        preset_frame.pack(fill='both', expand=True, padx=20, pady=5)

        tk.Label(preset_frame, text="Select Preset:").pack(pady=(10, 0))
        self.preset_combobox = ttk.Combobox(preset_frame, state="readonly")
        self.preset_combobox.pack(fill='x', padx=20, pady=5)
        self.preset_combobox.bind("<<ComboboxSelected>>", self.on_preset_select)
        self.refresh_preset_dropdown()

        tk.Label(preset_frame, text="Stream Title:").pack(pady=(5, 0))
        self.title_entry = tk.Entry(preset_frame)
        self.title_entry.pack(fill='x', padx=20, pady=5)

        tk.Label(preset_frame, text="Game Name:").pack(pady=(5, 0))
        self.game_entry = tk.Entry(preset_frame)
        self.game_entry.pack(fill='x', padx=20, pady=5)
        
        tk.Label(preset_frame, text="Tags (comma-separated, max 10):").pack(pady=(5, 0))
        self.tags_entry = tk.Entry(preset_frame)
        self.tags_entry.pack(fill='x', padx=20, pady=5)

        tk.Label(preset_frame, text="Save Preset As:").pack(pady=(5, 0))
        self.preset_name_entry = tk.Entry(preset_frame)
        self.preset_name_entry.pack(fill='x', padx=20, pady=5)

        btn_frame = tk.Frame(preset_frame)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Save", command=self.save_current_preset, width=10).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Delete", command=self.delete_preset, width=10, fg="red").grid(row=0, column=1, padx=5)

        tk.Button(root, text="UPDATE TWITCH", command=self.update_twitch, width=25, bg="purple", fg="white", font=("Arial", 10, "bold")).pack(pady=15)

        # --- FOOTER ---
        footer_label = tk.Label(root, text="Created by Sephrok the Pathfinder (Buy me a coffee!)", fg="blue", cursor="hand2", font=("Arial", 9, "underline"))
        footer_label.pack(side="bottom", pady=10)
        footer_label.bind("<Button-1>", lambda e: webbrowser.open_new("https://ko-fi.com/sephrok"))

    # --- FILE MANAGEMENT ---
    def load_json(self, filepath):
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_json(self, filepath, data):
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)

    # --- ACCOUNT LOGIC ---
    def refresh_account_dropdown(self):
        accounts = list(self.config.get("accounts", {}).keys())
        self.account_combobox['values'] = accounts
        active = self.config.get("active")
        
        if active and active in accounts:
            self.account_combobox.set(active)
        elif accounts:
            self.account_combobox.set(accounts[0])
            self.config["active"] = accounts[0]
            self.save_json(CONFIG_FILE, self.config)
        else:
            self.account_combobox.set("")

    def on_account_select(self, event):
        selected = self.account_combobox.get()
        if selected:
            self.config["active"] = selected
            self.save_json(CONFIG_FILE, self.config)

    def logout_account(self):
        active = self.account_combobox.get()
        if active in self.config["accounts"]:
            del self.config["accounts"][active]
            self.config["active"] = None
            self.save_json(CONFIG_FILE, self.config)
            self.refresh_account_dropdown()
            messagebox.showinfo("Logged Out", f"Removed account: {active}")

    # --- AUTHENTICATION (DEVICE CODE FLOW) ---
    def start_auth(self):
        url = "https://id.twitch.tv/oauth2/device"
        data = {"client_id": CLIENT_ID, "scopes": "channel:manage:broadcast"}
        try:
            response = requests.post(url, data=data)
            if response.status_code == 200:
                res_data = response.json()
                self.device_code = res_data['device_code']
                self.interval = res_data['interval']
                self.show_auth_popup(res_data['user_code'], res_data['verification_uri'])
                self.root.after(self.interval * 1000, self.poll_for_token)
            else:
                messagebox.showerror("Auth Error", "Failed to start authentication.")
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))

    def show_auth_popup(self, user_code, verification_uri):
        self.auth_popup = tk.Toplevel(self.root)
        self.auth_popup.title("Twitch Authentication")
        self.auth_popup.geometry("300x200")
        
        tk.Label(self.auth_popup, text="1. Copy this code:", font=("Arial", 10)).pack(pady=(15, 5))
        code_entry = tk.Entry(self.auth_popup, font=("Arial", 14, "bold"), justify='center')
        code_entry.insert(0, user_code)
        code_entry.config(state='readonly')
        code_entry.pack(pady=5)
        
        tk.Label(self.auth_popup, text="2. Enter it at this link:").pack(pady=5)
        link = tk.Label(self.auth_popup, text=verification_uri, fg="blue", cursor="hand2")
        link.pack()
        link.bind("<Button-1>", lambda e: webbrowser.open_new(verification_uri))
        tk.Label(self.auth_popup, text="Waiting for authorization...", fg="gray").pack(pady=15)

    def poll_for_token(self):
        if not hasattr(self, 'auth_popup') or not self.auth_popup.winfo_exists():
            return 
        url = "https://id.twitch.tv/oauth2/token"
        data = {
            "client_id": CLIENT_ID,
            "scopes": "channel:manage:broadcast",
            "device_code": self.device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code"
        }
        response = requests.post(url, data=data)
        if response.status_code == 200:
            self.fetch_user_info(response.json()['access_token'])
            self.auth_popup.destroy()
        elif response.status_code == 400:
            self.root.after(self.interval * 1000, self.poll_for_token)
        else:
            self.auth_popup.destroy()
            messagebox.showerror("Error", "Authentication failed or timed out.")

    def fetch_user_info(self, access_token):
        url = "https://api.twitch.tv/helix/users"
        headers = {'Client-ID': CLIENT_ID, 'Authorization': f'Bearer {access_token}'}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json().get('data', [])
            if data:
                display_name = data[0]['display_name']
                self.config["accounts"][display_name] = {
                    'access_token': access_token,
                    'broadcaster_id': data[0]['id']
                }
                self.config["active"] = display_name
                self.save_json(CONFIG_FILE, self.config)
                self.refresh_account_dropdown()
                messagebox.showinfo("Success", f"Logged in as {display_name}!")

    # --- PRESET LOGIC ---
    def refresh_preset_dropdown(self):
        self.preset_combobox['values'] = ["New Preset"] + list(self.presets.keys())
        self.preset_combobox.set("New Preset")

    def clear_fields(self):
        self.title_entry.delete(0, tk.END)
        self.game_entry.delete(0, tk.END)
        self.tags_entry.delete(0, tk.END)
        self.preset_name_entry.delete(0, tk.END)

    def on_preset_select(self, event):
        selected = self.preset_combobox.get()
        self.clear_fields()
        if selected != "New Preset" and selected in self.presets:
            self.title_entry.insert(0, self.presets[selected].get('title', ''))
            self.game_entry.insert(0, self.presets[selected].get('game', ''))
            self.tags_entry.insert(0, ", ".join(self.presets[selected].get('tags', [])))
            self.preset_name_entry.insert(0, selected)

    def save_current_preset(self):
        name = self.preset_name_entry.get().strip()
        title = self.title_entry.get().strip()
        game = self.game_entry.get().strip()
        tags_raw = self.tags_entry.get().strip()
        
        if not name:
            messagebox.showwarning("Error", "Please provide a Preset Name.")
            return

        # Format tags into a list, stripping whitespace, limited to 10
        tags_list = [t.strip() for t in tags_raw.split(',') if t.strip()][:10]

        self.presets[name] = {"title": title, "game": game, "tags": tags_list}
        self.save_json(PRESETS_FILE, self.presets)
        self.refresh_preset_dropdown()
        self.preset_combobox.set(name)
        messagebox.showinfo("Saved", f"Preset '{name}' saved!")

    def delete_preset(self):
        selected = self.preset_combobox.get()
        if selected == "New Preset" or selected not in self.presets:
            return
        
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{selected}'?"):
            del self.presets[selected]
            self.save_json(PRESETS_FILE, self.presets)
            self.refresh_preset_dropdown()
            self.clear_fields()

    # --- TWITCH API UPDATES (THREADED) ---
    def update_twitch(self):
        active_account = self.config.get("active")
        if not active_account or active_account not in self.config.get("accounts", {}):
            messagebox.showwarning("Error", "Please add and select a Twitch account first.")
            return

        game_name = self.game_entry.get().strip()
        title = self.title_entry.get().strip()
        tags_raw = self.tags_entry.get().strip()
        tags_list = [t.strip() for t in tags_raw.split(',') if t.strip()][:10]

        account_data = self.config["accounts"][active_account]
        
        # Start the background thread so the UI doesn't freeze
        threading.Thread(target=self.background_update_task, args=(account_data, title, game_name, tags_list), daemon=True).start()

    def background_update_task(self, account_data, title, game_name, tags_list):
        headers = {
            'Client-ID': CLIENT_ID,
            'Authorization': f"Bearer {account_data['access_token']}",
            'Content-Type': 'application/json'
        }

        game_id = ""
        if game_name:
            try:
                game_res = requests.get(f"https://api.twitch.tv/helix/games?name={game_name}", headers=headers)
                if game_res.status_code == 200 and game_res.json().get('data'):
                    game_id = game_res.json()['data'][0]['id']
            except:
                pass # Game search failed, proceed with empty game ID

        payload = {"title": title, "game_id": game_id, "tags": tags_list}
        url = f"https://api.twitch.tv/helix/channels?broadcaster_id={account_data['broadcaster_id']}"
        
        try:
            response = requests.patch(url, headers=headers, json=payload)
            if response.status_code == 204:
                self.root.after(0, lambda: messagebox.showinfo("Success", "Stream updated!"))
            else:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Update failed: {response.status_code}\n{response.text}"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to connect to Twitch: {e}"))

if __name__ == "__main__":
    root = tk.Tk()
    app = TwitchStreamManager(root)
    root.mainloop()
