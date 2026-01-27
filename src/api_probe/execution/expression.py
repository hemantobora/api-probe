"""Expression evaluator for ignore field conditions."""

import re
import sys
from typing import Any, Dict, Optional


class ExpressionEvaluator:
    """Evaluates simple boolean expressions for ignore field."""
    
    def __init__(self):
        """Initialize expression evaluator."""
        self.functions = {
            'len': self._func_len,
            'has': self._func_has,
            'empty': self._func_empty,
        }
    
    def is_expression(self, value: str) -> bool:
        """Check if string looks like an expression.
        
        Args:
            value: String to check
            
        Returns:
            True if it looks like an expression
        """
        # Check for operators or function calls
        operators = ['==', '!=', '>', '<', '>=', '<=', '&&', '||', '!']
        functions = ['len(', 'has(', 'empty(']
        
        for op in operators:
            if op in value:
                return True
        
        for func in functions:
            if func in value:
                return True
        
        return False
    
    def evaluate(self, expression: str, variables: Dict[str, Any]) -> bool:
        """Evaluate expression to boolean.
        
        Args:
            expression: Expression string
            variables: Variable context
            
        Returns:
            Boolean result (False if evaluation fails)
        """
        try:
            # Replace variables with their values
            expr = self._substitute_variables(expression, variables)
            
            # Evaluate functions
            expr = self._evaluate_functions(expr, variables)
            
            # Replace operators with Python equivalents
            expr = expr.replace('&&', ' and ')
            expr = expr.replace('||', ' or ')
            expr = expr.replace('!', ' not ')
            
            # Evaluate the expression
            result = eval(expr, {"__builtins__": {}}, {})
            
            return bool(result)
            
        except Exception as e:
            print(f"[WARN] Failed to evaluate expression '{expression}': {e}", file=sys.stderr)
            return False
    
    def _substitute_variables(self, expression: str, variables: Dict[str, Any]) -> str:
        """Substitute variable names with their string representations.
        
        Args:
            expression: Expression string
            variables: Variable context
            
        Returns:
            Expression with variables substituted
        """
        # Find all variable references (alphanumeric + underscore)
        # But avoid function names
        result = expression
        
        # Sort by length (longest first) to avoid partial replacements
        var_names = sorted(variables.keys(), key=len, reverse=True)
        
        for var_name in var_names:
            # Only replace if it's a standalone word (not part of function name)
            pattern = r'\b' + re.escape(var_name) + r'\b'
            value = variables[var_name]
            
            # Convert to Python representation
            if value is None:
                replacement = 'None'
            elif isinstance(value, str):
                replacement = repr(value)
            elif isinstance(value, bool):
                replacement = str(value)
            elif isinstance(value, (int, float)):
                replacement = str(value)
            elif isinstance(value, (list, dict)):
                replacement = repr(value)
            else:
                replacement = repr(str(value))
            
            result = re.sub(pattern, replacement, result)
        
        return result
    
    def _evaluate_functions(self, expression: str, variables: Dict[str, Any]) -> str:
        """Evaluate function calls in expression.
        
        Args:
            expression: Expression string
            variables: Variable context
            
        Returns:
            Expression with functions evaluated
        """
        result = expression
        
        # Find and evaluate function calls
        # Pattern: function_name(arg)
        func_pattern = r'(\w+)\(([^)]+)\)'
        
        def replace_func(match):
            func_name = match.group(1)
            arg = match.group(2).strip()
            
            if func_name not in self.functions:
                return match.group(0)  # Return unchanged
            
            # Get the actual variable value
            if arg in variables:
                value = variables[arg]
            else:
                # Try to evaluate the argument
                try:
                    value = eval(arg, {"__builtins__": {}}, {})
                except:
                    return match.group(0)  # Return unchanged
            
            # Call the function
            try:
                func_result = self.functions[func_name](value)
                return str(func_result)
            except Exception as e:
                print(f"[WARN] Function {func_name} failed: {e}", file=sys.stderr)
                return match.group(0)  # Return unchanged
        
        result = re.sub(func_pattern, replace_func, result)
        return result
    
    def _func_len(self, value: Any) -> int:
        """Get length of value.
        
        Args:
            value: Value to get length of
            
        Returns:
            Length
        """
        if value is None:
            return 0
        if isinstance(value, (str, list, dict)):
            return len(value)
        return 0
    
    def _func_has(self, value: Any) -> bool:
        """Check if value exists and is not empty.
        
        Args:
            value: Value to check
            
        Returns:
            True if exists and not empty
        """
        if value is None:
            return False
        if isinstance(value, str):
            return len(value) > 0
        if isinstance(value, (list, dict)):
            return len(value) > 0
        return True
    
    def _func_empty(self, value: Any) -> bool:
        """Check if value is empty or None.
        
        Args:
            value: Value to check
            
        Returns:
            True if empty or None
        """
        return not self._func_has(value)
    
    def evaluate_for_output(self, expression: str, response: Any, variables: Dict[str, Any], extractor: Any) -> Any:
        """Evaluate expression for output capture (returns actual value, not just boolean).
        
        Args:
            expression: Expression string
            response: HTTP response object
            variables: Variable context
            extractor: Path extractor for accessing response data
            
        Returns:
            Result of expression evaluation
        """
        try:
            # First, try to extract any response paths in the expression
            # Replace body.path with actual values
            import re
            
            # Find body.* patterns
            body_pattern = r'body\.([a-zA-Z0-9_.\[\]]+)'
            matches = re.findall(body_pattern, expression)
            
            temp_vars = variables.copy()
            for i, match in enumerate(matches):
                temp_var_name = f'__BODY_{i}__'
                try:
                    value = extractor.extract(response, match)
                    temp_vars[temp_var_name] = value
                    expression = expression.replace(f'body.{match}', temp_var_name)
                except:
                    temp_vars[temp_var_name] = None
                    expression = expression.replace(f'body.{match}', temp_var_name)
            
            # Evaluate functions
            expr = self._evaluate_functions(expression, temp_vars)
            
            # Substitute variables
            expr = self._substitute_variables(expr, temp_vars)
            
            # Replace operators with Python equivalents
            expr = expr.replace('&&', ' and ')
            expr = expr.replace('||', ' or ')
            expr = expr.replace('!', ' not ')
            
            # Evaluate
            result = eval(expr, {"__builtins__": {}}, {})
            return result
            
        except Exception as e:
            print(f"[WARN] Failed to evaluate output expression '{expression}': {e}", file=sys.stderr)
            return None