"""Configuration parser - converts raw dicts to models."""

from typing import Any, Dict, List, Union

from .models import Config, Test, Group, Validation


class ConfigParser:
    """Parses raw configuration dicts into model objects."""
    
    def parse(self, config_dict: Dict[str, Any]) -> Config:
        """Parse configuration dict into Config object.
        
        Args:
            config_dict: Raw configuration dictionary
            
        Returns:
            Parsed Config object
            
        Raises:
            ValueError: If configuration is invalid
        """
        if 'tests' not in config_dict:
            raise ValueError("Configuration must have 'tests' field")
        
        tests = []
        for item in config_dict['tests']:
            if 'group' in item:
                # It's a group
                tests.append(self._parse_group(item['group']))
            else:
                # It's a test
                tests.append(self._parse_test(item))
        
        return Config(tests=tests)
    
    def _parse_test(self, test_dict: Dict[str, Any]) -> Test:
        """Parse test dictionary into Test object.
        
        Args:
            test_dict: Raw test dictionary
            
        Returns:
            Test object
            
        Raises:
            ValueError: If test is invalid
        """
        # Validate required fields
        if 'name' not in test_dict:
            raise ValueError("Test must have 'name' field")
        if 'type' not in test_dict:
            raise ValueError(f"Test '{test_dict.get('name')}' must have 'type' field")
        if 'endpoint' not in test_dict:
            raise ValueError(f"Test '{test_dict.get('name')}' must have 'endpoint' field")
        
        test_type = test_dict['type']
        if test_type not in ['rest', 'graphql']:
            raise ValueError(f"Test type must be 'rest' or 'graphql', got '{test_type}'")
        
        # GraphQL requires query
        if test_type == 'graphql' and 'query' not in test_dict:
            raise ValueError(f"GraphQL test '{test_dict['name']}' must have 'query' field")
        
        # REST with body requires Content-Type
        if test_type == 'rest' and 'body' in test_dict and test_dict['body'] is not None:
            headers = test_dict.get('headers', {})
            if not any(k.lower() == 'content-type' for k in headers.keys()):
                raise ValueError(
                    f"REST test '{test_dict['name']}' with body must have Content-Type header"
                )
        
        # Parse validation if present
        validation = None
        if 'validation' in test_dict:
            validation = self._parse_validation(test_dict['validation'])
        
        return Test(
            name=test_dict['name'],
            type=test_dict['type'],
            endpoint=test_dict['endpoint'],
            method=test_dict.get('method', 'GET'),
            headers=test_dict.get('headers'),
            body=test_dict.get('body'),
            query=test_dict.get('query'),
            variables=test_dict.get('variables'),
            validation=validation,
            output=test_dict.get('output')
        )
    
    def _parse_group(self, group_dict: Dict[str, Any]) -> Group:
        """Parse group dictionary into Group object.
        
        Args:
            group_dict: Raw group dictionary
            
        Returns:
            Group object
        """
        if 'tests' not in group_dict:
            raise ValueError("Group must have 'tests' field")
        
        tests = [self._parse_test(t) for t in group_dict['tests']]
        return Group(tests=tests)
    
    def _parse_validation(self, val_dict: Dict[str, Any]) -> Validation:
        """Parse validation dictionary into Validation object.
        
        Args:
            val_dict: Raw validation dictionary
            
        Returns:
            Validation object
        """
        return Validation(
            status=val_dict.get('status'),
            headers=val_dict.get('headers'),
            body=val_dict.get('body')
        )
