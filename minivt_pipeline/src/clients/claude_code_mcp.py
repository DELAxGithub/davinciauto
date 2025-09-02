"""
Claude Code MCP execution adapter.
Provides interface to Claude Code's mcp__ide__executeCode functionality.
"""
import sys
import io
from contextlib import redirect_stdout, redirect_stderr


def execute_code(code: str) -> str:
    """
    Execute Python code and return output.
    This simulates Claude Code's MCP execution environment.
    
    Args:
        code: Python code to execute
        
    Returns:
        String output from code execution
    """
    try:
        # Capture stdout
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        
        # Redirect output streams
        sys.stdout = stdout_buffer
        sys.stderr = stderr_buffer
        
        # Create execution namespace
        namespace = {
            '__name__': '__main__',
            '__builtins__': __builtins__
        }
        
        # Execute code
        exec(code, namespace)
        
        # Get output
        stdout_content = stdout_buffer.getvalue()
        stderr_content = stderr_buffer.getvalue()
        
        # Restore streams
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        
        # Return stdout content, or stderr if stdout is empty
        if stdout_content.strip():
            return stdout_content.strip()
        elif stderr_content.strip():
            return f"ERROR: {stderr_content.strip()}"
        else:
            return ""
            
    except Exception as e:
        # Restore streams in case of error
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        return f"EXECUTION_ERROR: {str(e)}"


def execute_code_with_mcp(code: str) -> str:
    """
    Execute code using Claude Code's actual MCP execution if available.
    Falls back to local execution if MCP is not available.
    
    Args:
        code: Python code to execute
        
    Returns:
        String output from code execution
    """
    try:
        # Try to use actual MCP execution if available
        # This would be replaced with actual MCP call in Claude Code environment
        from mcp__ide__executeCode import execute_code as mcp_execute
        return mcp_execute(code)
    except ImportError:
        # Fallback to local execution
        return execute_code(code)