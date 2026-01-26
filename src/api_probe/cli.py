"""Command-line interface for api-probe."""

import sys
import os
import warnings

# Suppress urllib3 SSL warnings (important for CI/CD)
warnings.filterwarnings('ignore', message='.*OpenSSL.*')
warnings.filterwarnings('ignore', category=Warning, module='urllib3')

from .config.loader import load_config
from .config.parser import ConfigParser
from .config.validator import ConfigValidator
from .execution.executor import ProbeExecutor
from .reporting.reporter import Reporter


def print_usage():
    """Print usage information."""
    print("""Usage:
  api-probe <config-file>              Run probes from config file
  api-probe validate <config-file>     Validate config and list variables
  api-probe --help                     Show this help message
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
                if var in os.environ:
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
                    print(f"    • {var}", file=sys.stderr)
                print(file=sys.stderr)
        else:
            print("📋 No environment variables referenced", file=sys.stderr)
            print(file=sys.stderr)
        
        # Try parsing
        print("Parsing configuration...", file=sys.stderr)
        try:
            parser = ConfigParser()
            config = parser.parse(config_dict)
            print(f"✓ Successfully parsed {len(config.probes)} probe(s)", file=sys.stderr)
            
            if config.executions:
                print(f"✓ Found {len(config.executions)} execution context(s)", file=sys.stderr)
            
            print(file=sys.stderr)
        except Exception as e:
            print(f"✗ Parse error: {e}", file=sys.stderr)
            print(file=sys.stderr)
            return 1
        
        # Summary
        print("=" * 60, file=sys.stderr)
        if is_valid:
            print("✅ Configuration is valid!", file=sys.stderr)
            return 0
        else:
            print("❌ Configuration has errors", file=sys.stderr)
            return 1
            
    except FileNotFoundError:
        print(f"Error: Config file not found: {config_file}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 2


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
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 2


def main():
    """Main entry point for CLI."""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(2)
    
    # Handle commands
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
