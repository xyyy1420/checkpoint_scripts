import os
import yaml
import re

class BaseConfig:
    def __init__(self, path_env_vars_to_check=None, env_vars_to_check=None):
        self.path_env_vars = {}
        self.env_vars = {}
        if path_env_vars_to_check:
            for path_env_var in path_env_vars_to_check:
                self.path_env_vars[path_env_var] = self.check_directory(path_env_var)
        if env_vars_to_check:
            for env_var in env_vars_to_check:
                self.env_vars[env_var] = self.check_env_vars(env_var)

        self.config = {
            "path_env_vars": self.path_env_vars,
            "env_vars": self.env_vars
        }

    def append_env(self, env):
        env_pattern = re.compile(r"^\$[\(|\{](\w+)[\)|\}]")
        match = env_pattern.findall(env)
        for key in match:
            self.path_env_vars[key] = self.check_directory(key)

    def load_yaml(self, yaml_path):
        if yaml_path:
            with open(yaml_path, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file)
        else:
            return {}

    def get_config(self):
        return self.config

    def check_env_vars(self, env_var):
        value = os.environ.get(env_var)
        if not value:
            raise EnvironmentError(f"Environment variable {env_var} is not set.")
        return value

    def check_directory(self, env_var):
        """Check if the environment variable is set and points to an existing directory."""
        path = self.check_env_vars(env_var)
        if not os.path.exists(path):
            raise EnvironmentError(f"Path {path} for environment variable {env_var} does not exist.")
        return path

