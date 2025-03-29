import os
import sys
from pathlib import Path
import customtkinter as ctk
from ui import CompareDrivesApp

def main():
    # Set appearance mode and default color theme
    ctk.set_appearance_mode("dark")  # Modes: "System" (standard), "Dark", "Light"
    ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"
    
    app = CompareDrivesApp()
    app.mainloop()

if __name__ == "__main__":
    main() 