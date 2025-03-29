import os
import threading
import time
from pathlib import Path
from tkinter import filedialog, messagebox, Toplevel, StringVar, BooleanVar, IntVar
import customtkinter as ctk
from file_utils import DriveComparator, ScanResult, FileComparison

# Define colors and styles
GRAY_100 = "#F8F9FA"
GRAY_200 = "#E9ECEF"
GRAY_300 = "#DEE2E6" 
GRAY_400 = "#CED4DA"
GRAY_500 = "#ADB5BD"
GRAY_600 = "#6C757D"
GRAY_700 = "#495057"
GRAY_800 = "#343A40"
GRAY_900 = "#212529"

BLUE_ACCENT = "#3B82F6"
GREEN_SUCCESS = "#10B981"
RED_ERROR = "#EF4444"
ORANGE_WARNING = "#F59E0B"
YELLOW_WARNING = "#FBBF24"

class RoundedButton(ctk.CTkButton):
    """Custom button with enhanced styling"""
    def __init__(self, *args, **kwargs):
        kwargs.update({
            "corner_radius": 8,
            "border_width": 0,
            "hover_color": BLUE_ACCENT,
            "fg_color": GRAY_700,
            "text_color": GRAY_100,
            "height": 40
        })
        super().__init__(*args, **kwargs)

class DirectorySelector(ctk.CTkFrame):
    """Frame containing a path entry and browse button"""
    def __init__(self, master, label_text, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        
        # Label
        self.label = ctk.CTkLabel(self, text=label_text, anchor="w")
        self.label.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 0))
        
        # Path entry and browse button container
        self.container = ctk.CTkFrame(self)
        self.container.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        self.container.grid_columnconfigure(0, weight=1)
        
        # Path entry
        self.path_var = ctk.StringVar()
        self.path_entry = ctk.CTkEntry(self.container, textvariable=self.path_var)
        self.path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        # Browse button
        self.browse_button = RoundedButton(
            self.container, 
            text="Browse", 
            command=self.browse_directory,
            width=80
        )
        self.browse_button.grid(row=0, column=1)
    
    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.path_var.set(directory)
    
    def get_path(self):
        return self.path_var.get()
    
    def set_path(self, path):
        self.path_var.set(path)

class StatusBar(ctk.CTkFrame):
    """Status bar to display operations and progress"""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        
        # Status label
        self.status_var = ctk.StringVar(value="Ready")
        self.status_label = ctk.CTkLabel(
            self, 
            textvariable=self.status_var,
            anchor="w"
        )
        self.status_label.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        # Progress bar
        self.progress = ctk.CTkProgressBar(self)
        self.progress.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 5))
        self.progress.set(0)
    
    def update_status(self, text, progress_value=None):
        self.status_var.set(text)
        if progress_value is not None:
            self.progress.set(progress_value)
        self.update()
    
    def reset(self):
        self.status_var.set("Ready")
        self.progress.set(0)

class ModifiedFilesDialog(ctk.CTkToplevel):
    def __init__(self, parent, modified_files, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.modified_files = modified_files
        self.title("Review Modified Files")
        self.geometry("700x500")
        self.minsize(600, 400)
        
        self.selected_indices = []
        self.apply_to_all = False
        self.selection_vars = []
        
        self._create_ui()
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        parent.wait_window(self)
    
    def _create_ui(self):
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Header
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        ctk.CTkLabel(
            header_frame,
            text="Select Modified Files to Update",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=10, pady=5)
        
        ctk.CTkLabel(
            header_frame,
            text="Files with different sizes are listed below. Check the ones you want to update.",
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", padx=10, pady=0)
        
        # Files list in a scrollable frame
        files_frame = ctk.CTkScrollableFrame(self)
        files_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=0)
        files_frame.grid_columnconfigure(0, weight=1)
        
        # Add each file with checkbox
        for i, comparison in enumerate(self.modified_files):
            file_frame = self._create_file_row(files_frame, comparison, i)
            file_frame.grid(row=i, column=0, sticky="ew", padx=5, pady=5)
        
        # Bottom actions
        action_frame = ctk.CTkFrame(self)
        action_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        
        # "Apply to all" checkbox
        self.apply_all_var = ctk.BooleanVar(value=False)
        apply_all_check = ctk.CTkCheckBox(
            action_frame,
            text="Apply same action to all files",
            variable=self.apply_all_var
        )
        apply_all_check.pack(side="left", padx=10, pady=10)
        
        # Buttons
        ctk.CTkButton(
            action_frame,
            text="Select Newer Files",
            command=self._select_newer_files,
            fg_color=BLUE_ACCENT
        ).pack(side="right", padx=5, pady=10)
        
        ctk.CTkButton(
            action_frame,
            text="Select All",
            command=self._select_all_files
        ).pack(side="right", padx=5, pady=10)
        
        ctk.CTkButton(
            action_frame,
            text="Select None",
            command=self._select_no_files
        ).pack(side="right", padx=5, pady=10)
        
        ctk.CTkButton(
            action_frame,
            text="Confirm Selection",
            command=self._confirm_selection,
            fg_color=GREEN_SUCCESS
        ).pack(side="right", padx=5, pady=10)
    
    def _create_file_row(self, parent, comparison, index):
        """Create a row for a modified file with comparison information"""
        frame = ctk.CTkFrame(parent)
        frame.grid_columnconfigure(1, weight=1)
        
        # Add checkbox
        var = ctk.BooleanVar(value=comparison.is_newer)  # Default select newer files
        self.selection_vars.append(var)
        
        checkbox = ctk.CTkCheckBox(
            frame,
            text="",
            variable=var,
            width=20,
            onvalue=True,
            offvalue=False
        )
        checkbox.grid(row=0, column=0, rowspan=2, padx=5, pady=5)
        
        # Add file info
        # Filename (as header)
        filename = comparison.source_file.filename
        ctk.CTkLabel(
            frame,
            text=filename,
            font=ctk.CTkFont(weight="bold")
        ).grid(row=0, column=1, sticky="w", padx=5)
        
        # Create info subframe
        info_frame = ctk.CTkFrame(frame)
        info_frame.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        info_frame.grid_columnconfigure(1, weight=1)
        info_frame.grid_columnconfigure(3, weight=1)
        
        # Source file info with indicator
        source_label = ctk.CTkLabel(
            info_frame,
            text="Source:",
            font=ctk.CTkFont(weight="bold")
        )
        source_label.grid(row=0, column=0, sticky="w", padx=5, pady=2)
        
        if comparison.is_newer:
            newer_indicator = ctk.CTkLabel(
                info_frame,
                text="NEWER",
                text_color=GREEN_SUCCESS,
                font=ctk.CTkFont(weight="bold", size=10)
            )
            newer_indicator.grid(row=0, column=1, sticky="w", padx=0, pady=2)
        
        source_size = ctk.CTkLabel(
            info_frame,
            text=f"Size: {comparison.source_file.size_str}"
        )
        source_size.grid(row=1, column=0, columnspan=2, sticky="w", padx=5, pady=0)
        
        source_date = ctk.CTkLabel(
            info_frame,
            text=f"Modified: {comparison.source_file.modified_date_str}"
        )
        source_date.grid(row=2, column=0, columnspan=2, sticky="w", padx=5, pady=0)
        
        # Destination file info
        dest_label = ctk.CTkLabel(
            info_frame,
            text="Destination:",
            font=ctk.CTkFont(weight="bold")
        )
        dest_label.grid(row=0, column=2, sticky="w", padx=(20, 5), pady=2)
        
        if not comparison.is_newer:
            newer_indicator = ctk.CTkLabel(
                info_frame,
                text="NEWER", 
                text_color=GREEN_SUCCESS,
                font=ctk.CTkFont(weight="bold", size=10)
            )
            newer_indicator.grid(row=0, column=3, sticky="w", padx=0, pady=2)
        
        dest_size = ctk.CTkLabel(
            info_frame,
            text=f"Size: {comparison.dest_file.size_str}"
        )
        dest_size.grid(row=1, column=2, columnspan=2, sticky="w", padx=(20, 5), pady=0)
        
        dest_date = ctk.CTkLabel(
            info_frame,
            text=f"Modified: {comparison.dest_file.modified_date_str}"
        )
        dest_date.grid(row=2, column=2, columnspan=2, sticky="w", padx=(20, 5), pady=0)
        
        return frame
    
    def _confirm_selection(self):
        """Confirm the selection and close the dialog"""
        self.selected_indices = [i for i, var in enumerate(self.selection_vars) if var.get()]
        self.apply_to_all = self.apply_all_var.get()
        self.destroy()
    
    def _select_all_files(self):
        """Select all files"""
        for var in self.selection_vars:
            var.set(True)
    
    def _select_no_files(self):
        """Deselect all files"""
        for var in self.selection_vars:
            var.set(False)
    
    def _select_newer_files(self):
        """Select only files that are newer in the source"""
        for i, comparison in enumerate(self.modified_files):
            self.selection_vars[i].set(comparison.is_newer)

class ResultsDisplay(ctk.CTkScrollableFrame):
    """Scrollable frame to display scan results"""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        
        # Summary label
        self.summary_var = ctk.StringVar(value="No scan results yet.")
        self.summary_label = ctk.CTkLabel(
            self, 
            textvariable=self.summary_var,
            anchor="w",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.summary_label.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        # Details
        self.details_frame = ctk.CTkFrame(self)
        self.details_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.details_frame.grid_columnconfigure(0, weight=1)
    
    def clear(self):
        """Clear the results display"""
        for widget in self.details_frame.winfo_children():
            widget.destroy()
        self.summary_var.set("No scan results yet.")
    
    def update_with_results(self, result: ScanResult):
        """Update the display with scan results"""
        self.clear()
        
        # Update summary
        total_changes = len(result.new_files) + len(result.modified_files)
        self.summary_var.set(f"Scan Results - {total_changes} files to update")
        
        # Add stats
        stats_frame = ctk.CTkFrame(self.details_frame)
        stats_frame.grid(row=0, column=0, sticky="ew", pady=5)
        
        ctk.CTkLabel(stats_frame, text=f"New files: {len(result.new_files)}").grid(row=0, column=0, sticky="w", padx=10, pady=2)
        ctk.CTkLabel(stats_frame, text=f"Modified files: {len(result.modified_files)}").grid(row=1, column=0, sticky="w", padx=10, pady=2)
        ctk.CTkLabel(stats_frame, text=f"Missing files: {len(result.missing_files)}").grid(row=2, column=0, sticky="w", padx=10, pady=2)
        
        # Add information about duplicates if deep scan was performed
        if result.performed_deep_scan:
            duplicate_text = f"Files in different locations: {len(result.duplicate_locations)}"
            duplicate_label = ctk.CTkLabel(
                stats_frame, 
                text=duplicate_text,
                text_color=ORANGE_WARNING if result.duplicate_locations else None
            )
            duplicate_label.grid(row=3, column=0, sticky="w", padx=10, pady=2)
        
        ctk.CTkLabel(stats_frame, text=f"Scan time: {result.scan_time}").grid(row=4, column=0, sticky="w", padx=10, pady=2)
        
        # Add details for new files
        if result.new_files:
            self._add_section("New Files", result.new_files, row=1)
        
        # Add details for modified files
        if result.modified_files:
            self._add_modified_section("Modified Files", result.modified_files, row=2)
            
        # Add details for duplicate files
        if result.performed_deep_scan and result.duplicate_locations:
            self._add_duplicate_section("Files in Different Locations", result.duplicate_locations, row=3)
    
    def _add_section(self, title, files, row):
        """Add a section with file details"""
        section = ctk.CTkFrame(self.details_frame)
        section.grid(row=row, column=0, sticky="ew", pady=5)
        section.grid_columnconfigure(0, weight=1)
        
        # Section title
        ctk.CTkLabel(
            section, 
            text=title,
            font=ctk.CTkFont(weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=10, pady=5)
        
        # List first 10 files
        for i, file_info in enumerate(files[:10]):
            # Format display path (last part of path for clarity)
            parts = Path(file_info.relative_path).parts
            display_path = file_info.relative_path
            if len(parts) > 2:
                display_path = f".../{'/'.join(parts[-2:])}"
            
            # Format size in human-readable format
            size_str = self._format_size(file_info.size)
            
            ctk.CTkLabel(
                section, 
                text=f"{display_path} ({size_str})",
                anchor="w"
            ).grid(row=i+1, column=0, sticky="w", padx=20, pady=2)
        
        # Show count if more files exist
        remaining = len(files) - 10
        if remaining > 0:
            ctk.CTkLabel(
                section, 
                text=f"... and {remaining} more files",
                anchor="w",
                text_color=GRAY_500
            ).grid(row=11, column=0, sticky="w", padx=20, pady=(2, 5))
    
    def _add_modified_section(self, title, modified_files, row):
        """Add a section with modified file details"""
        section = ctk.CTkFrame(self.details_frame)
        section.grid(row=row, column=0, sticky="ew", pady=5)
        section.grid_columnconfigure(0, weight=1)
        
        # Section title
        ctk.CTkLabel(
            section, 
            text=title,
            font=ctk.CTkFont(weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=10, pady=5)
        
        # List first 10 files
        for i, file_comparison in enumerate(modified_files[:10]):
            # Format display path (last part of path for clarity)
            parts = Path(file_comparison.source_file.relative_path).parts
            display_path = file_comparison.source_file.relative_path
            if len(parts) > 2:
                display_path = f".../{'/'.join(parts[-2:])}"
            
            # Add newer indicator if applicable
            newer_indicator = " (newer)" if file_comparison.is_newer else ""
            
            # Format size
            source_size = self._format_size(file_comparison.source_file.size)
            dest_size = self._format_size(file_comparison.dest_file.size)
            
            # Display path and sizes
            ctk.CTkLabel(
                section, 
                text=f"{display_path}{newer_indicator} - Source: {source_size}, Dest: {dest_size}",
                anchor="w"
            ).grid(row=i+1, column=0, sticky="w", padx=20, pady=2)
        
        # Show count if more files exist
        remaining = len(modified_files) - 10
        if remaining > 0:
            ctk.CTkLabel(
                section, 
                text=f"... and {remaining} more modified files",
                anchor="w",
                text_color=GRAY_500
            ).grid(row=11, column=0, sticky="w", padx=20, pady=(2, 5))
    
    def _add_duplicate_section(self, title, duplicates, row):
        """Add a section showing duplicate files in different locations"""
        section = ctk.CTkFrame(self.details_frame)
        section.grid(row=row, column=0, sticky="ew", pady=5)
        section.grid_columnconfigure(0, weight=1)
        
        # Section title with warning color
        ctk.CTkLabel(
            section, 
            text=title,
            font=ctk.CTkFont(weight="bold"),
            text_color=ORANGE_WARNING
        ).grid(row=0, column=0, sticky="w", padx=10, pady=5)
        
        # List first 10 duplicates
        for i, (source_info, dest_info) in enumerate(duplicates[:10]):
            # Create a frame for each duplicate pair
            pair_frame = ctk.CTkFrame(section)
            pair_frame.grid(row=i+1, column=0, sticky="ew", padx=20, pady=2)
            pair_frame.grid_columnconfigure(0, weight=1)
            
            # File name and size
            filename = source_info.filename
            size_str = self._format_size(source_info.size)
            
            ctk.CTkLabel(
                pair_frame,
                text=f"{filename} ({size_str})",
                anchor="w",
                font=ctk.CTkFont(weight="bold")
            ).grid(row=0, column=0, sticky="w", padx=5, pady=(5, 0))
            
            # Source location
            source_path = source_info.relative_path
            ctk.CTkLabel(
                pair_frame,
                text=f"Source: {source_path}",
                anchor="w"
            ).grid(row=1, column=0, sticky="w", padx=5, pady=0)
            
            # Destination location
            dest_path = dest_info.relative_path
            ctk.CTkLabel(
                pair_frame,
                text=f"Destination: {dest_path}",
                anchor="w"
            ).grid(row=2, column=0, sticky="w", padx=5, pady=(0, 5))
        
        # Show count if more duplicates exist
        remaining = len(duplicates) - 10
        if remaining > 0:
            ctk.CTkLabel(
                section, 
                text=f"... and {remaining} more duplicate files",
                anchor="w",
                text_color=GRAY_500
            ).grid(row=11, column=0, sticky="w", padx=20, pady=(2, 5))
    
    def _format_size(self, size_bytes):
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

class CompareDrivesApp(ctk.CTk):
    """Main application window"""
    def __init__(self):
        super().__init__()
        
        # Configure window
        self.title("Drive Comparison Tool")
        self.geometry("800x750")  # Increased height from 600 to 750
        self.minsize(700, 650)    # Increased minimum height from 500 to 650
        
        # Grid configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)  # Give more weight to the results area (row 3)
        
        # Create UI components
        self._create_selectors()
        self._create_options_frame()
        self._create_action_buttons()
        self._create_results_area()
        self._create_status_bar()
        
        # Comparator instance
        self.comparator = DriveComparator()
        self.scan_result = None
        
        # Check for existing results
        self._check_for_existing_results()
    
    def _create_selectors(self):
        """Create the directory selector area"""
        selectors_frame = ctk.CTkFrame(self)
        selectors_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        selectors_frame.grid_columnconfigure(0, weight=1)
        
        # Destination drive selector
        self.destination_selector = DirectorySelector(
            selectors_frame,
            "1. Destination Drive (to be updated)"
        )
        self.destination_selector.grid(row=0, column=0, sticky="ew", pady=5)
        
        # Source drive selector
        self.source_selector = DirectorySelector(
            selectors_frame,
            "2. Drive to Check (contains files to compare)"
        )
        self.source_selector.grid(row=1, column=0, sticky="ew", pady=5)
        
        # Output folder selector
        self.output_selector = DirectorySelector(
            selectors_frame,
            "3. Newer and Changed Data Folder (stores logs and results)"
        )
        self.output_selector.grid(row=2, column=0, sticky="ew", pady=5)
    
    def _create_options_frame(self):
        """Create the options frame with scan and update settings"""
        options_frame = ctk.CTkFrame(self)
        options_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        options_frame.grid_columnconfigure((0, 1), weight=1)  # Equal weight for both columns
        
        # Scan options
        scan_options = ctk.CTkFrame(options_frame)
        scan_options.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        scan_label = ctk.CTkLabel(
            scan_options, 
            text="Scan Options",
            font=ctk.CTkFont(weight="bold")
        )
        scan_label.pack(anchor="w", padx=10, pady=(5, 0))
        
        # Deep scan option
        self.deep_scan_var = ctk.BooleanVar(value=True)
        deep_scan_checkbox = ctk.CTkCheckBox(
            scan_options,
            text="Perform deep scan to find files in different locations",
            variable=self.deep_scan_var
        )
        deep_scan_checkbox.pack(anchor="w", padx=10, pady=5)
        
        # Update options
        update_options = ctk.CTkFrame(options_frame)
        update_options.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        
        update_label = ctk.CTkLabel(
            update_options, 
            text="Update Options",
            font=ctk.CTkFont(weight="bold")
        )
        update_label.pack(anchor="w", padx=10, pady=(5, 0))
        
        # Duplicate handling option
        self.duplicate_handling_var = ctk.StringVar(value="ask")
        duplicate_frame = ctk.CTkFrame(update_options)
        duplicate_frame.pack(fill="x", padx=10, pady=5)
        
        dup_label = ctk.CTkLabel(duplicate_frame, text="Handle duplicates:")
        dup_label.pack(anchor="w")
        
        dup_ask = ctk.CTkRadioButton(
            duplicate_frame, 
            text="Ask", 
            variable=self.duplicate_handling_var,
            value="ask"
        )
        dup_ask.pack(anchor="w", padx=20)
        
        dup_copy = ctk.CTkRadioButton(
            duplicate_frame, 
            text="Copy to new location", 
            variable=self.duplicate_handling_var,
            value="copy"
        )
        dup_copy.pack(anchor="w", padx=20)
        
        dup_skip = ctk.CTkRadioButton(
            duplicate_frame, 
            text="Skip", 
            variable=self.duplicate_handling_var,
            value="skip"
        )
        dup_skip.pack(anchor="w", padx=20)
    
    def _create_action_buttons(self):
        """Create action buttons"""
        buttons_frame = ctk.CTkFrame(self)
        buttons_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        # Start Scan button
        self.scan_button = RoundedButton(
            buttons_frame,
            text="Start Scan",
            command=self.start_scan,
            fg_color=BLUE_ACCENT
        )
        self.scan_button.pack(side="left", padx=(10, 5), pady=10)
        
        # Update Destination button (initially disabled)
        self.update_button = RoundedButton(
            buttons_frame,
            text="Update Destination",
            command=self.update_destination,
            state="disabled",
            fg_color=GREEN_SUCCESS
        )
        self.update_button.pack(side="left", padx=5, pady=10)
    
    def _create_results_area(self):
        """Create results display area"""
        self.results_display = ResultsDisplay(self)
        self.results_display.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 10))
    
    def _create_status_bar(self):
        """Create status bar"""
        self.status_bar = StatusBar(self)
        self.status_bar.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 10))
    
    def _check_for_existing_results(self):
        """Check for existing scan results in the output folder"""
        # We'll implement this when the user selects an output folder
        pass
    
    def _load_scan_results(self, output_path):
        """Try to load existing scan results from the output folder"""
        result_file = os.path.join(output_path, "scan_result.json")
        if os.path.exists(result_file):
            try:
                result = DriveComparator.load_result(result_file)
                if result:
                    self.scan_result = result
                    self.results_display.update_with_results(result)
                    self.update_button.configure(state="normal")
                    return True
            except Exception as e:
                print(f"Error loading scan results: {e}")
        return False
    
    def start_scan(self):
        """Start the directory comparison scan"""
        # Get directory paths
        destination_path = self.destination_selector.get_path()
        source_path = self.source_selector.get_path()
        output_path = self.output_selector.get_path()
        perform_deep_scan = self.deep_scan_var.get()
        
        # Validate paths
        if not destination_path or not source_path or not output_path:
            messagebox.showerror("Error", "Please select all required directories.")
            return
        
        if not os.path.exists(destination_path) or not os.path.exists(source_path):
            messagebox.showerror("Error", "One or more selected directories do not exist.")
            return
        
        # Disable buttons during scan
        self.scan_button.configure(state="disabled")
        self.update_button.configure(state="disabled")
        
        # Update status
        self.status_bar.update_status("Starting scan...", 0.1)
        
        # Run scan in a background thread
        def run_scan():
            try:
                # Update status periodically
                self.status_bar.update_status("Scanning directories...", 0.3)
                
                # Run scan with deep scan option
                result = self.comparator.scan_directories(
                    destination_path, 
                    source_path,
                    perform_deep_scan=perform_deep_scan
                )
                
                # Save results
                self.status_bar.update_status("Saving scan results...", 0.8)
                self.comparator.save_result(output_path)
                
                # Update UI
                self.status_bar.update_status("Scan completed successfully.", 1.0)
                self.scan_result = result
                
                # Update results display in the main thread
                self.after(100, lambda: self.results_display.update_with_results(result))
                self.after(100, lambda: self.update_button.configure(state="normal"))
                self.after(3000, lambda: self.status_bar.reset())
                
            except Exception as e:
                # Handle errors
                error_msg = str(e)
                self.after(100, lambda: messagebox.showerror("Scan Error", f"An error occurred during the scan:\n{error_msg}"))
                self.after(100, lambda: self.status_bar.update_status(f"Error: {error_msg}", 0))
            finally:
                # Re-enable scan button
                self.after(100, lambda: self.scan_button.configure(state="normal"))
        
        # Start the thread
        threading.Thread(target=run_scan, daemon=True).start()
    
    def update_destination(self):
        """Update the destination directory with newer files"""
        # Check if we have scan results
        if not self.scan_result:
            messagebox.showerror("Error", "No scan results available. Please run a scan first.")
            return
        
        # Get duplicate handling method
        duplicate_handling = self.duplicate_handling_var.get()
        
        # Handle modified files carefully
        modified_files_to_update = None
        apply_to_all_modified = False
        
        if self.scan_result.modified_files:
            # Show dialog to select which modified files to update
            dialog = ModifiedFilesDialog(self, self.scan_result.modified_files)
            modified_files_to_update = dialog.selected_indices
            apply_to_all_modified = dialog.apply_to_all
            
            # If no files were selected, confirm with the user
            if not modified_files_to_update:
                if not messagebox.askyesno(
                    "No Modified Files Selected",
                    "You didn't select any modified files to update. Do you want to continue with only new files?"
                ):
                    return
        
        # If there are duplicates and the handling is set to "ask", prompt the user
        if (duplicate_handling == "ask" and self.scan_result.performed_deep_scan and 
            self.scan_result.duplicate_locations):
            
            response = messagebox.askyesnocancel(
                "Duplicate Files Found",
                f"Found {len(self.scan_result.duplicate_locations)} files that exist in different locations.\n\n"
                "What would you like to do with these duplicate files?\n"
                "• Yes: Copy files to new locations\n"
                "• No: Skip duplicate files\n"
                "• Cancel: Cancel the update operation"
            )
            
            if response is None:  # Cancel
                return
            
            # Update duplicate_handling based on user response
            duplicate_handling = "copy" if response else "skip"
        
        # Calculate total changes
        total_changes = len(self.scan_result.new_files)
        
        # Add modified files if updating them
        if modified_files_to_update is None:
            total_changes += len(self.scan_result.modified_files)
        else:
            total_changes += len(modified_files_to_update)
        
        # Add duplicates if copying them
        if duplicate_handling == "copy":
            total_changes += len(self.scan_result.duplicate_locations)
            
        # Confirm update operation
        message = f"This will update {total_changes} files in the destination directory.\n\n"
        message += f"- {len(self.scan_result.new_files)} new files will be copied.\n"
        
        # Modified files details
        if modified_files_to_update is None:
            message += f"- All {len(self.scan_result.modified_files)} modified files will be updated.\n"
        elif modified_files_to_update:
            message += f"- {len(modified_files_to_update)} modified files will be updated.\n"
        else:
            message += "- No modified files will be updated.\n"
        
        # Duplicates details
        if duplicate_handling == "copy" and self.scan_result.duplicate_locations:
            message += f"- {len(self.scan_result.duplicate_locations)} files will be copied to new locations.\n"
        
        message += "\nDo you want to continue?"
        
        if not messagebox.askyesno("Confirm Update", message):
            return
        
        # Get output path
        output_path = self.output_selector.get_path()
        
        # Disable buttons during update
        self.scan_button.configure(state="disabled")
        self.update_button.configure(state="disabled")
        
        # Update status
        self.status_bar.update_status("Starting update...", 0.1)
        
        # Run update in a background thread
        def run_update():
            try:
                # Update files
                self.status_bar.update_status("Updating files...", 0.5)
                updated_count, errors = DriveComparator.update_destination(
                    self.scan_result, 
                    output_path,
                    handle_duplicates=duplicate_handling,
                    modified_files_to_update=modified_files_to_update
                )
                
                # Update UI
                self.status_bar.update_status(f"Update completed. {updated_count} files updated.", 1.0)
                
                # Show summary
                if errors:
                    self.after(100, lambda: messagebox.showwarning(
                        "Update Completed with Errors",
                        f"Updated {updated_count} files with {len(errors)} errors.\n"
                        f"See the log file in the output folder for details."
                    ))
                else:
                    self.after(100, lambda: messagebox.showinfo(
                        "Update Completed",
                        f"Successfully updated {updated_count} files."
                    ))
                
                self.after(3000, lambda: self.status_bar.reset())
                
            except Exception as e:
                # Handle errors
                error_msg = str(e)
                self.after(100, lambda: messagebox.showerror("Update Error", f"An error occurred during the update:\n{error_msg}"))
                self.after(100, lambda: self.status_bar.update_status(f"Error: {error_msg}", 0))
            finally:
                # Re-enable buttons
                self.after(100, lambda: self.scan_button.configure(state="normal"))
                self.after(100, lambda: self.update_button.configure(state="normal"))
        
        # Start the thread
        threading.Thread(target=run_update, daemon=True).start() 