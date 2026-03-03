"""Output variable capture from responses."""

import sys
from typing import Any, Dict, List

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
        context: ExecutionContext,
    ) -> List[str]:
        """Capture output variables from response.

        Args:
            response: HTTP response object
            output_spec: Dict mapping var names to paths or expressions
            context: Execution context to store variables in

        Raises:
            ValueError: If path is invalid or extraction fails
        """
        warnings = []
        for var_name, path_or_expr in output_spec.items():
            if self.expression_evaluator.is_expression(path_or_expr):
                try:
                    value = self.expression_evaluator.evaluate_for_output(
                        path_or_expr, response, context.variables, self.extractor
                    )
                    context.set_variable(var_name, value)
                except Exception as e:
                    warnings.append(
                        f"    [WARN] Output capture failed for '{var_name}' "
                        f"(expression: '{path_or_expr}'): {e} — variable will be unset"
                    )
                    # Do NOT set the variable — leaves it unset so downstream
                    # probes that reference ${var_name} are skipped, not run with 'None'
            else:
                try:
                    value = self._extract_value(response, path_or_expr)
                    context.set_variable(var_name, value)
                except Exception as e:
                    warnings.append(
                        f"    [WARN] Output capture failed for '{var_name}' "
                        f"(path: '{path_or_expr}'): {e} — variable will be unset"
                    )
                    # Do NOT set the variable — leaves it unset so downstream
                    # probes that reference ${var_name} are skipped, not run with 'None'
        return warnings

    def _extract_value(self, response: Any, path: str) -> Any:
        """Extract value from response using path.

        Path convention matches all validators:

            status              → response status code
            headers.X-Auth-Token → header value
            data.token          → body field
            $.data.token        → body field (JSONPath)
            data.items[0].id    → array index in body

        If the path starts with 'headers.' it is always treated as a header.
        If the path is exactly 'status' it returns the status code.
        Everything else is treated as a body path.

        Args:
            response: HTTP response object
            path: Path string

        Returns:
            Extracted value

        Raises:
            ValueError: If extraction fails
        """
        if path == 'status':
            return response.status_code

        if path.startswith('headers.'):
            header_name = path[len('headers.'):]
            return self.extractor.extract_header(response, header_name)

        # Bare path — same convention as all validators
        return self.extractor.extract(response, path)
