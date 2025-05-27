# Contributing to Screener MCP Server

Thank you for your interest in contributing to the Screener MCP Server! This document provides guidelines and instructions for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/screener-mcp.git
   cd screener-mcp
   ```
3. Create a virtual environment and install dependencies:
   ```bash
   # On Mac/Linux
   ./run-server.sh
   
   # On Windows
   run-server.bat
   ```

## Development Guidelines

### Code Style
- Follow PEP 8 guidelines for Python code
- Use type hints for function parameters and return values
- Include docstrings for all functions and classes
- Keep functions focused and single-purpose
- Use meaningful variable and function names

### Adding New Tools
1. Add new tool functions in `server.py`
2. Use the `@mcp.tool()` decorator
3. Include comprehensive error handling
4. Add type hints and docstrings
5. Update the README.md with the new tool documentation

Example:
```python
@mcp.tool()
async def your_new_tool(param1: str, param2: int) -> Dict:
    """Description of what your tool does.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Dict containing the result
        
    Raises:
        ValueError: Description of when this error is raised
    """
    try:
        # Your implementation here
        return {"result": "success"}
    except Exception as e:
        return {"error": str(e)}
```

### Error Handling
- Use try/except blocks appropriately
- Return meaningful error messages
- Handle network errors gracefully
- Include error context when possible

### Testing
- Test your changes locally before submitting
- Verify all tools work as expected
- Test error scenarios
- Check rate limiting compliance

## Submitting Changes

1. Create a new branch for your feature:
   ```bash
   git checkout -b feature-name
   ```

2. Make your changes:
   - Write clear commit messages
   - Keep commits focused and atomic
   - Include tests if applicable

3. Push to your fork:
   ```bash
   git push origin feature-name
   ```

4. Create a Pull Request:
   - Provide a clear description of your changes
   - Reference any related issues
   - Include screenshots if relevant
   - List any breaking changes

## Pull Request Guidelines

- Keep PRs focused on a single feature/fix
- Include updated documentation
- Ensure code passes any existing tests
- Follow the existing code style
- Be responsive to review comments

## Code Review Process

1. All changes require review
2. Address review comments promptly
3. Keep discussions focused and professional
4. Be open to feedback and suggestions

## Documentation

- Update README.md for user-facing changes
- Include docstrings for new functions
- Document error cases and how to handle them
- Provide examples for new features

## Questions?

If you have questions about contributing:
1. Check existing issues and documentation
2. Ask in the project's discussion section
3. Open an issue for broader topics

Thank you for contributing!
