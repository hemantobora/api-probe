"""Output variable capture from responses."""

from typing import Any, Dict
import sys

from .context import ExecutionContext
from .expression import ExpressionEvaluator
from ..validation.extractor import PathExtractor


class OutputCapture:
    """Captures output variables from responses."""
    
    def __init__(self, extractor: PathExtractor):
        """Initialize output capture.
        
        Args:
            extractor: Path extractor for value extraction
        """
        self.extractor = extractor
        self.expression_evaluator = ExpressionEvaluator()
    
    def capture(
        self,
        response: Any,
        output_spec: Dict[str, str],
        context: ExecutionContext
    ) -> None:
        """Capture output variables from response.
        
        Args:
            response: HTTP response object
            output_spec: Dict mapping var names to paths or expressions
            context: Execution context to store variables in
            
        Raises:
            ValueError: If path is invalid or extraction fails
        """
        for var_name, path_or_expr in output_spec.items():
            # Check if it's an expression
            if self.expression_evaluator.is_expression(path_or_expr):
                # Evaluate expression with current context
                try:
                    value = self.expression_evaluator.evaluate_for_output(
                        path_or_expr, response, context.variables, self.extractor
                    )
                    context.set_variable(var_name, value)
                except Exception as e:
                    print(f"[WARN] Failed to evaluate output expression '{path_or_expr}': {e}", file=sys.stderr)
                    context.set_variable(var_name, None)
            else:
                # Standard path extraction
                value = self._extract_value(response, path_or_expr)
                context.set_variable(var_name, value)
    
    def _extract_value(self, response: Any, path: str) -> Any:
        """Extract value using path with prefix.
        
        Args:
            response: HTTP response object
            path: Path with prefix (body.*, headers.*, status)
            
        Returns:
            Extracted value
            
        Raises:
            ValueError: If path format is invalid
        """
        if path == "status":
            return response.status_code
        elif path.startswith("body."):
            # Extract from body
            body_path = path[5:]  # Remove "body." prefix
            return self.extractor.extract(response, body_path)
        elif path.startswith("headers."):
            # Extract from headers
            header_name = path[8:]  # Remove "headers." prefix
            return self.extractor.extract_header(response, header_name)
        else:
            raise ValueError(f"Invalid output path: {path}. Must start with 'body.', 'headers.', or be 'status'")
