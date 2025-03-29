import os
import json
import time
import datetime
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Set, Tuple, Optional, DefaultDict
from collections import defaultdict

@dataclass
class FileInfo:
    path: str
    size: int
    modified_time: float
    relative_path: str  # Path relative to the root directory
    filename: str = ""
    
    def __post_init__(self):
        self.filename = os.path.basename(self.path)
    
    @property
    def modified_date_str(self) -> str:
        """Return a human-readable modification date string"""
        return datetime.datetime.fromtimestamp(self.modified_time).strftime("%Y-%m-%d %H:%M:%S")
    
    @property
    def size_str(self) -> str:
        """Return a human-readable file size string"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if self.size < 1024.0:
                return f"{self.size:.1f} {unit}"
            self.size /= 1024.0
        return f"{self.size:.1f} PB"

@dataclass
class FileComparison:
    source_file: FileInfo
    dest_file: FileInfo
    is_newer: bool = False  # True if source is newer than destination
    
    def __post_init__(self):
        self.is_newer = self.source_file.modified_time > self.dest_file.modified_time

@dataclass
class ScanResult:
    new_files: List[FileInfo]
    modified_files: List[FileComparison]  # Changed from List[FileInfo] to List[FileComparison]
    missing_files: List[FileInfo]
    duplicate_locations: List[Tuple[FileInfo, FileInfo]]  # (source_file, dest_file) pairs of files that exist in different locations
    scan_time: str
    destination_path: str
    source_path: str
    performed_deep_scan: bool = False

class DriveComparator:
    def __init__(self):
        self.result = None
        self.destination_files = {}  # relative_path -> FileInfo
        self.source_files = {}  # relative_path -> FileInfo
        # For deep scan
        self.destination_by_size_name = defaultdict(list)  # (size, filename) -> [FileInfo]
        self.source_by_size_name = defaultdict(list)  # (size, filename) -> [FileInfo]
    
    def _index_directory(self, root_path: str) -> Tuple[Dict[str, FileInfo], Dict[Tuple[int, str], List[FileInfo]]]:
        """
        Create an index of all files in the directory with their metadata.
        Uses relative paths as keys for efficient comparison.
        """
        root = Path(root_path)
        file_index = {}
        size_name_index = defaultdict(list)
        
        # Walk the directory tree
        for dirpath, _, filenames in os.walk(root_path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                try:
                    stat_info = os.stat(file_path)
                    relative_path = str(Path(file_path).relative_to(root))
                    
                    file_info = FileInfo(
                        path=file_path,
                        size=stat_info.st_size,
                        modified_time=stat_info.st_mtime,
                        relative_path=relative_path,
                        filename=filename
                    )
                    file_index[relative_path] = file_info
                    
                    # Add to size-name index for deep scan
                    size_name_index[(stat_info.st_size, filename)].append(file_info)
                    
                except (PermissionError, FileNotFoundError) as e:
                    print(f"Error accessing {file_path}: {e}")
        
        return file_index, size_name_index
    
    def scan_directories(self, destination_path: str, source_path: str, perform_deep_scan=True) -> ScanResult:
        """
        Compare files between destination and source directories.
        Returns information about new, modified, and missing files.
        
        Args:
            destination_path: Path to the destination directory
            source_path: Path to the source directory
            perform_deep_scan: If True, will perform a deeper scan to identify files in different locations
        """
        print(f"Indexing destination directory: {destination_path}")
        self.destination_files, self.destination_by_size_name = self._index_directory(destination_path)
        
        print(f"Indexing source directory: {source_path}")
        self.source_files, self.source_by_size_name = self._index_directory(source_path)
        
        # Find new and modified files (in source but not in destination or different)
        new_files = []
        modified_files = []
        duplicate_locations = []  # Files that exist in both but in different locations
        potential_new_files = []  # Files not found by path but need deep scan
        
        # First pass: Check by relative path
        for rel_path, source_info in self.source_files.items():
            if rel_path not in self.destination_files:
                potential_new_files.append(source_info)
            else:
                dest_info = self.destination_files[rel_path]
                # Compare by size first (quick comparison)
                if source_info.size != dest_info.size:
                    # Only add to modified_files if sizes differ
                    comparison = FileComparison(source_info, dest_info)
                    modified_files.append(comparison)
        
        # Second pass (deep scan): Look for files with same name and size but in different locations
        if perform_deep_scan and potential_new_files:
            print("Performing deep scan to identify files in different locations...")
            for source_info in potential_new_files:
                key = (source_info.size, source_info.filename)
                if key in self.destination_by_size_name:
                    # Found a match by size and filename in destination
                    for dest_info in self.destination_by_size_name[key]:
                        duplicate_locations.append((source_info, dest_info))
                    # Don't add to new_files since we found a match
                else:
                    # No match found even in deep scan
                    new_files.append(source_info)
        else:
            # If deep scan is disabled, all potential new files are marked as new
            new_files = potential_new_files
        
        # Find missing files (in destination but not in source)
        missing_files = [
            info for rel_path, info in self.destination_files.items() 
            if rel_path not in self.source_files
        ]
        
        # Create scan result
        result = ScanResult(
            new_files=new_files,
            modified_files=modified_files,
            missing_files=missing_files,
            duplicate_locations=duplicate_locations,
            scan_time=time.strftime("%Y-%m-%d %H:%M:%S"),
            destination_path=destination_path,
            source_path=source_path,
            performed_deep_scan=perform_deep_scan
        )
        
        self.result = result
        return result
    
    def save_result(self, output_path: str) -> str:
        """
        Save scan results to a file for later use during the update phase.
        """
        if not self.result:
            raise ValueError("No scan results available. Run scan_directories first.")
        
        # Create output directory if it doesn't exist
        output_dir = Path(output_path)
        os.makedirs(output_dir, exist_ok=True)
        
        # Save result to JSON file
        result_file = output_dir / "scan_result.json"
        
        # Convert dataclasses to dictionaries
        result_dict = {
            "new_files": [asdict(f) for f in self.result.new_files],
            "modified_files": [{"source_file": asdict(comp.source_file), 
                               "dest_file": asdict(comp.dest_file), 
                               "is_newer": comp.is_newer} for comp in self.result.modified_files],
            "missing_files": [asdict(f) for f in self.result.missing_files],
            "duplicate_locations": [(asdict(src), asdict(dst)) for src, dst in self.result.duplicate_locations],
            "scan_time": self.result.scan_time,
            "destination_path": self.result.destination_path,
            "source_path": self.result.source_path,
            "performed_deep_scan": self.result.performed_deep_scan
        }
        
        with open(result_file, 'w') as f:
            json.dump(result_dict, f, indent=2)
        
        return str(result_file)
    
    @staticmethod
    def load_result(result_file: str) -> Optional[ScanResult]:
        """
        Load scan results from a file.
        """
        try:
            with open(result_file, 'r') as f:
                data = json.load(f)
            
            # Convert dictionaries back to dataclasses
            duplicate_locations = []
            if "duplicate_locations" in data:
                duplicate_locations = [
                    (FileInfo(**src), FileInfo(**dst)) 
                    for src, dst in data["duplicate_locations"]
                ]
            
            # Handle both old and new format for modified_files
            modified_files = []
            if "modified_files" in data:
                if isinstance(data["modified_files"][0], dict) and "source_file" in data["modified_files"][0]:
                    # New format
                    modified_files = [
                        FileComparison(
                            source_file=FileInfo(**item["source_file"]),
                            dest_file=FileInfo(**item["dest_file"]),
                            is_newer=item["is_newer"]
                        ) for item in data["modified_files"]
                    ]
                else:
                    # Old format (for backward compatibility)
                    modified_files = [FileInfo(**f) for f in data["modified_files"]]
            
            result = ScanResult(
                new_files=[FileInfo(**f) for f in data["new_files"]],
                modified_files=modified_files,
                missing_files=[FileInfo(**f) for f in data["missing_files"]],
                duplicate_locations=duplicate_locations,
                scan_time=data["scan_time"],
                destination_path=data["destination_path"],
                source_path=data["source_path"],
                performed_deep_scan=data.get("performed_deep_scan", False)
            )
            
            return result
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading scan results: {e}")
            return None
    
    @staticmethod
    def update_destination(scan_result: ScanResult, output_path: str, 
                          handle_duplicates="ask", 
                          modified_files_to_update=None) -> Tuple[int, List[str]]:
        """
        Update destination by copying new and modified files from the 'newer and changed data folder'.
        Returns the number of files updated and a list of errors encountered.
        
        Args:
            scan_result: The scan result containing files to update
            output_path: Path to store logs and output
            handle_duplicates: How to handle duplicate files found in different locations
                              'ask': Ask the user (default)
                              'copy': Copy to new location
                              'skip': Skip duplicate files
            modified_files_to_update: List of indices of modified files to update, if None all modified files will be updated
        """
        import shutil
        
        updated_count = 0
        errors = []
        
        # Update for new files
        for file_info in scan_result.new_files:
            try:
                source_path = os.path.join(scan_result.source_path, file_info.relative_path)
                dest_path = os.path.join(scan_result.destination_path, file_info.relative_path)
                
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                
                # Copy the file
                shutil.copy2(source_path, dest_path)
                updated_count += 1
            except Exception as e:
                errors.append(f"Error copying {file_info.relative_path}: {str(e)}")
        
        # Update for modified files
        if modified_files_to_update is None:
            # Update all modified files
            modified_to_update = scan_result.modified_files
        else:
            # Update only selected modified files
            modified_to_update = [scan_result.modified_files[i] for i in modified_files_to_update if i < len(scan_result.modified_files)]
        
        for file_comparison in modified_to_update:
            try:
                source_path = os.path.join(scan_result.source_path, file_comparison.source_file.relative_path)
                dest_path = os.path.join(scan_result.destination_path, file_comparison.source_file.relative_path)
                
                # Copy the file (overwrite existing)
                shutil.copy2(source_path, dest_path)
                updated_count += 1
            except Exception as e:
                errors.append(f"Error updating {file_comparison.source_file.relative_path}: {str(e)}")
        
        # Handle duplicate locations if deep scan was performed
        if scan_result.performed_deep_scan and scan_result.duplicate_locations:
            # Log details about duplicate files
            duplicates_log = os.path.join(output_path, "duplicates_log.txt")
            with open(duplicates_log, 'w') as f:
                f.write(f"Duplicate files found: {len(scan_result.duplicate_locations)}\n\n")
                for source_info, dest_info in scan_result.duplicate_locations:
                    f.write(f"File: {source_info.filename} (Size: {source_info.size} bytes)\n")
                    f.write(f"  Source: {source_info.relative_path}\n")
                    f.write(f"  Destination: {dest_info.relative_path}\n\n")
                
                if handle_duplicates == "copy":
                    f.write("All duplicates were copied to their new locations.\n")
                elif handle_duplicates == "skip":
                    f.write("All duplicates were skipped (not copied).\n")
            
            # Process duplicates based on handling option
            if handle_duplicates == "copy":
                for source_info, _ in scan_result.duplicate_locations:
                    try:
                        source_path = os.path.join(scan_result.source_path, source_info.relative_path)
                        dest_path = os.path.join(scan_result.destination_path, source_info.relative_path)
                        
                        # Create directory if it doesn't exist
                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                        
                        # Copy the file
                        shutil.copy2(source_path, dest_path)
                        updated_count += 1
                    except Exception as e:
                        errors.append(f"Error copying duplicate {source_info.relative_path}: {str(e)}")
        
        # Write update log
        log_file = os.path.join(output_path, "update_log.txt")
        with open(log_file, 'w') as f:
            f.write(f"Update completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Files updated: {updated_count}\n")
            f.write(f"New files: {len(scan_result.new_files)}\n")
            f.write(f"Modified files updated: {len(modified_to_update)}\n")
            if scan_result.performed_deep_scan:
                f.write(f"Duplicate files in different locations: {len(scan_result.duplicate_locations)}\n")
            f.write(f"Errors encountered: {len(errors)}\n\n")
            
            if errors:
                f.write("ERROR DETAILS:\n")
                for error in errors:
                    f.write(f"- {error}\n")
        
        return updated_count, errors 