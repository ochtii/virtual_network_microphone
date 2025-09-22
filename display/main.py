import tkinter as tk
from tkinter import ttk

# Farben für Light/Dark Theme
THEMES = {
    "light": {"bg": "#ffffff", "fg": "#000000"},
    "dark": {"bg": "#222222", "fg": "#ffffff"}
}

theme = "light"  # default

root = tk.Tk()
root.title("Raspberry Touch GUI")
root.geometry("800x480")
root.configure(bg=THEMES[theme]["bg"])

# Tab Control
tabControl = ttk.Notebook(root)

# Seite 1: Metrics
tab1 = ttk.Frame(tabControl)
tabControl.add(tab1, text='Metrics')

subtabs = ttk.Notebook(tab1)
system_tab = ttk.Frame(subtabs)
network_tab = ttk.Frame(subtabs)
placeholder_tab = ttk.Frame(subtabs)
subtabs.add(system_tab, text='System Metrics')
subtabs.add(network_tab, text='Network Metrics')
subtabs.add(placeholder_tab, text='Placeholder')
subtabs.pack(expand=1, fill="both")

# Beispiel Labels
tk.Label(system_tab, text="CPU: --%", font=("Arial", 16)).pack(pady=10)
tk.Label(network_tab, text="Upload/Download: --", font=("Arial", 16)).pack(pady=10)
tk.Label(placeholder_tab, text="Noch nix", font=("Arial", 16)).pack(pady=10)

# Seite 2: Settings
tab2 = ttk.Frame(tabControl)
tabControl.add(tab2, text='Settings')
tk.Label(tab2, text="Schriftgröße Stats:").pack(pady=10)
font_size = tk.IntVar(value=16)
tk.Spinbox(tab2, from_=8, to=32, textvariable=font_size).pack()

tk.Label(tab2, text="Theme:").pack(pady=10)
def change_theme(sel):
    global theme
    theme = sel
    root.configure(bg=THEMES[theme]["bg"])

ttk.Combobox(tab2, values=["light", "dark"], state="readonly", 
             postcommand=lambda: None, textvariable=tk.StringVar(value=theme),
             ).pack()

# Seite 3: Placeholder
tab3 = ttk.Frame(tabControl)
tabControl.add(tab3, text='Placeholder')
tk.Label(tab3, text="Seite 3: Platzhalter", font=("Arial", 16)).pack(pady=10)

tabControl.pack(expand=1, fill="both")
root.mainloop()
