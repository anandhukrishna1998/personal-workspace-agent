import shutil
import mimetypes
import hashlib
import os
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Optional
from mcp.server.fastmcp import FastMCP


# Initialize FastMCP server
mcp = FastMCP("file-manager")


@mcp.tool()
async def list_directory(path: str) -> str:
    """List contents of a directory.
    
    Args:
        path: Directory path to list
    """
    try:
        path_obj = Path(path)
        if not path_obj.exists():
            return f"Directory '{path}' does not exist."
        
        if not path_obj.is_dir():
            return f"'{path}' is not a directory."
        
        items = []
        for item in path_obj.iterdir():
            item_type = "📁" if item.is_dir() else "📄"
            size = ""
            if item.is_file():
                try:
                    size = f" ({item.stat().st_size} bytes)"
                except:
                    size = " (unknown size)"
            items.append(f"{item_type} {item.name}{size}")
        
        if not items:
            return f"Directory '{path}' is empty."
        
        return f"Contents of '{path}':\n" + "\n".join(sorted(items))
    
    except Exception as e:
        return f"Error listing directory: {str(e)}"


@mcp.tool()
async def read_file(file_path: str) -> str:
    """Read contents of a text file.
    
    Args:
        file_path: Path to the file to read
    """
    try:
        path_obj = Path(file_path)
        if not path_obj.exists():
            return f"File '{file_path}' does not exist."
        
        if not path_obj.is_file():
            return f"'{file_path}' is not a file."
        
        # Check file size (limit to 1MB for safety)
        if path_obj.stat().st_size > 1024 * 1024:
            return f"File '{file_path}' is too large (>1MB) to read."
        
        # Check if it's a text file
        mime_type, _ = mimetypes.guess_type(str(path_obj))
        if mime_type and not mime_type.startswith('text/'):
            return f"File '{file_path}' appears to be a binary file. MIME type: {mime_type}"
        
        with open(path_obj, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return f"Contents of '{file_path}':\n\n{content}"
    
    except UnicodeDecodeError:
        return f"File '{file_path}' cannot be read as text (encoding issue)."
    except Exception as e:
        return f"Error reading file: {str(e)}"


@mcp.tool()
async def write_file(file_path: str, content: str) -> str:
    """Write content to a file.
    
    Args:
        file_path: Path where to write the file
        content: Content to write to the file
    """
    try:
        path_obj = Path(file_path)
        
        # Create parent directories if they don't exist
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path_obj, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return f"Successfully wrote {len(content)} characters to '{file_path}'."
    
    except Exception as e:
        return f"Error writing file: {str(e)}"


@mcp.tool()
async def create_directory(dir_path: str) -> str:
    """Create a directory.
    
    Args:
        dir_path: Path of the directory to create
    """
    try:
        path_obj = Path(dir_path)
        path_obj.mkdir(parents=True, exist_ok=True)
        return f"Successfully created directory '{dir_path}'."
    
    except Exception as e:
        return f"Error creating directory: {str(e)}"


@mcp.tool()
async def delete_file_or_directory(path: str) -> str:
    """Delete a file or directory.
    
    Args:
        path: Path of the file or directory to delete
    """
    try:
        path_obj = Path(path)
        if not path_obj.exists():
            return f"Path '{path}' does not exist."
        
        if path_obj.is_file():
            path_obj.unlink()
            return f"Successfully deleted file '{path}'."
        elif path_obj.is_dir():
            shutil.rmtree(path_obj)
            return f"Successfully deleted directory '{path}' and all its contents."
        else:
            return f"'{path}' is neither a file nor a directory."
    
    except Exception as e:
        return f"Error deleting '{path}': {str(e)}"


@mcp.tool()
async def get_file_info(file_path: str) -> str:
    """Get detailed information about a file or directory.
    
    Args:
        file_path: Path to the file or directory
    """
    try:
        path_obj = Path(file_path)
        if not path_obj.exists():
            return f"Path '{file_path}' does not exist."
        
        stat = path_obj.stat()
        mime_type, encoding = mimetypes.guess_type(str(path_obj))
        
        info = f"""
File Information for '{file_path}':
- Type: {'Directory' if path_obj.is_dir() else 'File'}
- Size: {stat.st_size} bytes
- Created: {datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S')}
- Modified: {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}
- MIME Type: {mime_type or 'Unknown'}
- Encoding: {encoding or 'Unknown'}
- Absolute Path: {path_obj.resolve()}
        """.strip()
        
        return info
    
    except Exception as e:
        return f"Error getting file info: {str(e)}"


# ========== ADVANCED FEATURES ==========

@mcp.tool()
async def search_files_by_content(
    directory: str,
    search_term: str,
    file_extensions: Optional[str] = ".txt,.py,.md,.json,.csv"
) -> str:
    """Search for files containing specific text content.
    
    Args:
        directory: Directory to search in
        search_term: Text to search for
        file_extensions: Comma-separated file extensions to search (default: .txt,.py,.md,.json,.csv)
    """
    try:
        path_obj = Path(directory)
        if not path_obj.exists():
            return f"Directory '{directory}' does not exist."
        
        extensions = [ext.strip() for ext in file_extensions.split(',')]
        results = []
        
        for file_path in path_obj.rglob('*'):
            if file_path.is_file() and file_path.suffix in extensions:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if search_term.lower() in content.lower():
                            # Count occurrences
                            count = content.lower().count(search_term.lower())
                            results.append(f"📄 {file_path} ({count} matches)")
                except:
                    continue
        
        if not results:
            return f"No files containing '{search_term}' found in '{directory}'."
        
        return f"Found {len(results)} file(s) containing '{search_term}':\n" + "\n".join(results)
    
    except Exception as e:
        return f"Error searching files: {str(e)}"


@mcp.tool()
async def find_duplicate_files(directory: str, min_size: int = 0) -> str:
    """Find duplicate files in a directory based on MD5 hash.
    
    Args:
        directory: Directory to search for duplicates
        min_size: Minimum file size in bytes to consider (default: 0)
    """
    try:
        path_obj = Path(directory)
        if not path_obj.exists():
            return f"Directory '{directory}' does not exist."
        
        def get_file_hash(file_path: Path) -> str:
            """Calculate MD5 hash of a file."""
            hash_md5 = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        
        # Dictionary to store file hashes
        file_hashes: Dict[str, List[Path]] = defaultdict(list)
        total_files = 0
        
        for file_path in path_obj.rglob('*'):
            if file_path.is_file():
                try:
                    file_size = file_path.stat().st_size
                    if file_size >= min_size:
                        total_files += 1
                        file_hash = get_file_hash(file_path)
                        file_hashes[file_hash].append(file_path)
                except:
                    continue
        
        # Filter only duplicate groups
        duplicates = {hash_val: files for hash_val, files in file_hashes.items() if len(files) > 1}
        
        if not duplicates:
            return f"No duplicate files found in '{directory}' (scanned {total_files} files)."
        
        result = [f"Found {len(duplicates)} duplicate file group(s) (scanned {total_files} files):\n"]
        
        for hash_val, files in duplicates.items():
            size = files[0].stat().st_size
            result.append(f"\n🔄 Duplicate group (Size: {size} bytes, Hash: {hash_val[:8]}...):")
            for file_path in files:
                result.append(f"   - {file_path}")
        
        return "\n".join(result)
    
    except Exception as e:
        return f"Error finding duplicates: {str(e)}"


@mcp.tool()
async def organize_files_by_type(source_dir: str, target_dir: str) -> str:
    """Organize files into subdirectories based on their type.
    
    Args:
        source_dir: Source directory containing files to organize
        target_dir: Target directory where organized files will be placed
    """
    try:
        source_path = Path(source_dir)
        target_path = Path(target_dir)
        
        if not source_path.exists():
            return f"Source directory '{source_dir}' does not exist."
        
        target_path.mkdir(parents=True, exist_ok=True)
        
        # File type categories
        categories = {
            'Images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'],
            'Documents': ['.pdf', '.doc', '.docx', '.txt', '.md', '.odt'],
            'Spreadsheets': ['.xls', '.xlsx', '.csv', '.ods'],
            'Videos': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv'],
            'Audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a'],
            'Archives': ['.zip', '.rar', '.7z', '.tar', '.gz'],
            'Code': ['.py', '.js', '.java', '.cpp', '.c', '.h', '.cs', '.html', '.css'],
            'Others': []
        }
        
        moved_files = defaultdict(int)
        
        for file_path in source_path.rglob('*'):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                
                # Find category
                category = 'Others'
                for cat, extensions in categories.items():
                    if ext in extensions:
                        category = cat
                        break
                
                # Create category directory
                category_dir = target_path / category
                category_dir.mkdir(exist_ok=True)
                
                # Move file
                try:
                    destination = category_dir / file_path.name
                    # Handle name conflicts
                    counter = 1
                    while destination.exists():
                        stem = file_path.stem
                        destination = category_dir / f"{stem}_{counter}{ext}"
                        counter += 1
                    
                    shutil.copy2(file_path, destination)
                    moved_files[category] += 1
                except:
                    continue
        
        result = [f"Files organized from '{source_dir}' to '{target_dir}':\n"]
        for category, count in sorted(moved_files.items()):
            result.append(f"  {category}: {count} file(s)")
        
        return "\n".join(result)
    
    except Exception as e:
        return f"Error organizing files: {str(e)}"


@mcp.tool()
async def batch_rename_files(
    directory: str,
    pattern: str,
    replacement: str,
    file_extensions: Optional[str] = None
) -> str:
    """Batch rename files using pattern matching.
    
    Args:
        directory: Directory containing files to rename
        pattern: Regular expression pattern to match in filenames
        replacement: Replacement string
        file_extensions: Optional comma-separated file extensions to filter (e.g., '.txt,.py')
    """
    try:
        path_obj = Path(directory)
        if not path_obj.exists():
            return f"Directory '{directory}' does not exist."
        
        extensions = None
        if file_extensions:
            extensions = [ext.strip() for ext in file_extensions.split(',')]
        
        renamed_files = []
        
        for file_path in path_obj.iterdir():
            if file_path.is_file():
                # Filter by extension if specified
                if extensions and file_path.suffix not in extensions:
                    continue
                
                old_name = file_path.name
                new_name = re.sub(pattern, replacement, old_name)
                
                if new_name != old_name:
                    new_path = file_path.parent / new_name
                    
                    # Avoid overwriting existing files
                    if new_path.exists():
                        continue
                    
                    file_path.rename(new_path)
                    renamed_files.append(f"{old_name} → {new_name}")
        
        if not renamed_files:
            return f"No files matched the pattern '{pattern}' in '{directory}'."
        
        return f"Renamed {len(renamed_files)} file(s):\n" + "\n".join(renamed_files)
    
    except Exception as e:
        return f"Error renaming files: {str(e)}"


@mcp.tool()
async def get_directory_statistics(directory: str) -> str:
    """Get comprehensive statistics about a directory.
    
    Args:
        directory: Directory to analyze
    """
    try:
        path_obj = Path(directory)
        if not path_obj.exists():
            return f"Directory '{directory}' does not exist."
        
        stats = {
            'total_files': 0,
            'total_dirs': 0,
            'total_size': 0,
            'file_types': defaultdict(int),
            'largest_file': ('', 0),
            'oldest_file': ('', float('inf')),
            'newest_file': ('', 0)
        }
        
        for item in path_obj.rglob('*'):
            if item.is_file():
                stats['total_files'] += 1
                size = item.stat().st_size
                stats['total_size'] += size
                stats['file_types'][item.suffix or 'No extension'] += 1
                
                # Track largest file
                if size > stats['largest_file'][1]:
                    stats['largest_file'] = (str(item), size)
                
                # Track oldest/newest files
                mtime = item.stat().st_mtime
                if mtime < stats['oldest_file'][1]:
                    stats['oldest_file'] = (str(item), mtime)
                if mtime > stats['newest_file'][1]:
                    stats['newest_file'] = (str(item), mtime)
            
            elif item.is_dir():
                stats['total_dirs'] += 1
        
        # Format output
        result = [
            f"Directory Statistics for '{directory}':",
            f"\n📊 Overview:",
            f"  - Total Files: {stats['total_files']}",
            f"  - Total Directories: {stats['total_dirs']}",
            f"  - Total Size: {stats['total_size'] / (1024**2):.2f} MB",
            f"\n📁 File Types (Top 10):"
        ]
        
        for ext, count in sorted(stats['file_types'].items(), key=lambda x: x[1], reverse=True)[:10]:
            result.append(f"  - {ext}: {count} file(s)")
        
        result.extend([
            f"\n📈 Records:",
            f"  - Largest File: {Path(stats['largest_file'][0]).name} ({stats['largest_file'][1] / 1024:.2f} KB)",
            f"  - Oldest File: {Path(stats['oldest_file'][0]).name} ({datetime.fromtimestamp(stats['oldest_file'][1]).strftime('%Y-%m-%d')})",
            f"  - Newest File: {Path(stats['newest_file'][0]).name} ({datetime.fromtimestamp(stats['newest_file'][1]).strftime('%Y-%m-%d')})"
        ])
        
        return "\n".join(result)
    
    except Exception as e:
        return f"Error calculating statistics: {str(e)}"


@mcp.resource("file://{path}")
def file_resource(path: str) -> str:
    """Access file system resources"""
    try:
        path_obj = Path(path)
        if path_obj.exists():
            return f"File resource: {path} (exists)"
        else:
            return f"File resource: {path} (does not exist)"
    except Exception as e:
        return f"File resource error: {str(e)}"


if __name__ == "__main__":
    # Run the server
    import asyncio
    asyncio.run(mcp.run())
