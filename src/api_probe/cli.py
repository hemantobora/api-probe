"""Command-line interface for api-probe."""

import sys
import os
import warnings
import yaml

# Suppress urllib3 SSL warnings (important for CI/CD)
warnings.filterwarnings('ignore', message='.*OpenSSL.*')
warnings.filterwarnings('ignore', category=Warning, module='urllib3')

from . import __version__
from .config.loader import load_config
from .config.parser import ConfigParser
from .config.validator import ConfigValidator
from .execution.executor import ProbeExecutor
from .reporting.reporter import Reporter
from .config.models import Config, Group, Probe


def print_usage():
    """Print usage information."""
    print("""Usage:
  api-probe <config-file>              Run probes from config file
  api-probe validate <config-file>     Validate config and list variables
  api-probe --help                     Show this help message
  api-probe -v, --version              Print version
""", file=sys.stderr)


def validate_command(config_file: str) -> int:
    """Execute validate command.
    
    Args:
        config_file: Path to configuration file
        
    Returns:
        Exit code (0 = valid, 1 = invalid, 2 = error)
    """
    try:
        # Load configuration
        print(f"Validating: {config_file}", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(file=sys.stderr)
        
        config_dict = load_config(config_file)
        
        # Validate structure
        validator = ConfigValidator()
        is_valid, errors, warnings_list = validator.validate(config_dict)
        
        # Show errors
        if errors:
            print("❌ VALIDATION ERRORS:", file=sys.stderr)
            for error in errors:
                print(f"  • {error}", file=sys.stderr)
            print(file=sys.stderr)
        
        # Show warnings
        if warnings_list:
            print("⚠️  WARNINGS:", file=sys.stderr)
            for warning in warnings_list:
                print(f"  • {warning}", file=sys.stderr)
            print(file=sys.stderr)
        
        # Extract and show variables
        variables = validator.extract_variables(config_dict)
        
        if variables:
            print("📋 ENVIRONMENT VARIABLES REFERENCED:", file=sys.stderr)
            print(file=sys.stderr)
            
            # Check which are defined
            defined = []
            undefined = []
            
            for var in sorted(variables):
                if var in os.environ or validator._is_variable_defined_in_all_executions(var):
                    defined.append(var)
                else:
                    undefined.append(var)
            
            if defined:
                print("  ✓ Defined:", file=sys.stderr)
                for var in defined:
                    print(f"    • {var}", file=sys.stderr)
                print(file=sys.stderr)
            
            if undefined:
                print("  ✗ Not defined:", file=sys.stderr)
                for var in undefined:
                    exec_blocks = validator._get_execution_block_for_undefined_variable(var) if validator._is_variable_defined_in_any_execution(var) else []
                    if exec_blocks:
                        print(f"    • {var} (undefined in executions: {', '.join(exec_blocks)})", file=sys.stderr)
                    else:
                        print(f"    • {var}", file=sys.stderr)
                print(file=sys.stderr)
        else:
            print("📋 No environment variables referenced", file=sys.stderr)
            print(file=sys.stderr)
        
        # Try parsing
        parse_ok = True
        print("Parsing configuration...", file=sys.stderr)
        try:
            parser = ConfigParser()
            config = parser.parse(config_dict)
            print(f"✓ Successfully parsed {count_probes(config)} probe(s)", file=sys.stderr)
            
            if config.executions:
                print(f"✓ Found {len(config.executions)} execution context(s)", file=sys.stderr)
            
            print(file=sys.stderr)
        except Exception as e:
            print(f"✗ Parse error: {e}", file=sys.stderr)
            print(file=sys.stderr)
            parse_ok = False
        
        # Summary
        print("=" * 60, file=sys.stderr)
        if is_valid and parse_ok:
            print("✅ Configuration is valid!", file=sys.stderr)
            return 0
        else:
            print("❌ Configuration has errors", file=sys.stderr)
            return 1
            
    except FileNotFoundError:
        print(f"Error: Config file not found: {config_file}", file=sys.stderr)
        return 2
    except yaml.YAMLError as e:
        print(f"Error: YAML parse error in {config_file}:", file=sys.stderr)
        print(str(e), file=sys.stderr)
        print(file=sys.stderr)
        print("Tip: Common causes — tabs instead of spaces, invalid escape sequences (use single quotes for regex patterns)", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

def count_probes(config: Config) -> int:
    """Count total number of probes in the configuration, including nested groups."""
    count = 0
    stack = list(config.probes)  # Start with top-level probes list
    while stack:
        item = stack.pop()
        if isinstance(item, Probe):
            count += 1
        elif isinstance(item, Group):
            stack.extend(list(item.probes))
    
    return count

def run_command(config_file: str) -> int:
    """Execute run command (normal probe execution).
    
    Args:
        config_file: Path to configuration file
        
    Returns:
        Exit code (0 = success, 1 = failures, 2 = error)
    """
    try:
        # Load configuration
        config_dict = load_config(config_file)
        
        # Parse into models
        parser = ConfigParser()
        config = parser.parse(config_dict)
        
        # Execute probes
        executor = ProbeExecutor()
        result = executor.execute(config)
        
        # Report results
        reporter = Reporter()
        reporter.report(result)
        
        # Exit code based on success
        return 0 if result.success else 1
        
    except FileNotFoundError:
        print(f"Error: Config file not found: {config_file}", file=sys.stderr)
        return 2
    except yaml.YAMLError as e:
        print(f"Error: YAML parse error in {config_file}:", file=sys.stderr)
        print(str(e), file=sys.stderr)
        print(file=sys.stderr)
        print("Tip: Common causes — tabs instead of spaces, invalid escape sequences (use single quotes for regex patterns)", file=sys.stderr)
        return 2
    except (ValueError, KeyError) as e:
        # Config/parse errors — clean message, no traceback
        print(f"Error: {e}", file=sys.stderr)
        print(f"Run 'api-probe validate {config_file}' for details", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2


def main():
    """Main entry point for CLI."""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(2)
    
    # Handle commands
    if sys.argv[1] in ['-v', '--version']:
        print(f"api-probe {__version__}")
        sys.exit(0)

    if sys.argv[1] in ['--help', '-h', 'help']:
        print_usage()
        sys.exit(0)
    
    if sys.argv[1] == 'validate':
        if len(sys.argv) < 3:
            print("Error: validate command requires a config file", file=sys.stderr)
            print(file=sys.stderr)
            print_usage()
            sys.exit(2)
        
        config_file = sys.argv[2]
        exit_code = validate_command(config_file)
        sys.exit(exit_code)
    
    # Default: run probes
    config_file = sys.argv[1]
    exit_code = run_command(config_file)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
