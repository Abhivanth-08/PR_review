"""
Advanced Git Diff Parser with context extraction
"""
import re
from typing import List, Dict, Tuple
from models import FileChange


class DiffParser:
    """Parse and analyze git diffs with enhanced context"""

    @staticmethod
    def parse_diff(diff_content: str) -> List[FileChange]:
        """Parse unified diff format into structured file changes"""
        files = []
        current_file = None
        current_patch = []

        lines = diff_content.split('\n')

        for line in lines:
            # Detect file header
            if line.startswith('diff --git'):
                if current_file:
                    current_file['patch'] = '\n'.join(current_patch)
                    files.append(FileChange(**current_file))

                # Extract filename
                match = re.search(r'b/(.+)$', line)
                filename = match.group(1) if match else "unknown"

                current_file = {
                    'filename': filename,
                    'additions': 0,
                    'deletions': 0,
                    'patch': '',
                    'status': 'modified'
                }
                current_patch = []

            # Detect file status
            elif line.startswith('new file'):
                if current_file:
                    current_file['status'] = 'added'
            elif line.startswith('deleted file'):
                if current_file:
                    current_file['status'] = 'deleted'

            # Count additions/deletions
            elif line.startswith('+') and not line.startswith('+++'):
                if current_file:
                    current_file['additions'] += 1
                current_patch.append(line)
            elif line.startswith('-') and not line.startswith('---'):
                if current_file:
                    current_file['deletions'] += 1
                current_patch.append(line)
            else:
                current_patch.append(line)

        # Add last file
        if current_file:
            current_file['patch'] = '\n'.join(current_patch)
            files.append(FileChange(**current_file))

        return files

    @staticmethod
    def extract_changed_lines(patch: str) -> List[Dict]:
        """Extract changed lines with context"""
        changed_lines = []
        current_line_num = 0

        for line in patch.split('\n'):
            # Parse hunk header
            if line.startswith('@@'):
                match = re.search(r'\+(\d+)', line)
                if match:
                    current_line_num = int(match.group(1))
                continue

            # Track additions
            if line.startswith('+') and not line.startswith('+++'):
                changed_lines.append({
                    'line_number': current_line_num,
                    'type': 'addition',
                    'content': line[1:],
                    'raw': line
                })
                current_line_num += 1

            # Track deletions
            elif line.startswith('-') and not line.startswith('---'):
                changed_lines.append({
                    'line_number': current_line_num,
                    'type': 'deletion',
                    'content': line[1:],
                    'raw': line
                })

            # Context lines
            elif not line.startswith('\\'):
                current_line_num += 1

        return changed_lines

    @staticmethod
    def get_file_extension(filename: str) -> str:
        """Extract file extension"""
        return filename.split('.')[-1] if '.' in filename else ''

    @staticmethod
    def group_changes_by_function(patch: str, language: str) -> List[Dict]:
        """Group changes by function/method context"""
        # Simplified function detection patterns
        function_patterns = {
            'python': r'^\s*def\s+(\w+)',
            'javascript': r'^\s*(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\()',
            'typescript': r'^\s*(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\()',
            'java': r'^\s*(?:public|private|protected)?\s*(?:static\s+)?[\w<>]+\s+(\w+)\s*\(',
            'go': r'^\s*func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)',
        }

        pattern = function_patterns.get(language)
        if not pattern:
            return []

        functions = []
        current_function = None

        for line in patch.split('\n'):
            match = re.search(pattern, line)
            if match:
                function_name = match.group(1) or match.group(2)
                current_function = {
                    'name': function_name,
                    'changes': []
                }
                functions.append(current_function)

            if current_function and (line.startswith('+') or line.startswith('-')):
                current_function['changes'].append(line)

        return functions

