"""Configuration parser - converts raw dicts to models."""

from typing import Any, Dict, List, Union

from .models import Config, Probe, Group, Validation, Execution


class ConfigParser:
    """Parses configuration dictionaries into model objects."""
    
    def parse(self, config_dict: Dict[str, Any]) -> Config:
        """Parse configuration dictionary.
        
        Args:
            config_dict: Raw configuration dictionary
            
        Returns:
            Parsed Config object
            
        Raises:
            ValueError: If configuration is invalid
        """
        if 'probes' not in config_dict:
            raise ValueError("Configuration must have 'probes' field")
        
        probes = []
        for item in config_dict['probes']:
            if 'group' in item:
                probes.append(self._parse_group(item['group']))
            else:
                probes.append(self._parse_probe(item))
        
        # Parse executions if present
        executions = []
        if 'executions' in config_dict:
            executions_list = config_dict['executions']
            if executions_list:  # Not empty
                for exec_dict in executions_list:
                    executions.append(self._parse_execution(exec_dict))
        
        return Config(probes=probes, executions=executions)
    
    def _parse_execution(self, exec_dict: Dict[str, Any]) -> Execution:
        """Parse execution definition.
        
        Args:
            exec_dict: Execution dictionary
            
        Returns:
            Execution object
        """
        name = exec_dict.get('name')
        vars_list = exec_dict.get('vars', [])
        
        return Execution(name=name, vars=vars_list)
    
    def _parse_probe(self, probe_dict: Dict[str, Any]) -> Probe:
        """Parse probe definition.
        
        Args:
            probe_dict: Probe dictionary
            
        Returns:
            Probe object
            
        Raises:
            ValueError: If probe definition is invalid
        """
        # Required fields
        if 'name' not in probe_dict:
            raise ValueError("Probe must have 'name' field")
        if 'type' not in probe_dict:
            raise ValueError(f"Probe '{probe_dict['name']}' must have 'type' field")
        if 'endpoint' not in probe_dict:
            raise ValueError(f"Probe '{probe_dict['name']}' must have 'endpoint' field")
        
        probe_type = probe_dict['type']
        
        # Type-specific validation
        if probe_type == 'graphql' and 'query' not in probe_dict:
            raise ValueError(f"GraphQL probe '{probe_dict['name']}' must have 'query' field")
        
        # REST with body requires Content-Type
        if probe_type == 'rest' and 'body' in probe_dict:
            headers = probe_dict.get('headers', {})
            if not any(k.lower() == 'content-type' for k in headers.keys()):
                raise ValueError(
                    f"REST probe '{probe_dict['name']}' with body must have Content-Type header"
                )
        
        # Parse validation
        validation = None
        if 'validation' in probe_dict:
            validation = self._parse_validation(probe_dict['validation'])
        
        return Probe(
            name=probe_dict['name'],
            type=probe_type,
            endpoint=probe_dict['endpoint'],
            method=probe_dict.get('method', 'GET'),
            headers=probe_dict.get('headers'),
            body=probe_dict.get('body'),
            query=probe_dict.get('query'),
            variables=probe_dict.get('variables'),
            validation=validation,
            output=probe_dict.get('output'),
            delay=probe_dict.get('delay')
        )
    
    def _parse_group(self, group_dict: Dict[str, Any]) -> Group:
        """Parse group definition.
        
        Args:
            group_dict: Group dictionary
            
        Returns:
            Group object
        """
        probes = []
        for probe_dict in group_dict.get('probes', []):
            probes.append(self._parse_probe(probe_dict))
        
        return Group(probes=probes)
    
    def _parse_validation(self, validation_dict: Dict[str, Any]) -> Validation:
        """Parse validation specification.
        
        Args:
            validation_dict: Validation dictionary
            
        Returns:
            Validation object
        """
        return Validation(
            status=validation_dict.get('status'),
            headers=validation_dict.get('headers'),
            body=validation_dict.get('body')
        )
