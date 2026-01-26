"""Command-line interface for api-probe."""

import sys
import warnings

# Suppress urllib3 SSL warnings (important for CI/CD)
warnings.filterwarnings('ignore', message='.*OpenSSL.*')
warnings.filterwarnings('ignore', category=Warning, module='urllib3')

from .config.loader import load_config
from .config.parser import ConfigParser
from .execution.executor import ProbeExecutor
from .reporting.reporter import Reporter


def main():
    """Main entry point for CLI."""
    if len(sys.argv) < 2:
        print("Usage: api-probe <config-file>")
        sys.exit(2)
    
    config_file = sys.argv[1]
    
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
        sys.exit(0 if result.success else 1)
        
    except FileNotFoundError:
        print(f"Error: Config file not found: {config_file}")
        sys.exit(2)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == '__main__':
    main()
